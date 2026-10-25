#!/usr/bin/env python3
"""Single Integrator & Deterministic Event-Sourced State Rebuilder (WP-5).

Enforces the Single-Integrator serialization contract:
1. Validates every incoming worker session proposal against Constitutional Laws L01..L16.
2. Verifies `base_snapshot_tick` staleness against the current latest tick.
3. Writes the single append-only file (`events/`, `story/segments/`, `story/feasts/`, `digests/`, `qa/`).
4. Deterministically regenerates `snapshots/tick_XXXX.json`, `snapshots/latest.json`, and
   `relationships/graph.json` strictly from the append-only `events/` log and canonical cores.
5. Provides `rebuild_state_from_events()` and `rollback_to_tick(tick_id)` for 100% self-repair.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.chronosphere import build_chronosphere_for_tick
from engine.magneto_weather import compute_exoplanet_weather
from engine.state_ode import sample_character_state
from tools.check_enclave_constitutions import (
    ALLOWED_WORKER_PREFIXES,
    check_baton_handoff_continuity,
    check_dispatch_claim_event_citations,
    check_feast_daily_convergence,
    validate_proposal,
)

DEFAULT_EPOCH_SEED = "enclave_epoch_2026"
DEFAULT_MAX_STALENESS_TICKS = 1


def _resolve_root(repo_root: Path | str | None = None) -> Path:
    return Path(repo_root).resolve() if repo_root else REPO_ROOT


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def _load_character_cores(root: Path) -> dict[str, dict[str, Any]]:
    cores: dict[str, dict[str, Any]] = {}
    char_dir = root / "canon" / "characters"
    if not char_dir.is_dir():
        return cores
    for p in sorted(char_dir.glob("*.core.json")):
        card = _load_json(p)
        ident = card.get("agent_identity") or {}
        cid = str(ident.get("character_id") or card.get("character_id") or p.stem.replace(".core", ""))
        cores[cid] = card
    return cores


def _load_initial_relationships(root: Path) -> dict[str, Any]:
    rel_path = root / "relationships" / "initial_matrix_120.json"
    if not rel_path.is_file():
        return {"schema_version": "relationship_matrix_v2.0.0", "total_pairs": 0, "pairs": []}
    return copy.deepcopy(_load_json(rel_path))


def _load_all_events(root: Path, up_to_tick: int | None = None) -> list[dict[str, Any]]:
    events_dir = root / "events"
    if not events_dir.is_dir():
        return []
    events: list[dict[str, Any]] = []
    for p in sorted(events_dir.glob("*.json")):
        try:
            ev = _load_json(p)
            if not isinstance(ev, dict):
                continue
            t_id = int(ev.get("tick_id", 1) or 1)
            if up_to_tick is not None and t_id > int(up_to_tick):
                continue
            events.append(ev)
        except Exception:
            continue
    events.sort(key=lambda e: (int(e.get("tick_id", 1) or 1), str(e.get("event_id") or "")))
    return events


def _apply_state_deltas_to_char(
    char_state: dict[str, Any],
    deltas: dict[str, Any],
) -> dict[str, Any]:
    updated = copy.deepcopy(char_state)
    trait_states = dict(updated.get("trait_states") or {})

    for k, val in deltas.items():
        if not isinstance(val, (int, float)):
            continue
        fval = float(val)
        if k in ("stress_delta", "delta_stress"):
            updated["stress"] = round(min(1.0, max(0.0, float(updated.get("stress", 0.30)) + fval)), 4)
        elif k in ("fatigue_delta", "delta_fatigue"):
            new_f = round(min(1.0, max(0.0, float(updated.get("fatigue", 0.20)) + fval)), 4)
            updated["fatigue"] = new_f
            updated["sleep_debt_norm"] = new_f
        elif k in ("stress", "fatigue", "sleep_debt_norm"):
            updated[k] = round(min(1.0, max(0.0, fval)), 4)
        else:
            base_dim = k.replace("_delta", "").replace("_state", "")
            if base_dim in (
                "openness",
                "conscientiousness",
                "extraversion",
                "agreeableness",
                "neuroticism",
                "hexaco_honesty_humility",
            ):
                if k.endswith("_delta"):
                    cur = float(trait_states.get(base_dim, updated.get(base_dim, 0.50)))
                    new_v = round(min(1.0, max(0.0, cur + fval)), 4)
                else:
                    new_v = round(min(1.0, max(0.0, fval)), 4)
                trait_states[base_dim] = new_v
                updated[base_dim] = new_v
                updated[f"{base_dim}_state"] = new_v

    updated["trait_states"] = trait_states
    return updated


def _apply_relationship_deltas(
    rel_graph: dict[str, Any],
    rel_deltas: Any,
    event_id: str,
) -> None:
    pairs = rel_graph.get("pairs") or []
    pair_map: dict[tuple[str, str], dict[str, Any]] = {}
    for p in pairs:
        a = str(p.get("agent_a") or p.get("character_a") or "")
        b = str(p.get("agent_b") or p.get("character_b") or "")
        if a and b:
            key = (min(a, b), max(a, b))
            pair_map[key] = p

    delta_items: list[dict[str, Any]] = []
    if isinstance(rel_deltas, list):
        delta_items = [d for d in rel_deltas if isinstance(d, dict)]
    elif isinstance(rel_deltas, dict):
        for k, v in rel_deltas.items():
            if isinstance(v, dict):
                item = dict(v)
                item.setdefault("pair_id", k)
                delta_items.append(item)
            elif isinstance(v, (int, float)) and "__" in k:
                parts = k.split("__", 1)
                delta_items.append({"from": parts[0], "to": parts[1], "bond_delta": float(v)})

    for d in delta_items:
        a = str(d.get("from") or d.get("agent_a") or d.get("character_a") or "")
        b = str(d.get("to") or d.get("agent_b") or d.get("character_b") or "")
        if not (a and b) and "__" in str(d.get("pair_id") or ""):
            a, b = str(d["pair_id"]).split("__", 1)
        if not (a and b) or a == b:
            continue
        key = (min(a, b), max(a, b))
        target_pair = pair_map.get(key)
        if not target_pair:
            continue

        bond_delta = float(
            d.get("bond_delta", d.get("bond_strength_delta", d.get("affectionate_exasperation_delta", 0.0))) or 0.0
        )
        trust_delta = float(d.get("trust_delta", 0.0) or 0.0)
        friction_delta = float(d.get("friction_delta", d.get("intellectual_friction_delta", 0.0)) or 0.0)

        # Law L11: PvE loving family floor >= 0.35
        target_pair["bond_strength"] = round(
            min(1.0, max(0.35, float(target_pair.get("bond_strength", 0.75)) + bond_delta)), 4
        )
        target_pair["trust"] = round(
            min(1.0, max(0.35, float(target_pair.get("trust", 0.80)) + trust_delta)), 4
        )
        target_pair["intellectual_friction"] = round(
            min(1.0, max(0.0, float(target_pair.get("intellectual_friction", 0.35)) + friction_delta)), 4
        )
        citations = target_pair.setdefault("evidence_refs", [])
        if event_id and event_id not in citations:
            citations.append(event_id)


def rebuild_state_from_events(
    repo_root: Path | str | None = None,
    up_to_tick: int | None = None,
    epoch_seed: str = DEFAULT_EPOCH_SEED,
    write_files: bool = True,
) -> dict[str, Any]:
    """Deterministically reconstruct snapshots and relationships/graph.json from append-only events/."""
    root = _resolve_root(repo_root)
    cores = _load_character_cores(root)
    rel_graph = _load_initial_relationships(root)
    events = _load_all_events(root, up_to_tick=up_to_tick)

    max_event_tick = max((int(e.get("tick_id", 1) or 1) for e in events), default=1)
    target_tick = int(up_to_tick) if up_to_tick is not None else max_event_tick
    target_tick = max(1, target_tick)

    events_by_tick: dict[int, list[dict[str, Any]]] = {}
    for ev in events:
        t = int(ev.get("tick_id", 1) or 1)
        events_by_tick.setdefault(t, []).append(ev)

    prev_char_states: dict[str, dict[str, Any]] = {}
    for cid, card in cores.items():
        tier3 = card.get("tier_3_momentary_state_and_override_physics") or {}
        prev_char_states[cid] = copy.deepcopy(tier3.get("current_state_vector") or {"tick_id": 0, "stress": 0.30, "fatigue": 0.20})

    snapshots_by_tick: dict[int, dict[str, Any]] = {}
    snapshots_dir = root / "snapshots"
    if write_files:
        snapshots_dir.mkdir(parents=True, exist_ok=True)

    for tick in range(1, target_tick + 1):
        chrono = build_chronosphere_for_tick(tick_id=tick, epoch_seed=epoch_seed)
        colony_sol = int(chrono["colony_sol"])
        day_phase = str(chrono["day_phase"])
        weather = compute_exoplanet_weather(
            tick_id=tick,
            colony_sol=colony_sol,
            day_phase=day_phase,
            epoch_seed=epoch_seed,
        )

        tick_events = events_by_tick.get(tick, [])
        current_char_states: dict[str, dict[str, Any]] = {}

        for cid, card in sorted(cores.items()):
            sampled = sample_character_state(
                core_card=card,
                prev_state=prev_char_states.get(cid, {}),
                world_slice=weather,
                active_situation={"tick_id": tick, "colony_sol": colony_sol, "day_phase": day_phase},
                rng_seed=f"{epoch_seed}:tick_{tick:04d}:{cid}",
            )
            current_char_states[cid] = sampled

        # Apply deterministic event deltas recorded on this tick
        for ev in tick_events:
            ev_id = str(ev.get("event_id") or "")
            s_deltas = ev.get("state_deltas") or {}
            actors = [str(a) for a in (ev.get("actors") or []) if a]

            if isinstance(s_deltas, dict) and s_deltas:
                # Check if keyed by character_id or flat delta applied to actors
                has_char_subdicts = any(k in current_char_states and isinstance(v, dict) for k, v in s_deltas.items())
                if has_char_subdicts:
                    for cid_key, sub_delta in s_deltas.items():
                        if cid_key in current_char_states and isinstance(sub_delta, dict):
                            current_char_states[cid_key] = _apply_state_deltas_to_char(
                                current_char_states[cid_key], sub_delta
                            )
                else:
                    for actor_id in actors:
                        if actor_id in current_char_states:
                            current_char_states[actor_id] = _apply_state_deltas_to_char(
                                current_char_states[actor_id], s_deltas
                            )

            r_deltas = ev.get("relationship_deltas")
            if r_deltas:
                _apply_relationship_deltas(rel_graph, r_deltas, ev_id)

        prev_char_states = copy.deepcopy(current_char_states)
        snapshot_obj = {
            "schema_version": "enclave_snapshot_v2.0.0",
            "tick_id": tick,
            "colony_sol": colony_sol,
            "day_phase": day_phase,
            "epoch_seed": epoch_seed,
            "chronosphere": chrono,
            "weather": weather,
            "character_states": current_char_states,
            "applied_event_ids": [str(e.get("event_id")) for e in tick_events if e.get("event_id")],
            "total_events_through_tick": sum(len(events_by_tick.get(t, [])) for t in range(1, tick + 1)),
        }
        snapshots_by_tick[tick] = snapshot_obj
        if write_files:
            _write_json(snapshots_dir / f"tick_{tick:04d}.json", snapshot_obj)

    latest_snapshot = snapshots_by_tick[target_tick]
    rel_graph["updated_at_tick"] = target_tick
    rel_graph["applied_event_count"] = len(events)

    if write_files:
        _write_json(snapshots_dir / "latest.json", latest_snapshot)
        _write_json(root / "relationships" / "graph.json", rel_graph)

    return {
        "latest_tick": target_tick,
        "events_replayed": len(events),
        "latest_snapshot": latest_snapshot,
        "snapshots_by_tick": snapshots_by_tick,
        "relationship_graph": rel_graph,
    }


def rollback_to_tick(
    tick_id: int,
    repo_root: Path | str | None = None,
    epoch_seed: str = DEFAULT_EPOCH_SEED,
    purge_future_files: bool = True,
) -> dict[str, Any]:
    """Roll back the simulation state to `tick_id` and deterministically rebuild snapshots & relationships."""
    target_tick = max(1, int(tick_id))
    root = _resolve_root(repo_root)
    removed_files: list[str] = []

    if purge_future_files:
        events_dir = root / "events"
        if events_dir.is_dir():
            for p in sorted(events_dir.glob("*.json")):
                try:
                    ev = _load_json(p)
                    if isinstance(ev, dict) and int(ev.get("tick_id", 1) or 1) > target_tick:
                        removed_files.append(str(p.relative_to(root)))
                        p.unlink()
                except Exception:
                    continue

        snapshots_dir = root / "snapshots"
        if snapshots_dir.is_dir():
            for sp in sorted(snapshots_dir.glob("tick_*.json")):
                try:
                    snap = _load_json(sp)
                    if isinstance(snap, dict) and int(snap.get("tick_id", 1) or 1) > target_tick:
                        removed_files.append(str(sp.relative_to(root)))
                        sp.unlink()
                except Exception:
                    continue

    rebuilt = rebuild_state_from_events(
        repo_root=root,
        up_to_tick=target_tick,
        epoch_seed=epoch_seed,
        write_files=True,
    )
    rebuilt["rolled_back_to_tick"] = target_tick
    rebuilt["removed_files"] = removed_files
    return rebuilt


class SingleIntegrator:
    """Authoritative Single Integrator serializing worker session outputs."""

    def __init__(
        self,
        repo_root: Path | str | None = None,
        epoch_seed: str = DEFAULT_EPOCH_SEED,
        max_staleness_ticks: int = DEFAULT_MAX_STALENESS_TICKS,
    ) -> None:
        self.repo_root = _resolve_root(repo_root)
        self.epoch_seed = epoch_seed
        self.max_staleness_ticks = max(0, int(max_staleness_ticks))

    def get_current_tick(self) -> int:
        latest_path = self.repo_root / "snapshots" / "latest.json"
        if latest_path.is_file():
            try:
                data = _load_json(latest_path)
                return int(data.get("tick_id", 1) or 1)
            except Exception:
                pass
        events = _load_all_events(self.repo_root)
        if events:
            return max(int(e.get("tick_id", 1) or 1) for e in events)
        return 1

    def check_staleness(
        self,
        proposal: dict[str, Any],
        current_tick: int | None = None,
    ) -> tuple[bool, str]:
        """Verify proposal's `base_snapshot_tick` is within `max_staleness_ticks` of `current_tick`."""
        curr = int(current_tick if current_tick is not None else self.get_current_tick())
        base_tick_raw = proposal.get("base_snapshot_tick")
        if base_tick_raw is None:
            return True, "OK"
        base_tick = int(base_tick_raw)
        if base_tick < 0:
            return False, f"Invalid negative base_snapshot_tick={base_tick}."
        if curr - base_tick > self.max_staleness_ticks:
            return (
                False,
                f"Stale proposal rejected: base_snapshot_tick={base_tick} lags current_tick={curr} "
                f"by > {self.max_staleness_ticks} ticks.",
            )
        return True, "OK"

    def integrate_proposal(
        self,
        proposal: dict[str, Any],
        target_rel_path: str | None = None,
        rebuild_snapshots: bool = True,
        current_tick: int | None = None,
    ) -> dict[str, Any]:
        """Validate a proposal against L01..L16 + staleness, write its append-only file, and rebuild state."""
        payload = copy.deepcopy(proposal)
        resolved_rel = str(
            target_rel_path
            or payload.get("target_path")
            or payload.get("output_path")
            or f"events/{payload.get('event_id', 'evt_unnamed')}.json"
        ).lstrip("./")
        payload["target_path"] = resolved_rel

        if not any(resolved_rel.startswith(pref) for pref in ALLOWED_WORKER_PREFIXES):
            return {
                "integrated": False,
                "violated_laws": ["L02"],
                "errors": [f"Law L02 violation: target_path '{resolved_rel}' outside {ALLOWED_WORKER_PREFIXES}."],
            }

        fresh, stale_msg = self.check_staleness(payload, current_tick=current_tick)
        if not fresh:
            return {
                "integrated": False,
                "stale": True,
                "violated_laws": [],
                "errors": [stale_msg],
            }

        validation = validate_proposal(payload, repo_root=self.repo_root)
        if not validation["valid"]:
            return {
                "integrated": False,
                "stale": False,
                "violated_laws": validation["violated_laws"],
                "errors": validation["errors"],
            }

        dest_path = self.repo_root / resolved_rel
        if dest_path.exists() and payload.get("disallow_overwrite", True):
            return {
                "integrated": False,
                "stale": False,
                "violated_laws": ["L02"],
                "errors": [f"Law L02 violation: append-only target '{resolved_rel}' already exists."],
            }

        # Strip transient wrapper keys before persisting if desired, or keep clean record
        record_to_write = copy.deepcopy(payload)
        record_to_write.pop("disallow_overwrite", None)
        _write_json(dest_path, record_to_write)

        if resolved_rel.startswith("story/segments/"):
            l10_ok, l10_errs = check_baton_handoff_continuity(proposal=None, repo_root=self.repo_root)
            if not l10_ok:
                dest_path.unlink(missing_ok=True)
                return {
                    "integrated": False,
                    "stale": False,
                    "violated_laws": ["L10"],
                    "errors": l10_errs,
                }
        elif resolved_rel.startswith("events/"):
            l13_ok, l13_errs = check_feast_daily_convergence(proposal=None, repo_root=self.repo_root)
            if not l13_ok:
                dest_path.unlink(missing_ok=True)
                return {
                    "integrated": False,
                    "stale": False,
                    "violated_laws": ["L13"],
                    "errors": l13_errs,
                }
        elif resolved_rel.startswith("digests/"):
            l15_ok, l15_errs = check_dispatch_claim_event_citations(proposal=None, repo_root=self.repo_root)
            if not l15_ok:
                dest_path.unlink(missing_ok=True)
                return {
                    "integrated": False,
                    "stale": False,
                    "violated_laws": ["L15"],
                    "errors": l15_errs,
                }

        rebuilt_summary: dict[str, Any] = {}
        if rebuild_snapshots:
            rebuilt = rebuild_state_from_events(
                repo_root=self.repo_root,
                epoch_seed=self.epoch_seed,
                write_files=True,
            )
            rebuilt_summary = {
                "latest_tick": rebuilt["latest_tick"],
                "events_replayed": rebuilt["events_replayed"],
            }

        return {
            "integrated": True,
            "stale": False,
            "target_path": resolved_rel,
            "violated_laws": [],
            "errors": [],
            "rebuild_summary": rebuilt_summary,
        }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enclave of the 16 — Single Integrator & Deterministic State Rebuilder."
    )
    parser.add_argument("--integrate-file", type=str, default=None, help="Proposal JSON file to validate and integrate.")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild snapshots and relationship graph from events/.")
    parser.add_argument("--rollback-to-tick", type=int, default=None, help="Rollback state and events to tick_id.")
    parser.add_argument("--repo-root", type=str, default=None, help="Repository root override.")
    parser.add_argument("--epoch-seed", type=str, default=DEFAULT_EPOCH_SEED, help="Deterministic epoch seed.")
    args = parser.parse_args(argv)

    root = _resolve_root(args.repo_root)

    if args.rollback_to_tick is not None:
        res = rollback_to_tick(
            tick_id=args.rollback_to_tick,
            repo_root=root,
            epoch_seed=args.epoch_seed,
        )
        print(
            json.dumps(
                {
                    "status": "ROLLED_BACK",
                    "rolled_back_to_tick": res["rolled_back_to_tick"],
                    "events_replayed": res["events_replayed"],
                    "removed_files": res["removed_files"],
                },
                indent=2,
            )
        )
        return 0

    if args.integrate_file:
        integrator = SingleIntegrator(repo_root=root, epoch_seed=args.epoch_seed)
        prop = _load_json(Path(args.integrate_file))
        res = integrator.integrate_proposal(prop)
        print(json.dumps(res, indent=2))
        return 0 if res["integrated"] else 1

    if args.rebuild:
        res = rebuild_state_from_events(repo_root=root, epoch_seed=args.epoch_seed, write_files=True)
        print(
            json.dumps(
                {
                    "status": "REBUILT",
                    "latest_tick": res["latest_tick"],
                    "events_replayed": res["events_replayed"],
                },
                indent=2,
            )
        )
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
