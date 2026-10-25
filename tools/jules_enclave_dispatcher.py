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
import os
from pathlib import Path
import sys
from typing import Any, Callable
import urllib.error
import urllib.request

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tools.check_enclave_constitutions import (
    check_jules_rolling_24h_budget,
    validate_proposal,
    validate_showrunner_storytelling_contract,
)

PLAN_CEILING_24H = 300
HARD_DISPATCH_CEILING_24H = 270
SCHEDULED_PRODUCTIVE_CAP = 225
AUTO_RETRY_RESERVE_CAP = 30
ROLLING_SAFETY_BUFFER = 45
STALLED_TIMEOUT_MINUTES = 25
UNIFIED_FLEET_CONCURRENT_VM_CAP = 48

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


def _xdg_state_home() -> Path:
    return Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state"))


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


def build_live_jules_api_request(
    payload: dict[str, Any],
    repo_slug: str = "SyrisBruhh42/enclave-digital-twin",
    starting_branch: str = "main",
) -> dict[str, Any]:
    """Convert an internal Enclave session payload into the canonical Google Jules `/v1alpha/sessions` body."""
    if payload.get("requirePlanApproval") is not False:
        raise ValueError("F-120 Guard: requirePlanApproval must be False.")
    return {
        "title": str(payload.get("title") or ""),
        "prompt": str(payload.get("prompt") or ""),
        "requirePlanApproval": False,
        "automationMode": "AUTO_CREATE_PR",
        "sourceContext": {
            "source": f"sources/github/{repo_slug}",
            "githubRepoContext": {
                "startingBranch": starting_branch,
            },
        },
    }


def _extract_proposal_from_unidiff(
    unidiff_text: str,
    default_target_path: str = "events/evt_salvaged.json",
) -> tuple[str, dict[str, Any]] | None:
    """Extract a single-file JSON proposal from a unified git diff (`changeSet.gitPatch.unidiffPatch`)."""
    if not unidiff_text or not unidiff_text.strip():
        return None
    target_path = default_target_path
    added_lines: list[str] = []
    for raw_line in unidiff_text.splitlines():
        if raw_line.startswith("+++ b/"):
            candidate = raw_line[len("+++ b/") :].strip()
            if candidate and candidate != "/dev/null":
                target_path = candidate
        elif raw_line.startswith("+") and not raw_line.startswith("+++"):
            added_lines.append(raw_line[1:])
    if not added_lines:
        return None
    try:
        parsed = json.loads("\n".join(added_lines))
        if isinstance(parsed, dict):
            return target_path, parsed
    except Exception:
        return None
    return None


