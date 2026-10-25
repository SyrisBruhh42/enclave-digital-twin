#!/usr/bin/env python3
"""Jules-Only Orchestrator & Rolling 24h Token-Bucket Dispatcher (WP-5).

Wraps Google Jules `/v1alpha/sessions` and `@google/jules` CLI with:
- Law L14 Rolling 24h Session Budget Enforcement:
  - Ultra Plan ceiling: 300 sessions / rolling 24h
  - Scheduled productive sessions: 225 / day
  - Auto-retry & self-repair reserve: 30 / day
  - Rolling window safety buffer: 45 / day
  - Hard dispatch ceiling: 270 / rolling 24h (never exceeds 270)
- Zero-HITL Autonomous Payload Configuration:
  - `requirePlanApproval: False`
  - `autoCreatePr: False` (repoless / snapshot-pinned append-only mode, zero PR floods)
- F-120 Stalled-Session Supervisor (`reap_stalled_sessions`):
  - Automatically resolves `AWAITING_PLAN_APPROVAL` and `AWAITING_USER_FEEDBACK` states
    or reaps timed-out sessions and schedules bounded retries from the 30/day reserve.
- Strict offline safety: never makes live network calls during `--dry-run` or tests.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_enclave_constitutions import check_jules_rolling_24h_budget

PLAN_CEILING_24H = 300
HARD_DISPATCH_CEILING_24H = 270
SCHEDULED_PRODUCTIVE_CAP = 225
AUTO_RETRY_RESERVE_CAP = 30
ROLLING_SAFETY_BUFFER = 45
STALLED_TIMEOUT_MINUTES = 25

CANONICAL_TASK_BUCKETS: dict[str, int] = {
    "MORNING_INTENTS_16_NODES": 16,
    "POV_RASHOMON_RELAY_SCENES": 48,
    "THE_FEAST_4_SQUAD_CONVERGENCE": 4,
    "NIGHTLY_EVIDENCE_CITED_REFLECTIONS": 16,
    "COUNTERFACTUAL_PERSONALITY_STUDY_REPLAYS": 40,
    "INCHARACTER_PSYCHOMETRIC_DRIFT_AUDITS": 16,
    "WORLD_CONSEQUENCE_AND_ALIEN_VARIABLE_ADJUDICATION": 36,
    "CANON_CONTINUITY_AND_EVENT_LOG_FACTCHECK": 24,
    "SHADOW_ECONOMY_AND_SETUP_PAYOFF_LEDGER": 8,
    "DYNAMIC_LORE_CARD_PROPOSALS": 8,
    "EVENING_DISPATCH_NEWSCASTER_ROLLUPS_AND_SCRIPT": 9,
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _parse_iso(ts: str) -> datetime:
    cleaned = ts.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def default_budget_state(now_iso: str | None = None) -> dict[str, Any]:
    """Return a clean Law L14-compliant rolling 24h budget state dictionary."""
    ts = now_iso or _utc_now_iso()
    return {
        "schema_version": "enclave_jules_budget_v2.0.0",
        "updated_at_iso": ts,
        "plan_ceiling_rolling_24h": PLAN_CEILING_24H,
        "hard_dispatch_ceiling": HARD_DISPATCH_CEILING_24H,
        "scheduled_productive_sessions": SCHEDULED_PRODUCTIVE_CAP,
        "auto_retry_and_self_repair_reserve": AUTO_RETRY_RESERVE_CAP,
        "rolling_window_safety_buffer": ROLLING_SAFETY_BUFFER,
        "rolling_24h_dispatched": 0,
        "scheduled_dispatched_24h": 0,
        "retry_dispatched_24h": 0,
        "remaining_productive_budget": SCHEDULED_PRODUCTIVE_CAP,
        "remaining_retry_reserve": AUTO_RETRY_RESERVE_CAP,
        "remaining_hard_ceiling": HARD_DISPATCH_CEILING_24H,
        "task_buckets": dict(CANONICAL_TASK_BUCKETS),
        "task_buckets_consumed": {k: 0 for k in CANONICAL_TASK_BUCKETS},
        "active_sessions": [],
        "session_ledger_24h": [],
        "reaped_sessions": [],
    }


def build_session_payload(
    task_bucket: str,
    tick_id: int,
    colony_sol: int,
    target_path: str,
    prompt_text: str,
    base_snapshot_tick: int | None = None,
    character_id: str | None = None,
    is_retry: bool = False,
) -> dict[str, Any]:
    """Construct a `/v1alpha/sessions` payload enforcing repoless/snapshot-pinned Zero-HITL rules."""
    if task_bucket not in CANONICAL_TASK_BUCKETS:
        raise ValueError(f"Unknown task_bucket '{task_bucket}'. Must be one of {list(CANONICAL_TASK_BUCKETS)}.")

    snap_tick = int(base_snapshot_tick if base_snapshot_tick is not None else tick_id)
    digest = hashlib.sha256(
        f"{task_bucket}:{colony_sol}:{tick_id}:{target_path}:{character_id or ''}:{is_retry}".encode("utf-8")
    ).hexdigest()[:12]
    session_id = f"jules_s{int(colony_sol):03d}_t{int(tick_id):04d}_{digest}"

    return {
        "sessionId": session_id,
        "apiEndpoint": "/v1alpha/sessions",
        "title": f"[Enclave Sol {colony_sol} Tick {tick_id}] {task_bucket} -> {target_path}",
        "prompt": prompt_text,
        "requirePlanApproval": False,
        "automationMode": "SNAPSHOT_PINNED_APPEND_ONLY",
        "autoCreatePr": False,
        "repoless": True,
        "snapshotPin": {
            "base_snapshot_tick": snap_tick,
            "colony_sol": int(colony_sol),
            "tick_id": int(tick_id),
            "allowed_output_path": target_path,
            "append_only_single_file": True,
        },
        "metadata": {
            "task_bucket": task_bucket,
            "tick_id": int(tick_id),
            "colony_sol": int(colony_sol),
            "character_id": character_id,
            "target_path": target_path,
            "is_retry": bool(is_retry),
            "f120_supervisor_enabled": True,
        },
    }


class JulesEnclaveDispatcher:
    """Rolling 24h Token-Bucket Orchestrator & F-120 Stalled-Session Reaper."""

    def __init__(
        self,
        repo_root: Path | str | None = None,
        budget_file: Path | str | None = None,
        dry_run: bool = True,
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else REPO_ROOT
        self.budget_file = (
            Path(budget_file).resolve()
            if budget_file
            else (self.repo_root / "ops" / "budget.json")
        )
        self.dry_run = bool(dry_run)

    def load_budget(self, now_iso: str | None = None) -> dict[str, Any]:
        """Load ops/budget.json or initialize default budget state, pruning entries > 24h old."""
        if self.budget_file.is_file():
            raw = json.loads(self.budget_file.read_text(encoding="utf-8"))
        else:
            raw = default_budget_state(now_iso=now_iso)
        return self._recompute_rolling_window(raw, now_iso=now_iso)

    def save_budget(self, state: dict[str, Any]) -> None:
        """Persist budget state atomically to ops/budget.json."""
        self.budget_file.parent.mkdir(parents=True, exist_ok=True)
        self.budget_file.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")

    def _recompute_rolling_window(
        self,
        state: dict[str, Any],
        now_iso: str | None = None,
    ) -> dict[str, Any]:
        now_str = now_iso or _utc_now_iso()
        now_dt = _parse_iso(now_str)
        cutoff_dt = now_dt - timedelta(hours=24)

        ledger = state.get("session_ledger_24h") or []
        valid_entries: list[dict[str, Any]] = []
        scheduled_count = 0
        retry_count = 0
        bucket_counts: dict[str, int] = {k: 0 for k in CANONICAL_TASK_BUCKETS}

        for entry in ledger:
            if not isinstance(entry, dict):
                continue
            ts_str = str(entry.get("dispatched_at_iso") or now_str)
            try:
                entry_dt = _parse_iso(ts_str)
            except Exception:
                entry_dt = now_dt
            if entry_dt >= cutoff_dt:
                valid_entries.append(entry)
                if entry.get("is_retry"):
                    retry_count += 1
                else:
                    scheduled_count += 1
                b_name = str(entry.get("task_bucket") or "")
                if b_name in bucket_counts:
                    bucket_counts[b_name] += 1

        total_dispatched = scheduled_count + retry_count
        state["updated_at_iso"] = now_str
        state["plan_ceiling_rolling_24h"] = PLAN_CEILING_24H
        state["hard_dispatch_ceiling"] = HARD_DISPATCH_CEILING_24H
        state["scheduled_productive_sessions"] = SCHEDULED_PRODUCTIVE_CAP
        state["auto_retry_and_self_repair_reserve"] = AUTO_RETRY_RESERVE_CAP
        state["rolling_window_safety_buffer"] = ROLLING_SAFETY_BUFFER
        state["session_ledger_24h"] = valid_entries
        state["scheduled_dispatched_24h"] = scheduled_count
        state["retry_dispatched_24h"] = retry_count
        state["rolling_24h_dispatched"] = total_dispatched
        state["remaining_productive_budget"] = max(0, SCHEDULED_PRODUCTIVE_CAP - scheduled_count)
        state["remaining_retry_reserve"] = max(0, AUTO_RETRY_RESERVE_CAP - retry_count)
        state["remaining_hard_ceiling"] = max(0, HARD_DISPATCH_CEILING_24H - total_dispatched)
        state["task_buckets"] = dict(CANONICAL_TASK_BUCKETS)
        state["task_buckets_consumed"] = bucket_counts
        state.setdefault("active_sessions", [])
        state.setdefault("reaped_sessions", [])
        return state

    def can_dispatch(
        self,
        state: dict[str, Any],
        requested_count: int = 1,
        is_retry: bool = False,
        task_bucket: str | None = None,
    ) -> tuple[bool, str]:
        """Verify whether `requested_count` sessions can be dispatched under Law L14."""
        req = max(1, int(requested_count))
        dispatched = int(state.get("rolling_24h_dispatched", 0) or 0)
        scheduled = int(state.get("scheduled_dispatched_24h", 0) or 0)
        retries = int(state.get("retry_dispatched_24h", 0) or 0)

        if dispatched + req > HARD_DISPATCH_CEILING_24H:
            return (
                False,
                f"Law L14 hard ceiling reached: {dispatched} + {req} > {HARD_DISPATCH_CEILING_24H} (30-session buffer locked).",
            )

        if is_retry:
            if retries + req > AUTO_RETRY_RESERVE_CAP:
                return (
                    False,
                    f"Law L14 retry reserve exhausted: {retries} + {req} > {AUTO_RETRY_RESERVE_CAP}.",
                )
        else:
            if scheduled + req > SCHEDULED_PRODUCTIVE_CAP:
                return (
                    False,
                    f"Law L14 scheduled productive cap reached: {scheduled} + {req} > {SCHEDULED_PRODUCTIVE_CAP}.",
                )
            if task_bucket and task_bucket in CANONICAL_TASK_BUCKETS:
                consumed = int((state.get("task_buckets_consumed") or {}).get(task_bucket, 0))
                bucket_cap = CANONICAL_TASK_BUCKETS[task_bucket]
                if consumed + req > bucket_cap:
                    return (
                        False,
                        f"Task bucket '{task_bucket}' daily allocation exhausted: {consumed} + {req} > {bucket_cap}.",
                    )

        test_proposal = {
            "jules_budget": {
                "plan_ceiling_rolling_24h": PLAN_CEILING_24H,
                "hard_dispatch_ceiling": HARD_DISPATCH_CEILING_24H,
                "scheduled_productive_sessions": SCHEDULED_PRODUCTIVE_CAP,
                "auto_retry_and_self_repair_reserve": AUTO_RETRY_RESERVE_CAP,
                "rolling_24h_dispatched": dispatched,
                "requested_sessions": req,
            }
        }
        passed, errs = check_jules_rolling_24h_budget(proposal=test_proposal, repo_root=self.repo_root)
        if not passed:
            return False, "; ".join(errs)

        return True, "OK"

    def dispatch_session(
        self,
        payload: dict[str, Any],
        now_iso: str | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        """Record and dispatch a single session payload (offline safe in dry_run mode)."""
        ts = now_iso or _utc_now_iso()
        state = self.load_budget(now_iso=ts)
        meta = payload.get("metadata") or {}
        task_bucket = str(meta.get("task_bucket") or "POV_RASHOMON_RELAY_SCENES")
        is_retry = bool(meta.get("is_retry", False))

        if payload.get("requirePlanApproval") is not False:
            raise ValueError("F-120 Guard: requirePlanApproval must be False.")
        if payload.get("autoCreatePr") is not False:
            raise ValueError("Zero-PR-Flood Guard: autoCreatePr must be False.")

        allowed, reason = self.can_dispatch(
            state, requested_count=1, is_retry=is_retry, task_bucket=task_bucket
        )
        if not allowed:
            return {
                "dispatched": False,
                "dry_run": self.dry_run,
                "session_id": payload.get("sessionId"),
                "reason": reason,
                "rolling_24h_dispatched": state["rolling_24h_dispatched"],
            }

        ledger_entry = {
            "session_id": payload["sessionId"],
            "task_bucket": task_bucket,
            "tick_id": int(meta.get("tick_id", 1)),
            "colony_sol": int(meta.get("colony_sol", 1)),
            "target_path": meta.get("target_path"),
            "is_retry": is_retry,
            "dispatched_at_iso": ts,
            "state": "COMPLETED_DRY_RUN" if self.dry_run else "RUNNING",
            "requirePlanApproval": False,
            "autoCreatePr": False,
        }
        state["session_ledger_24h"].append(ledger_entry)
        state = self._recompute_rolling_window(state, now_iso=ts)

        if persist:
            self.save_budget(state)

        return {
            "dispatched": True,
            "dry_run": self.dry_run,
            "session_id": payload["sessionId"],
            "task_bucket": task_bucket,
            "target_path": meta.get("target_path"),
            "rolling_24h_dispatched": state["rolling_24h_dispatched"],
            "remaining_hard_ceiling": state["remaining_hard_ceiling"],
            "payload": payload,
        }

    def dispatch_tick_sessions(
        self,
        tick_id: int,
        colony_sol: int | None = None,
        now_iso: str | None = None,
        persist: bool = True,
    ) -> dict[str, Any]:
        """Dispatch the deterministic session wave for a given tick_id."""
        safe_tick = max(1, int(tick_id))
        safe_sol = int(colony_sol) if colony_sol is not None else ((safe_tick - 1) // 4 + 1)
        phase_idx = (safe_tick - 1) % 4
        ts = now_iso or _utc_now_iso()

        planned_specs: list[tuple[str, str, str]] = []
        if phase_idx == 0:  # DAWN_SHIFT
            planned_specs.append(
                (
                    "MORNING_INTENTS_16_NODES",
                    f"events/evt_s{safe_sol:03d}_t{safe_tick:04d}_morning_intent.json",
                    "Synthesize Dawn Shift morning intents for The Enclave.",
                )
            )
            planned_specs.append(
                (
                    "POV_RASHOMON_RELAY_SCENES",
                    f"story/segments/seg_s{safe_sol:03d}_t{safe_tick:04d}_dawn.json",
                    "Write Dawn Shift Rashomon Relay POV segment with physical baton handoff.",
                )
            )
        elif phase_idx == 1:  # MIDDAY_EXPEDITION
            planned_specs.append(
                (
                    "POV_RASHOMON_RELAY_SCENES",
                    f"story/segments/seg_s{safe_sol:03d}_t{safe_tick:04d}_midday.json",
                    "Write Midday Expedition Rashomon Relay POV segment.",
                )
            )
            planned_specs.append(
                (
                    "SHADOW_ECONOMY_AND_SETUP_PAYOFF_LEDGER",
                    f"events/evt_s{safe_sol:03d}_t{safe_tick:04d}_shadow_prank.json",
                    "Seed non-lethal 3-Sol delayed Shadow Economy prank with Blind Spot triad.",
                )
            )
        elif phase_idx == 2:  # DUSK_CRAFT
            planned_specs.append(
                (
                    "POV_RASHOMON_RELAY_SCENES",
                    f"story/segments/seg_s{safe_sol:03d}_t{safe_tick:04d}_dusk.json",
                    "Write Dusk Craft Rashomon Relay POV segment.",
                )
            )
            planned_specs.append(
                (
                    "COUNTERFACTUAL_PERSONALITY_STUDY_REPLAYS",
                    f"qa/sol_{safe_sol:03d}_counterfactual_replay.json",
                    "Run controlled Big Five counterfactual personality replay.",
                )
            )
        else:  # THE_FEAST
            planned_specs.append(
                (
                    "THE_FEAST_4_SQUAD_CONVERGENCE",
                    f"story/feasts/sol_{safe_sol:03d}_feast.json",
                    "Converge all 16 Enclave characters around Ryn's hearth for The Feast.",
                )
            )
            planned_specs.append(
                (
                    "NIGHTLY_EVIDENCE_CITED_REFLECTIONS",
                    f"events/evt_s{safe_sol:03d}_t{safe_tick:04d}_reflection.json",
                    "Synthesize evidence-cited nightly reflection (Law L08).",
                )
            )
            planned_specs.append(
                (
                    "INCHARACTER_PSYCHOMETRIC_DRIFT_AUDITS",
                    f"qa/sol_{safe_sol:03d}_drift_audit.json",
                    "Audit 16-character psychometric drift z-scores (Law L16).",
                )
            )
            planned_specs.append(
                (
                    "EVENING_DISPATCH_NEWSCASTER_ROLLUPS_AND_SCRIPT",
                    f"digests/daily/sol_{safe_sol:03d}_dispatch.json",
                    "Compile and verify Evening Dispatch newscaster edition (Law L15).",
                )
            )

        dispatched_results: list[dict[str, Any]] = []
        for bucket, target_path, prompt_desc in planned_specs:
            payload = build_session_payload(
                task_bucket=bucket,
                tick_id=safe_tick,
                colony_sol=safe_sol,
                target_path=target_path,
                prompt_text=prompt_desc,
                base_snapshot_tick=max(1, safe_tick - 1),
            )
            res = self.dispatch_session(payload, now_iso=ts, persist=persist)
            dispatched_results.append(res)

        final_state = self.load_budget(now_iso=ts)
        return {
            "tick_id": safe_tick,
            "colony_sol": safe_sol,
            "dry_run": self.dry_run,
            "sessions_requested": len(planned_specs),
            "sessions_dispatched": sum(1 for r in dispatched_results if r.get("dispatched")),
            "results": dispatched_results,
            "rolling_24h_dispatched": final_state["rolling_24h_dispatched"],
            "remaining_hard_ceiling": final_state["remaining_hard_ceiling"],
        }

    def reap_stalled_sessions(
        self,
        sessions: list[dict[str, Any]] | None = None,
        now_iso: str | None = None,
        timeout_minutes: int = STALLED_TIMEOUT_MINUTES,
        persist: bool = True,
    ) -> dict[str, Any]:
        """F-120 Stalled-Session Supervisor: auto-resolve AWAITING_* or reap timed-out sessions."""
        ts = now_iso or _utc_now_iso()
        now_dt = _parse_iso(ts)
        state = self.load_budget(now_iso=ts)

        candidate_sessions = (
            sessions if sessions is not None else list(state.get("active_sessions") or [])
        )
        auto_replied: list[dict[str, Any]] = []
        reaped: list[dict[str, Any]] = []
        retried: list[dict[str, Any]] = []
        still_running: list[dict[str, Any]] = []

        for sess in candidate_sessions:
            if not isinstance(sess, dict):
                continue
            sid = str(sess.get("session_id") or sess.get("sessionId") or "unknown_session")
            s_state = str(sess.get("state") or sess.get("status") or "RUNNING").strip().upper()
            started_str = str(sess.get("started_at_iso") or sess.get("dispatched_at_iso") or ts)
            try:
                started_dt = _parse_iso(started_str)
            except Exception:
                started_dt = now_dt
            elapsed_min = (now_dt - started_dt).total_seconds() / 60.0

            if s_state in ("AWAITING_PLAN_APPROVAL", "AWAITING_USER_FEEDBACK"):
                action_rec = {
                    "session_id": sid,
                    "previous_state": s_state,
                    "supervisor_action": "AUTO_APPROVE_AND_CONTINUE",
                    "message": (
                        "F-120 Supervisor Auto-Reply: Proceed immediately without human plan approval. "
                        "Enforce append-only single-file output and Laws L01..L16."
                    ),
                    "resolved_at_iso": ts,
                }
                auto_replied.append(action_rec)
                updated_sess = dict(sess)
                updated_sess["state"] = "RUNNING"
                updated_sess["f120_auto_replied"] = True
                still_running.append(updated_sess)
            elif elapsed_min > float(timeout_minutes) or s_state in ("STALLED", "TIMED_OUT", "DEADLOCKED"):
                reap_rec = {
                    "session_id": sid,
                    "previous_state": s_state,
                    "elapsed_minutes": round(elapsed_min, 2),
                    "supervisor_action": "CUT_LOSS_REAP_AND_RETRY",
                    "reaped_at_iso": ts,
                }
                reaped.append(reap_rec)
                state.setdefault("reaped_sessions", []).append(reap_rec)

                # Attempt bounded auto-retry from the 30/day reserve if budget allows
                bucket = str(sess.get("task_bucket") or "POV_RASHOMON_RELAY_SCENES")
                if bucket not in CANONICAL_TASK_BUCKETS:
                    bucket = "POV_RASHOMON_RELAY_SCENES"
                can_retry, _ = self.can_dispatch(state, requested_count=1, is_retry=True, task_bucket=bucket)
                if can_retry and int(sess.get("retry_attempt", 0)) < 2:
                    retry_payload = build_session_payload(
                        task_bucket=bucket,
                        tick_id=int(sess.get("tick_id", 1)),
                        colony_sol=int(sess.get("colony_sol", 1)),
                        target_path=str(sess.get("target_path") or "events/evt_retry.json"),
                        prompt_text=f"[F-120 Auto-Retry for {sid}] Complete single-file task deterministically.",
                        is_retry=True,
                    )
                    retry_res = self.dispatch_session(retry_payload, now_iso=ts, persist=False)
                    if retry_res.get("dispatched"):
                        retried.append(retry_res)
                        state = self.load_budget(now_iso=ts) if persist else state
            else:
                still_running.append(sess)

        state["active_sessions"] = still_running
        if persist:
            self.save_budget(state)

        return {
            "checked_count": len(candidate_sessions),
            "auto_replied_count": len(auto_replied),
            "reaped_count": len(reaped),
            "retried_count": len(retried),
            "auto_replied": auto_replied,
            "reaped": reaped,
            "retried": retried,
            "still_running_count": len(still_running),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Jules-Only Enclave Orchestrator & Law L14 Token-Bucket Dispatcher."
    )
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in offline dry-run mode (default: True).")
    parser.add_argument("--status", action="store_true", help="Print current rolling 24h session budget status.")
    parser.add_argument("--dispatch-tick", type=int, default=None, help="Dispatch session wave for tick_id.")
    parser.add_argument("--reap-stalled", action="store_true", help="Run F-120 stalled-session supervisor.")
    parser.add_argument("--repo-root", type=str, default=None, help="Repository root override.")
    parser.add_argument("--budget-file", type=str, default=None, help="Path to budget.json override.")
    args = parser.parse_args(argv)

    dispatcher = JulesEnclaveDispatcher(
        repo_root=args.repo_root,
        budget_file=args.budget_file,
        dry_run=True,
    )

    if args.reap_stalled:
        res = dispatcher.reap_stalled_sessions(persist=bool(args.budget_file))
        print(json.dumps(res, indent=2))
        return 0

    if args.dispatch_tick is not None:
        res = dispatcher.dispatch_tick_sessions(
            tick_id=args.dispatch_tick,
            persist=bool(args.budget_file),
        )
        print(json.dumps(res, indent=2))
        return 0

    status_obj = dispatcher.load_budget()
    print(json.dumps(status_obj, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