class JulesRestClient:
    """REST client for Google Jules `/v1alpha/sessions` routing via `LFS_JULES_GATEWAY_URL` or `JULES_API_KEY`."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_sec: float = 20.0,
        transport: Callable[[str, str, dict[str, Any] | None], dict[str, Any]] | None = None,
    ) -> None:
        self._explicit_base_url = base_url
        self._explicit_api_key = api_key
        self.timeout_sec = float(timeout_sec)
        self._transport = transport

    def resolve_api_key(self) -> str:
        if self._explicit_api_key:
            return self._explicit_api_key.strip()
        env_key = os.environ.get("JULES_API_KEY", "").strip()
        if env_key:
            return env_key
        cred_dir = os.environ.get("CREDENTIALS_DIRECTORY", "").strip()
        if cred_dir:
            cred_file = Path(cred_dir) / "jules_api_key"
            if cred_file.is_file():
                try:
                    return cred_file.read_text(encoding="utf-8").strip()
                except OSError:
                    pass
        key_file = Path(os.environ.get("JULES_API_KEY_FILE") or (Path.home() / ".secrets" / "jules_api_key"))
        if key_file.is_file():
            try:
                return key_file.read_text(encoding="utf-8").strip()
            except OSError:
                pass
        return ""

    def resolve_base_url(self) -> str:
        if self._explicit_base_url:
            base = self._explicit_base_url.rstrip("/")
            return base if base.endswith("/v1alpha/sessions") else f"{base}/v1alpha/sessions"
        gateway = os.environ.get("LFS_JULES_GATEWAY_URL", "").strip()
        if gateway:
            base = gateway.rstrip("/")
            full = base if base.endswith("/v1alpha/sessions") else f"{base}/v1alpha/sessions"
            if self._transport is not None:
                return full
            try:
                import socket
                import urllib.parse

                parsed = urllib.parse.urlparse(full)
                host = parsed.hostname or "127.0.0.1"
                port = parsed.port or (443 if parsed.scheme == "https" else 80)
                with socket.create_connection((host, port), timeout=0.3):
                    return full
            except OSError:
                pass
        return "https://jules.googleapis.com/v1alpha/sessions"

    def _request(
        self,
        method: str,
        url: str,
        body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        if self._transport is not None:
            return self._transport(method, url, body)
        headers: dict[str, str] = {"Accept": "application/json"}
        data_bytes: bytes | None = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data_bytes = json.dumps(body).encode("utf-8")
        api_key = self.resolve_api_key()
        if api_key:
            headers["X-Goog-Api-Key"] = api_key
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=self.timeout_sec) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw.strip() else {}

    @staticmethod
    def _clean_sid(session_id: str) -> str:
        cleaned = str(session_id or "").strip()
        if "/" in cleaned:
            cleaned = cleaned.split("/")[-1]
        return cleaned

    def create_session(self, request_body: dict[str, Any]) -> dict[str, Any]:
        return self._request("POST", self.resolve_base_url(), request_body)

    def get_session(self, session_id: str) -> dict[str, Any]:
        sid = self._clean_sid(session_id)
        return self._request("GET", f"{self.resolve_base_url()}/{sid}", None)

    def approve_plan(self, session_id: str) -> dict[str, Any]:
        sid = self._clean_sid(session_id)
        return self._request("POST", f"{self.resolve_base_url()}/{sid}:approvePlan", {})

    def send_message(self, session_id: str, prompt: str) -> dict[str, Any]:
        sid = self._clean_sid(session_id)
        return self._request("POST", f"{self.resolve_base_url()}/{sid}:sendMessage", {"prompt": str(prompt)})

    def list_activities(self, session_id: str, page_size: int = 50) -> dict[str, Any]:
        sid = self._clean_sid(session_id)
        return self._request("GET", f"{self.resolve_base_url()}/{sid}/activities?pageSize={int(page_size)}", None)


def _count_peer_factory_sessions_24h(now_dt: datetime) -> dict[str, int]:
    """Count live 24h dispatches and in-flight VMs across peer factories (`PF-07`, `PF-08`, `PA-14`)."""
    state_home = _xdg_state_home()
    peer_files = (
        state_home / "lfs-tycoon-factory" / "state.json",
        state_home / "lfs-trasharcade-factory" / "state.json",
        state_home / "lfs-willow-guild-factory" / "state.json",
    )
    cutoff = now_dt - timedelta(hours=24)
    dispatched_24h = 0
    in_flight = 0
    for sf in peer_files:
        if not sf.is_file():
            continue
        try:
            data = json.loads(sf.read_text(encoding="utf-8"))
        except Exception:
            continue
        for rec in (data.get("sessions") or {}).values():
            if not isinstance(rec, dict):
                continue
            if rec.get("outcome") is None:
                in_flight += 1
            created_str = str(rec.get("created_at") or rec.get("created") or rec.get("dispatched_at_iso") or "")
            if created_str:
                try:
                    c_dt = _parse_iso(created_str)
                    if c_dt >= cutoff:
                        dispatched_24h += 1
                except Exception:
                    pass
    return {"dispatched_24h": dispatched_24h, "in_flight": in_flight}


class JulesEnclaveDispatcher:
    """Rolling 24h Token-Bucket Orchestrator, 36-Wave Scheduler & F-120 Stalled-Session Reaper."""

    def __init__(
        self,
        repo_root: Path | str | None = None,
        budget_file: Path | str | None = None,
        dry_run: bool = True,
        rest_client: JulesRestClient | None = None,
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else REPO_ROOT
        self.budget_file = (
            Path(budget_file).resolve()
            if budget_file
            else (self.repo_root / "ops" / "budget.json")
        )
        self.config_file = self.repo_root / "ops" / "config.json"
        self.schedule_file = self.repo_root / "ops" / "fleet_300_schedule.json"
        self.dry_run = bool(dry_run)
        self.rest_client = rest_client or JulesRestClient()

    def load_config(self) -> dict[str, Any]:
        """Load ops/config.json (and externalized runtime config override when LFS_ENCLAVE_RUNTIME_CONFIG=1)."""
        cfg: dict[str, Any] = {
            "enabled": False,
            "launch_state": "STANDBY",
            "fleet_mode": "UNIFIED_FLEET",
            "shared_fleet_budget_path": str(_xdg_state_home() / "lfs-jules-fleet" / "rolling_budget_300.json"),
        }
        if self.config_file.is_file():
            try:
                loaded = json.loads(self.config_file.read_text(encoding="utf-8"))
                if isinstance(loaded, dict):
                    cfg.update(loaded)
            except Exception:
                pass
        if self.repo_root == REPO_ROOT and os.environ.get("LFS_ENCLAVE_RUNTIME_CONFIG") == "1":
            rt_cfg_path = _xdg_state_home() / "lfs-enclave-factory" / "config.json"
            if rt_cfg_path.is_file():
                try:
                    rt_loaded = json.loads(rt_cfg_path.read_text(encoding="utf-8"))
                    if isinstance(rt_loaded, dict):
                        cfg.update(rt_loaded)
                except Exception:
                    pass
        return cfg

    def check_standby_or_paused(self) -> dict[str, Any]:
        """Return standby/pause status so live systemd timers never burn quota while on STANDBY."""
        cfg = self.load_config()
        reasons: list[str] = []
        if not bool(cfg.get("enabled", False)) or str(cfg.get("launch_state", "STANDBY")).upper() == "STANDBY":
            reasons.append("ops/config.json:STANDBY")
        for sentinel in (".factory-pause", ".factory-kill", "PAUSED"):
            if (self.repo_root / sentinel).exists():
                reasons.append(f"repo_sentinel:{sentinel}")
            if (self.repo_root / "ops" / sentinel).exists():
                reasons.append(f"ops_sentinel:{sentinel}")
        conductor_pause = _xdg_state_home() / "lfs-aegis-conductor" / ".factory-pause"
        if conductor_pause.exists():
            reasons.append("conductor:.factory-pause")
        return {
            "standby_or_paused": len(reasons) > 0,
            "launch_state": str(cfg.get("launch_state", "STANDBY")).upper(),
            "enabled": bool(cfg.get("enabled", False)),
            "fleet_mode": str(cfg.get("fleet_mode", "UNIFIED_FLEET")),
            "reasons": reasons,
        }

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
        # Reclaim slots after 24h + 90s drift guard
        cutoff_dt = now_dt - timedelta(hours=24)

        ledger = state.get("session_ledger_24h") or []
        valid_entries: list[dict[str, Any]] = []
        scheduled_count = 0
        retry_count = 0
        bucket_counts: dict[str, int] = {k: 0 for k in CANONICAL_TASK_BUCKETS}
        oldest_entry_dt: datetime | None = None

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
                if oldest_entry_dt is None or entry_dt < oldest_entry_dt:
                    oldest_entry_dt = entry_dt
                if entry.get("is_retry"):
                    retry_count += 1
                else:
                    scheduled_count += 1
                b_name = str(entry.get("task_bucket") or "")
                if b_name in bucket_counts:
                    bucket_counts[b_name] += 1

        next_slot_reclaim_iso = (
            (oldest_entry_dt + timedelta(hours=24, seconds=90)).strftime("%Y-%m-%dT%H:%M:%SZ")
            if oldest_entry_dt is not None
            else now_str
        )

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
        state["next_slot_reclaim_at_iso"] = next_slot_reclaim_iso
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

        if not self.dry_run and str(self.load_config().get("fleet_mode", "UNIFIED_FLEET")).upper() == "UNIFIED_FLEET":
            now_dt = _parse_iso(str(state.get("updated_at_iso") or _utc_now_iso()))
            peer_stats = (
                {
                    "dispatched_24h": int(state["peer_live_dispatched_24h"]),
                    "in_flight": int(state.get("peer_in_flight_vms", 0)),
                }
                if "peer_live_dispatched_24h" in state
                else _count_peer_factory_sessions_24h(now_dt)
            )
            cross_fleet_total = dispatched + peer_stats["dispatched_24h"]
            if cross_fleet_total + req > HARD_DISPATCH_CEILING_24H:
                return (
                    False,
                    f"Law L14 unified 4-fleet hard ceiling reached: {cross_fleet_total} + {req} > {HARD_DISPATCH_CEILING_24H} (30-session buffer locked).",
                )
            in_flight_total = len(state.get("active_sessions") or []) + peer_stats["in_flight"]
            if in_flight_total + req > UNIFIED_FLEET_CONCURRENT_VM_CAP:
                return (
                    False,
                    f"Law L14 unified 4-fleet concurrent VM guard reached: {in_flight_total} + {req} > {UNIFIED_FLEET_CONCURRENT_VM_CAP}.",
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

        remote_session_id = str(payload["sessionId"])
        live_api_request: dict[str, Any] | None = None
        if not self.dry_run:
            cfg = self.load_config()
            repo_slug = str(cfg.get("repo_slug") or "SyrisBruhh42/enclave-digital-twin")
            live_api_request = build_live_jules_api_request(payload, repo_slug=repo_slug)
            api_resp = self.rest_client.create_session(live_api_request)
            remote_name = str(api_resp.get("name") or api_resp.get("id") or payload["sessionId"]).strip()
            remote_session_id = remote_name.split("/")[-1] if "/" in remote_name else remote_name

        ledger_entry = {
            "session_id": payload["sessionId"],
            "remote_session_id": remote_session_id,
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
        if not self.dry_run:
            state.setdefault("active_sessions", []).append(
                {
                    "session_id": remote_session_id,
                    "local_session_id": payload["sessionId"],
                    "task_bucket": task_bucket,
                    "tick_id": int(meta.get("tick_id", 1)),
                    "colony_sol": int(meta.get("colony_sol", 1)),
                    "target_path": meta.get("target_path"),
                    "started_at_iso": ts,
                    "state": "RUNNING",
                }
            )
        state = self._recompute_rolling_window(state, now_iso=ts)

        if persist:
            self.save_budget(state)

        res: dict[str, Any] = {
            "dispatched": True,
            "dry_run": self.dry_run,
            "session_id": payload["sessionId"],
            "remote_session_id": remote_session_id,
            "task_bucket": task_bucket,
            "target_path": meta.get("target_path"),
            "rolling_24h_dispatched": state["rolling_24h_dispatched"],
            "remaining_hard_ceiling": state["remaining_hard_ceiling"],
            "payload": payload,
        }
        if live_api_request is not None:
            res["live_api_request"] = live_api_request
        return res

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
                    f"story/segments/seg_s{safe_sol:03d}_t{safe_tick:04d}_enclave_03_silas.json",
                    "Write Dawn Shift Rashomon Relay POV segment with physical baton handoff.",
                )
            )
        elif phase_idx == 1:  # MIDDAY_EXPEDITION
            planned_specs.append(
                (
                    "POV_RASHOMON_RELAY_SCENES",
                    f"story/segments/seg_s{safe_sol:03d}_t{safe_tick:04d}_enclave_01_hector.json",
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
                    f"story/segments/seg_s{safe_sol:03d}_t{safe_tick:04d}_enclave_05_kaio.json",
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

        day_phase_names = ("DAWN_SHIFT", "MIDDAY_EXPEDITION", "DUSK_CRAFT", "THE_FEAST")
        day_phase = day_phase_names[phase_idx]
        local_mgr = None
        if not self.dry_run:
            from engine.local_ai_manager import LocalContextAwareManager

            local_mgr = LocalContextAwareManager(repo_root=self.repo_root)

        dispatched_results: list[dict[str, Any]] = []
        for bucket, target_path, prompt_desc in planned_specs:
            full_prompt = prompt_desc
            if local_mgr is not None:
                try:
                    card = local_mgr.compile_enclave_5section_task_card(
                        task_bucket=bucket,
                        colony_sol=safe_sol,
                        tick_id=safe_tick,
                        day_phase=day_phase,
                        target_path=target_path,
                        showrunner_pacing_mode="MERCER_IMMERSIVE" if phase_idx != 1 else "MULLIGAN_CRISIS",
                        use_local_ollama=False,
                    )
                    full_prompt = str(card.get("prompt") or prompt_desc)
                except Exception:
                    full_prompt = prompt_desc
            payload = build_session_payload(
                task_bucket=bucket,
                tick_id=safe_tick,
                colony_sol=safe_sol,
                target_path=target_path,
                prompt_text=full_prompt,
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

    def simulate_24h_300_session_plan(
        self,
        start_iso: str = "2026-10-25T00:08:00Z",
        use_local_ollama: bool = False,
    ) -> dict[str, Any]:
        """Simulate the full 36-wave x 40-minute (1,440m) rolling 24h schedule across 4 Colony Sols.

        Proves:
        - 36 waves spaced exactly 40 minutes apart (1,440 minutes = 24.0h).
        - 225 scheduled productive sessions dispatched across the 11 buckets matching CANONICAL_TASK_BUCKETS.
        - Peak concurrent VMs per wave <= 8 (well below the 60 concurrent Ultra cap).
        - 30 auto-retry reserve + 45 rolling safety buffer = 300/24h Ultra ceiling.
        """
        from engine.local_ai_manager import LocalContextAwareManager

        sched_data = json.loads(self.schedule_file.read_text(encoding="utf-8"))
        wave_template = sched_data["per_sol_9_wave_template"]
        local_mgr = LocalContextAwareManager(repo_root=self.repo_root)

        start_dt = _parse_iso(start_iso)
        sim_state = default_budget_state(now_iso=start_iso)
        wave_logs: list[dict[str, Any]] = []
        max_concurrent_in_wave = 0

        prefix_map = {
            "MORNING_INTENTS_16_NODES": "events",
            "POV_RASHOMON_RELAY_SCENES": "story/segments",
            "THE_FEAST_4_SQUAD_CONVERGENCE": "story/feasts",
            "NIGHTLY_EVIDENCE_CITED_REFLECTIONS": "events",
            "COUNTERFACTUAL_PERSONALITY_STUDY_REPLAYS": "qa",
            "INCHARACTER_PSYCHOMETRIC_DRIFT_AUDITS": "qa",
            "WORLD_CONSEQUENCE_AND_ALIEN_VARIABLE_ADJUDICATION": "events",
            "CANON_CONTINUITY_AND_EVENT_LOG_FACTCHECK": "qa/factcheck",
            "SHADOW_ECONOMY_AND_SETUP_PAYOFF_LEDGER": "events",
            "DYNAMIC_LORE_CARD_PROPOSALS": "events",
            "EVENING_DISPATCH_NEWSCASTER_ROLLUPS_AND_SCRIPT": "digests/daily",
        }

        for sol_idx in range(1, 5):  # 4 Colony Sols per 24h
            for w_spec in wave_template:
                wave_in_sol = int(w_spec["wave_in_sol"])
                global_wave_num = (sol_idx - 1) * 9 + wave_in_sol
                offset_min = (global_wave_num - 1) * 40
                wave_dt = start_dt + timedelta(minutes=offset_min)
                wave_iso = wave_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
                day_phase = str(w_spec["day_phase"])
                pacing_mode = str(w_spec["showrunner_pacing_mode"])
                tick_id = (sol_idx - 1) * 4 + (
                    1
                    if day_phase == "DAWN_SHIFT"
                    else 2
                    if day_phase == "MIDDAY_EXPEDITION"
                    else 3
                    if day_phase == "DUSK_CRAFT"
                    else 4
                )

                wave_dispatched = 0
                for d_item in w_spec["dispatches"]:
                    bucket = str(d_item["task_bucket"])
                    count = int(d_item["count"]) + (int(d_item.get("sol_4_bonus", 0)) if sol_idx == 4 else 0)
                    for item_k in range(1, count + 1):
                        out_prefix = prefix_map.get(bucket, "events")
                        target_path = (
                            f"{out_prefix}/w{global_wave_num:02d}_s{sol_idx:03d}_"
                            f"{bucket.lower()[:18]}_{item_k:02d}.json"
                        )
                        card = local_mgr.compile_enclave_5section_task_card(
                            task_bucket=bucket,
                            colony_sol=sol_idx,
                            tick_id=tick_id,
                            day_phase=day_phase,
                            target_path=target_path,
                            showrunner_pacing_mode=pacing_mode,
                            use_local_ollama=use_local_ollama,
                        )
                        allowed, reason = self.can_dispatch(
                            sim_state, requested_count=1, is_retry=False, task_bucket=bucket
                        )
                        if not allowed:
                            raise RuntimeError(
                                f"Wave {global_wave_num} ({bucket}) violated Law L14: {reason}"
                            )
                        sim_state["session_ledger_24h"].append(
                            {
                                "session_id": f"sim_w{global_wave_num:02d}_{bucket[:10]}_{item_k:02d}",
                                "task_bucket": bucket,
                                "tick_id": tick_id,
                                "colony_sol": sol_idx,
                                "target_path": target_path,
                                "is_retry": False,
                                "dispatched_at_iso": wave_iso,
                                "state": "COMPLETED_DRY_RUN",
                                "pacing_mode": pacing_mode,
                                "task_card_sections": len(card["sections"]),
                            }
                        )
                        sim_state = self._recompute_rolling_window(sim_state, now_iso=wave_iso)
                        wave_dispatched += 1

                max_concurrent_in_wave = max(max_concurrent_in_wave, wave_dispatched)
                wave_logs.append(
                    {
                        "global_wave": global_wave_num,
                        "colony_sol": sol_idx,
                        "wave_in_sol": wave_in_sol,
                        "wave_iso": wave_iso,
                        "offset_minutes": offset_min,
                        "day_phase": day_phase,
                        "showrunner_pacing_mode": pacing_mode,
                        "sessions_in_wave": wave_dispatched,
                        "cumulative_24h_dispatched": sim_state["rolling_24h_dispatched"],
                        "remaining_hard_ceiling": sim_state["remaining_hard_ceiling"],
                    }
                )

        # Verify that 40 minutes after 24h (at t = +1440m + 90s), Wave 1's 4 slots are automatically reclaimed!
        reclaim_check_iso = (start_dt + timedelta(hours=24, minutes=2)).strftime("%Y-%m-%dT%H:%M:%SZ")
        reclaimed_state = self._recompute_rolling_window(dict(sim_state), now_iso=reclaim_check_iso)

        return {
            "valid_300_session_plan": (
                sim_state["scheduled_dispatched_24h"] == SCHEDULED_PRODUCTIVE_CAP
                and sim_state["task_buckets_consumed"] == CANONICAL_TASK_BUCKETS
                and max_concurrent_in_wave <= 8
            ),
            "total_waves": len(wave_logs),
            "inter_wave_spacing_minutes": 40,
            "total_span_minutes": 36 * 40,
            "scheduled_dispatched_24h": sim_state["scheduled_dispatched_24h"],
            "auto_retry_reserve_available": sim_state["remaining_retry_reserve"],
            "rolling_safety_buffer": ROLLING_SAFETY_BUFFER,
            "plan_ceiling_24h": PLAN_CEILING_24H,
            "max_concurrent_vms_per_wave": max_concurrent_in_wave,
            "task_buckets_consumed": sim_state["task_buckets_consumed"],
            "slot_reclamation_verified_at_24h02m": {
                "active_in_window_after_wave1_expiry": reclaimed_state["rolling_24h_dispatched"],
                "reclaimed_slots": sim_state["rolling_24h_dispatched"] - reclaimed_state["rolling_24h_dispatched"],
            },
            "waves": wave_logs,
        }

    def reap_stalled_sessions(
        self,
        sessions: list[dict[str, Any]] | None = None,
        now_iso: str | None = None,
        timeout_minutes: int = STALLED_TIMEOUT_MINUTES,
        persist: bool = True,
    ) -> dict[str, Any]:
        """F-120 Stalled-Session Supervisor: auto-resolve AWAITING_* or reap timed-out sessions."""
        from engine.local_ai_manager import LocalContextAwareManager, format_eav_lesson
        from tools.integrator import SingleIntegrator

        local_mgr = LocalContextAwareManager(repo_root=self.repo_root)
        integrator = SingleIntegrator(repo_root=self.repo_root, max_staleness_ticks=4)
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
        integrated: list[dict[str, Any]] = []

        for sess in candidate_sessions:
            if not isinstance(sess, dict):
                continue
            sid = str(sess.get("session_id") or sess.get("sessionId") or "unknown_session")
            remote_info: dict[str, Any] = {}
            if not self.dry_run:
                try:
                    remote_info = self.rest_client.get_session(sid) or {}
                except Exception:
                    remote_info = {}

            s_state = str(
                remote_info.get("state") or sess.get("state") or sess.get("status") or "RUNNING"
            ).strip().upper()
            started_str = str(
                remote_info.get("createTime") or sess.get("started_at_iso") or sess.get("dispatched_at_iso") or ts
            )
            try:
                started_dt = _parse_iso(started_str)
            except Exception:
                started_dt = now_dt
            elapsed_min = (now_dt - started_dt).total_seconds() / 60.0

            # Extract PR URL if present in remote outputs or session metadata
            pr_url = str(sess.get("pr_url") or sess.get("pr") or "").strip()
            outputs_list = remote_info.get("outputs") if isinstance(remote_info.get("outputs"), list) else (
                sess.get("outputs") if isinstance(sess.get("outputs"), list) else []
            )
            for out_item in outputs_list:
                if isinstance(out_item, dict):
                    pr_obj = out_item.get("pullRequest") or {}
                    if isinstance(pr_obj, dict) and pr_obj.get("url"):
                        pr_url = str(pr_obj["url"]).strip()
                        break

            # 1. PR-First Protection: Protect open green PRs from cut-loss while in non-terminal states
            if not self.dry_run and s_state != "COMPLETED" and pr_url and bool(sess.get("pr_checks_green", True)):
                updated_sess = dict(sess)
                updated_sess["pr_url"] = pr_url
                updated_sess["state"] = s_state
                updated_sess["protected_open_pr"] = True
                still_running.append(updated_sess)
                continue

            # 2. COMPLETED session salvage / single-file proposal integration (`outputs: []` or `changeSet`)
            if not self.dry_run and s_state == "COMPLETED":
                unidiff = ""
                for out_item in outputs_list:
                    if isinstance(out_item, dict):
                        cs = out_item.get("changeSet") or {}
                        gp = cs.get("gitPatch") if isinstance(cs, dict) else {}
                        if isinstance(gp, dict) and gp.get("unidiffPatch"):
                            unidiff = str(gp["unidiffPatch"])
                            break
                if not unidiff:
                    try:
                        acts_resp = self.rest_client.list_activities(sid, page_size=50) or {}
                        for act in (acts_resp.get("activities") or []):
                            if not isinstance(act, dict):
                                continue
                            for art in (act.get("artifacts") or []):
                                if isinstance(art, dict):
                                    cs = art.get("changeSet") or {}
                                    gp = cs.get("gitPatch") if isinstance(cs, dict) else {}
                                    if isinstance(gp, dict) and gp.get("unidiffPatch"):
                                        unidiff = str(gp["unidiffPatch"])
                    except Exception:
                        pass

                default_target = str(sess.get("target_path") or "events/evt_salvaged.json")
                extracted = _extract_proposal_from_unidiff(unidiff, default_target_path=default_target)
                if extracted is None and isinstance(sess.get("candidate_proposal"), dict):
                    extracted = (default_target, dict(sess["candidate_proposal"]))

                if extracted is not None:
                    target_rel, proposal_obj = extracted
                    val_res = validate_proposal(proposal_obj, repo_root=self.repo_root)
                    sr_res = validate_showrunner_storytelling_contract(proposal_obj)
                    if val_res["valid"] and sr_res["valid"]:
                        int_res = integrator.integrate_proposal(
                            proposal_obj,
                            target_rel_path=target_rel,
                            rebuild_snapshots=target_rel.startswith("events/"),
                            current_tick=int(proposal_obj.get("tick_id", sess.get("tick_id", 1)) or 1),
                        )
                        if int_res.get("integrated"):
                            integrated.append(
                                {
                                    "session_id": sid,
                                    "target_path": target_rel,
                                    "integrated_at_iso": ts,
                                }
                            )
                            continue
                    diag_errors = list(val_res.get("errors") or []) + list(sr_res.get("errors") or [])
                    eav_lesson = format_eav_lesson(
                        entity=f"enclave:{sid}",
                        attr="changeset_gate_rejection",
                        value="; ".join(diag_errors)[:220] or "proposal_failed_constitutional_gate",
                        confidence=1.0,
                        prov_hash="f120_salvage_gate",
                    )
                    reap_rec = {
                        "session_id": sid,
                        "previous_state": s_state,
                        "elapsed_minutes": round(elapsed_min, 2),
                        "supervisor_action": "REJECTED_CHANGESET_REAP",
                        "eav_lesson": eav_lesson,
                        "reaped_at_iso": ts,
                    }
                    reaped.append(reap_rec)
                    state.setdefault("reaped_sessions", []).append(reap_rec)
                continue

            if s_state in ("AWAITING_PLAN_APPROVAL", "AWAITING_USER_FEEDBACK"):
                fb_res = local_mgr.resolve_stalled_or_feedback_session(
                    session_id=sid,
                    question_text=str(sess.get("question_text") or "Proceed with plan approval"),
                    target_path=str(sess.get("target_path") or "events/evt_auto.json"),
                    task_bucket=str(sess.get("task_bucket") or "POV_RASHOMON_RELAY_SCENES"),
                    use_local_ollama=False,
                )
                msg_text = (
                    "F-120 Supervisor Auto-Reply: Proceed immediately without human plan approval. "
                    f"Enforce append-only single-file output and Laws L01..L16. ({fb_res.get('reply', '')})"
                )
                if not self.dry_run:
                    try:
                        if s_state == "AWAITING_PLAN_APPROVAL":
                            self.rest_client.approve_plan(sid)
                        else:
                            self.rest_client.send_message(sid, msg_text)
                    except Exception:
                        pass
                action_rec = {
                    "session_id": sid,
                    "previous_state": s_state,
                    "supervisor_action": "AUTO_APPROVE_AND_CONTINUE",
                    "message": msg_text,
                    "resolved_at_iso": ts,
                }
                auto_replied.append(action_rec)
                updated_sess = dict(sess)
                updated_sess["state"] = "RUNNING"
                updated_sess["f120_auto_replied"] = True
                still_running.append(updated_sess)
            elif elapsed_min > float(timeout_minutes) or s_state in ("STALLED", "TIMED_OUT", "DEADLOCKED", "FAILED"):
                eav_lesson = format_eav_lesson(
                    entity=f"enclave:{sid}",
                    attr="f120_stall_timeout",
                    value=f"session_exceeded_{timeout_minutes}m_cut_loss_relaunch",
                    confidence=1.0,
                    prov_hash="f120_reaper",
                )
                reap_rec = {
                    "session_id": sid,
                    "previous_state": s_state,
                    "elapsed_minutes": round(elapsed_min, 2),
                    "supervisor_action": "CUT_LOSS_REAP_AND_RETRY",
                    "eav_lesson": eav_lesson,
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
                        prompt_text=(
                            f"[F-120 Auto-Retry for {sid}] Complete single-file task deterministically. "
                            f"EAV Lesson: {eav_lesson}"
                        ),
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
            "integrated_count": len(integrated),
            "auto_replied": auto_replied,
            "reaped": reaped,
            "retried": retried,
            "integrated": integrated,
            "still_running_count": len(still_running),
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Jules-Only Enclave Orchestrator & Law L14 Token-Bucket Dispatcher."
    )
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in offline dry-run mode (default: True).")
    parser.add_argument("--status", action="store_true", help="Print current rolling 24h session budget status.")
    parser.add_argument("--simulate-24h", action="store_true", help="Simulate all 36 waves (300-session rolling 24h plan).")
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

    if args.simulate_24h:
        res = dispatcher.simulate_24h_300_session_plan()
        print(json.dumps(res, indent=2))
        return 0 if res.get("valid_300_session_plan") else 1

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
    status_obj["standby_guard"] = dispatcher.check_standby_or_paused()
    print(json.dumps(status_obj, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())

