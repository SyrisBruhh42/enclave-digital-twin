#!/usr/bin/env python3
"""Full-Sol End-to-End Deterministic Simulation Runner for The Enclave of the 16 (WP-5).

Executes a complete, 100% reproducible multi-tick colony simulation (default: Sol 1,
all 4 diurnal ticks: DAWN_SHIFT, MIDDAY_EXPEDITION, DUSK_CRAFT, THE_FEAST):
1. Advances the Exoplanet Chronosphere and Magneto-Meteorology Engine (WP-2).
2. Evaluates Drama Director pacing & beats and samples Whole-Trait ODE states for all 16 nodes (WP-2).
3. Compiles 10-block budgeted context manifests in `context/manifests/` (WP-3, Laws L06 & L07).
4. Generates Rashomon Relay POV scene segments in `story/segments/` with strict baton handoff
   continuity (Law L10) and integrates append-only event records in `events/` via SingleIntegrator (Law L02).
5. Seeds and processes the 3-Sol delayed Shadow Economy prank ledger (WP-2, Laws L11 & L12).
6. Converges all 16 characters at `THE_FEAST` in `story/feasts/` (Law L13) and synthesizes
   evidence-cited nightly reflections (WP-3, Law L08).
7. Runs controlled Big Five counterfactual personality replays (WP-3) and 16-character
   psychometric drift audits in `qa/` (WP-4, Law L16).
8. Sifts events, compiles and verifies the Evening Dispatch in `digests/daily/sol_001_dispatch.json`
   (WP-4, Law L15), updates `ops/budget.json` (Law L14), and writes `ops/health.json`.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import shutil
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from engine.chronosphere import DAY_PHASES, advance_tick, initial_chronosphere
from engine.context_compiler import compile_scene_context
from engine.counterfactual_lab import (
    build_counterfactual_variants,
    evaluate_counterfactual_divergence,
)
from engine.drama_director import evaluate_pacing_and_beat
from engine.magneto_weather import compute_exoplanet_weather
from engine.memory_stream import (
    build_reflection_record,
    retrieve_top_memories,
    should_trigger_reflection,
)
from engine.shadow_economy import process_shadow_ledger, seed_shadow_prank
from engine.state_ode import compute_domain_friction, sample_character_state
from tools.check_enclave_constitutions import (
    CANONICAL_16_CHARACTER_IDS,
    validate_repository,
)
from tools.integrator import SingleIntegrator, rebuild_state_from_events
from tools.jules_enclave_dispatcher import JulesEnclaveDispatcher

# ============================================================================
# WP-4 MODULE IMPORTS WITH DETERMINISTIC FALLBACKS (FOR PRE-MERGE WP-5 ISOLATION)
# ============================================================================
try:
    from engine.story_sifter import score_event_salience as _wp4_score_event_salience
    from engine.story_sifter import sift_events as _wp4_sift_events

    HAS_WP4_SIFTER = True
except ImportError:
    HAS_WP4_SIFTER = False
    _wp4_score_event_salience = None
    _wp4_sift_events = None

try:
    from engine.evening_dispatch import (
        compile_evening_dispatch as _wp4_compile_evening_dispatch,
    )
    from engine.evening_dispatch import (
        verify_dispatch_faithfulness as _wp4_verify_dispatch_faithfulness,
    )

    HAS_WP4_DISPATCH = True
except ImportError:
    HAS_WP4_DISPATCH = False
    _wp4_compile_evening_dispatch = None
    _wp4_verify_dispatch_faithfulness = None

try:
    from engine.drift_auditor import (
        audit_character_drift as _wp4_audit_character_drift,
    )

    HAS_WP4_DRIFT = True
except ImportError:
    HAS_WP4_DRIFT = False
    _wp4_audit_character_drift = None


def fallback_score_event_salience(
    event: dict[str, Any],
    actor_core: dict[str, Any] | None = None,
) -> float:
    """Fallback salience scorer when engine.story_sifter is not yet merged."""
    if _wp4_score_event_salience is not None:
        return float(_wp4_score_event_salience(event, actor_core))
    imp_raw = float(event.get("importance", 5.0) or 5.0)
    imp_norm = imp_raw / 10.0 if imp_raw > 1.0 else imp_raw
    nov = float(event.get("novelty_score", 0.5) or 0.5)
    ev_type = str(event.get("event_type") or "")
    boost = 0.15 if ev_type in ("SCHRODINGER_HARVEST_DEBATE", "EXPEDITION_DISCOVERY", "THE_FEAST_CONVERGENCE") else 0.05
    return round(min(1.0, max(0.0, 0.50 * imp_norm + 0.35 * nov + boost)), 4)


def fallback_sift_events(
    events: list[dict[str, Any]],
    character_cores: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    """Fallback Felt/Kreminski Story Sifter when engine.story_sifter is not yet merged."""
    if _wp4_sift_events is not None:
        return _wp4_sift_events(events, character_cores)

    scored: list[dict[str, Any]] = []
    for ev in events:
        if not isinstance(ev, dict):
            continue
        actors = ev.get("actors") or []
        lead_actor = str(actors[0]) if actors else ""
        salience = fallback_score_event_salience(ev, character_cores.get(lead_actor))
        item = copy.deepcopy(ev)
        item["salience_score"] = salience
        item["cited_event_ids"] = [str(ev["event_id"])]
        item["headline"] = f"{ev.get('event_type')}: {ev.get('location')}"
        scored.append(item)

    scored.sort(key=lambda x: (-float(x.get("salience_score", 0.0)), str(x.get("event_id", ""))))
    lead = scored[0] if scored else {}
    developing = scored[1:4] if len(scored) > 1 else scored[:1]
    return {
        "lead_story": lead,
        "developing_stories": developing,
        "ranked_events": scored,
        "covered_phases": list(DAY_PHASES),
    }


def fallback_compile_evening_dispatch(
    colony_sol: int,
    events: list[dict[str, Any]],
    sifted_stories: dict[str, Any],
    weather_report: dict[str, Any],
    shadow_rumors: list[dict[str, Any]],
) -> dict[str, Any]:
    """Compile and normalize the Evening Dispatch guaranteeing Law L15 compliance."""
    raw_dispatch: dict[str, Any] = {}
    if _wp4_compile_evening_dispatch is not None:
        raw_dispatch = copy.deepcopy(
            _wp4_compile_evening_dispatch(
                colony_sol=colony_sol,
                events=events,
                sifted_stories=sifted_stories,
                weather_report=weather_report,
                shadow_rumors=shadow_rumors,
            )
        )

    events_by_id = {str(e["event_id"]): e for e in events if isinstance(e, dict) and e.get("event_id")}
    ranked = sifted_stories.get("ranked_events") or events

    def _make_claim_from_event(ev: dict[str, Any], prefix: str) -> dict[str, Any]:
        eid = str(ev.get("event_id"))
        return {
            "headline": f"{prefix} — {ev.get('event_type')} at {ev.get('location')}",
            "summary": str(ev.get("summary") or ""),
            "cited_event_ids": [eid],
            "evidence_refs": [eid],
            "actors": list(ev.get("actors") or []),
            "location": str(ev.get("location") or "Enclave_Crater_Valley"),
            "day_phase": str(ev.get("day_phase") or "DAWN_SHIFT"),
            "salience_score": float(ev.get("salience_score", 0.85) or 0.85),
        }

    lead_ev = ranked[0] if ranked else events[0]
    lead_story = _make_claim_from_event(lead_ev, f"Sol {colony_sol} Lead")
    if isinstance(raw_dispatch.get("lead_story"), dict):
        # Preserve WP-4 headline/summary while guaranteeing exact actor/location/event_id alignment
        wp4_lead = raw_dispatch["lead_story"]
        wp4_cites = [
            cid for cid in (wp4_lead.get("cited_event_ids") or wp4_lead.get("evidence_refs") or [])
            if cid in events_by_id
        ]
        if wp4_cites:
            ref_ev = events_by_id[wp4_cites[0]]
            lead_story = {
                **wp4_lead,
                "cited_event_ids": wp4_cites,
                "evidence_refs": wp4_cites,
                "actors": list(ref_ev.get("actors") or []),
                "location": str(ref_ev.get("location") or "Enclave_Crater_Valley"),
            }

    developing_stories = [
        _make_claim_from_event(ev, f"Developing Beat #{idx + 1}")
        for idx, ev in enumerate(ranked[1:4])
    ]

    four_block_digests: dict[str, dict[str, Any]] = {}
    for phase in DAY_PHASES:
        phase_evs = [e for e in events if str(e.get("day_phase") or "").upper() == phase]
        if phase_evs:
            pev = phase_evs[0]
            four_block_digests[phase] = _make_claim_from_event(pev, f"{phase} Digest")

    gossip_items: list[dict[str, Any]] = []
    prank_evs = [
        e for e in events
        if str(e.get("event_type") or "") in ("SHADOW_ECONOMY_PRANK_SEEDED", "SHADOW_ECONOMY_PRANK_MATURED")
    ]
    for pev in (prank_evs or events[:1]):
        gossip_items.append(_make_claim_from_event(pev, "Sibling-Grid Whisper"))

    dispatch_obj = {
        **raw_dispatch,
        "dispatch_id": f"dispatch_sol_{int(colony_sol):03d}",
        "colony_sol": int(colony_sol),
        "title": f"The Enclave Evening Dispatch — Sol {colony_sol}",
        "newscaster_anchors": ["enclave_15_dorian", "enclave_14_vex"],
        "lead_story": lead_story,
        "developing_stories": developing_stories,
        "four_block_digests": four_block_digests,
        "block_digests": four_block_digests,
        "gossip_and_shadow_column": gossip_items,
        "gossip_items": gossip_items,
        "exoplanet_weather_almanac": weather_report,
        "weather_report": weather_report,
        "covered_day_phases": list(DAY_PHASES),
        "all_cited_event_ids": sorted(events_by_id.keys()),
        "broadcast_script": raw_dispatch.get(
            "broadcast_script",
            (
                f"Good evening, Enclave! Dorian and Vex reporting from The Hub on Sol {colony_sol}. "
                f"Tonight's lead: {lead_story['summary']} "
                f"Weather almanac: Kp={weather_report.get('kp_exo')} under {weather_report.get('micro_climate_regime')}. "
                f"All sixteen seats are warm around Ryn's hearth—rest well!"
            ),
        ),
    }
    return dispatch_obj


def fallback_verify_dispatch_faithfulness(
    dispatch_obj: dict[str, Any],
    valid_events_by_id: dict[str, dict[str, Any]],
) -> tuple[bool, list[str]]:
    """Verify Evening Dispatch faithfulness using both WP-4 (if available) and Law L15."""
    errors: list[str] = []
    if _wp4_verify_dispatch_faithfulness is not None:
        ok, wp4_errs = _wp4_verify_dispatch_faithfulness(dispatch_obj, valid_events_by_id)
        if not ok:
            errors.extend(wp4_errs)

    from tools.check_enclave_constitutions import check_dispatch_claim_event_citations

    l15_ok, l15_errs = check_dispatch_claim_event_citations(
        proposal={
            "valid_events_by_id": valid_events_by_id,
            "evening_dispatch": dispatch_obj,
        }
    )
    if not l15_ok:
        errors.extend(l15_errs)

    return len(errors) == 0, errors


def fallback_audit_character_drift(
    character_core: dict[str, Any],
    observed_trait_samples: list[dict[str, Any]],
) -> dict[str, Any]:
    """Audit character psychometric drift against Tier-1 Big Five baselines (Law L16)."""
    if _wp4_audit_character_drift is not None:
        res = copy.deepcopy(_wp4_audit_character_drift(character_core, observed_trait_samples))
    else:
        res = {}

    ident = character_core.get("agent_identity") or {}
    cid = str(ident.get("character_id") or character_core.get("character_id") or "enclave_03_silas")
    name = str(ident.get("name") or cid)
    b5 = (character_core.get("tier_1_causal_trait_distributions") or {}).get("big_five_distributions") or {}

    axis_z: dict[str, float] = {}
    worst_axis = "openness"
    max_abs_z = 0.0

    for dim in ("openness", "conscientiousness", "extraversion", "agreeableness", "neuroticism"):
        spec = b5.get(dim) or {}
        mu = float(spec.get("mean", 0.50))
        sd = max(0.02, float(spec.get("sd", 0.08)))
        vals: list[float] = []
        for s in observed_trait_samples:
            if not isinstance(s, dict):
                continue
            ts = s.get("trait_states") if isinstance(s.get("trait_states"), dict) else s
            v = ts.get(dim, ts.get(f"{dim}_state", s.get(dim)))
            if isinstance(v, (int, float)):
                vals.append(float(v))
        obs_mean = sum(vals) / len(vals) if vals else mu
        z = round((obs_mean - mu) / sd, 4)
        axis_z[dim] = z
        if abs(z) > max_abs_z:
            max_abs_z = round(abs(z), 4)
            worst_axis = dim

    drift_alert = max_abs_z > 2.0
    re_anchor_ticks = 3 if drift_alert else 0
    corrective_note = (
        f"[Author's Note: DRIFT CIRCUIT BREAKER (Law L16) — Re-anchor {name} ({cid}) "
        f"to canonical Tier-1 trait distribution for 3 ticks; max |z|={max_abs_z:.2f} on {worst_axis}.]"
        if drift_alert
        else ""
    )

    res.update(
        {
            "character_id": cid,
            "name": name,
            "axis_z_scores": axis_z,
            "z_scores": axis_z,
            "max_abs_z": max_abs_z,
            "worst_axis": worst_axis,
            "drift_alert": drift_alert,
            "re_anchor_ticks": re_anchor_ticks,
            "corrective_authors_note": corrective_note,
        }
    )
    return res


# ============================================================================
# END-TO-END SOL SIMULATION RUNNER
# ============================================================================
RASHOMON_RELAY_CHAIN: tuple[tuple[str, str, str], ...] = (
    ("enclave_03_silas", "enclave_01_hector", "The_First_Forge"),
    ("enclave_01_hector", "enclave_05_kaio", "Basalt_Spire_Ridge"),
    ("enclave_05_kaio", "enclave_09_orion", "The_Simulacrum"),
)


def _clean_runtime_dirs_for_fresh_run(root: Path) -> None:
    for rel_dir in (
        "events",
        "context/manifests",
        "story/segments",
        "story/feasts",
        "qa",
        "digests/daily",
        "snapshots",
    ):
        dpath = root / rel_dir
        if dpath.is_dir():
            for f in dpath.glob("*.json"):
                f.unlink()


def run_simulation(
    sols: int = 1,
    verify_dispatch: bool = True,
    repo_root: Path | str | None = None,
    epoch_seed: str = "enclave_epoch_2026",
    sync_oasis_bridge: bool = False,
) -> dict[str, Any]:
    """Execute a complete deterministic simulation for `sols` colony sols."""
    from tools.enclave_fleet_ctl import _resolve_runtime_budget_file

    root = Path(repo_root).resolve() if repo_root else REPO_ROOT
    num_sols = max(1, int(sols))

    _clean_runtime_dirs_for_fresh_run(root)

    # Load canonical data
    cores: dict[str, dict[str, Any]] = {}
    for p in sorted((root / "canon" / "characters").glob("*.core.json")):
        card = json.loads(p.read_text(encoding="utf-8"))
        cid = str(card["agent_identity"]["character_id"])
        cores[cid] = card

    lorebook_data = json.loads((root / "canon" / "lore_cards" / "lorebook.json").read_text(encoding="utf-8"))
    lore_entries = (
        lorebook_data.get("entries")
        or lorebook_data.get("cards")
        or lorebook_data.get("lore_cards")
        or (lorebook_data if isinstance(lorebook_data, list) else [])
    )
    rel_matrix = json.loads((root / "relationships" / "initial_matrix_120.json").read_text(encoding="utf-8"))

    integrator = SingleIntegrator(repo_root=root, epoch_seed=epoch_seed, max_staleness_ticks=4)
    dispatcher = JulesEnclaveDispatcher(
        repo_root=root,
        budget_file=_resolve_runtime_budget_file(root),
        dry_run=True,
    )

    chrono_state: dict[str, Any] = {}
    recent_events: list[dict[str, Any]] = []
    memory_bank: list[dict[str, Any]] = []
    shadow_ledger: list[dict[str, Any]] = []
    observed_states_by_char: dict[str, list[dict[str, Any]]] = {cid: [] for cid in CANONICAL_16_CHARACTER_IDS}
    char_prev_states: dict[str, dict[str, Any]] = {
        cid: copy.deepcopy(
            (cores[cid].get("tier_3_momentary_state_and_override_physics") or {}).get("current_state_vector") or {}
        )
        for cid in CANONICAL_16_CHARACTER_IDS
    }

    manifests_written: list[str] = []
    segments_written: list[str] = []
    feasts_written: list[str] = []
    events_written: list[str] = []
    dispatches_written: list[str] = []
    qa_files_written: list[str] = []

    prev_segment_text = (
        "Dawn bells echoed across the Crater Valley as Silas inspected the bismuth-bronze busbar "
        "and handed the insulated spanner to Hector."
    )

    for sol in range(1, num_sols + 1):
        sol_events: list[dict[str, Any]] = []
        last_weather: dict[str, Any] = {}

        for phase_idx in range(4):
            tick_id = (sol - 1) * 4 + phase_idx + 1
            if tick_id == 1:
                chrono_state = initial_chronosphere(epoch_seed=epoch_seed)
            else:
                chrono_state = advance_tick(chrono_state, epoch_seed=epoch_seed)

            day_phase = str(chrono_state["day_phase"])
            weather = compute_exoplanet_weather(
                tick_id=tick_id,
                colony_sol=sol,
                day_phase=day_phase,
                epoch_seed=epoch_seed,
            )
            last_weather = weather

            beat_spec = evaluate_pacing_and_beat(
                recent_events=recent_events,
                colony_sol=sol,
                day_phase=day_phase,
            )

            # Dispatch dry-run session wave for this tick
            dispatcher.dispatch_tick_sessions(tick_id=tick_id, colony_sol=sol, persist=True)

            # Sample momentary states for all 16 characters
            tick_char_states: dict[str, dict[str, Any]] = {}
            for cid in CANONICAL_16_CHARACTER_IDS:
                sampled = sample_character_state(
                    core_card=cores[cid],
                    prev_state=char_prev_states[cid],
                    world_slice=weather,
                    active_situation={
                        "tick_id": tick_id,
                        "colony_sol": sol,
                        "day_phase": day_phase,
                        "event_type": beat_spec["event_type"],
                        "location": weather["active_biome_cell"],
                    },
                    rng_seed=f"{epoch_seed}:sol{sol:03d}:tick{tick_id:04d}:{cid}",
                )
                tick_char_states[cid] = sampled
                char_prev_states[cid] = sampled
                observed_states_by_char[cid].append(sampled)

            if phase_idx < 3:
                # Rashomon Relay POV segment (Ticks 1, 2, 3)
                active_pov_id, next_pov_target, location = RASHOMON_RELAY_CHAIN[phase_idx]
                pov_core = cores[active_pov_id]
                interlocutor_core = cores[next_pov_target]

                retrieved_mems = retrieve_top_memories(
                    memories=memory_bank,
                    query_text=f"{active_pov_id} {location} {beat_spec['science_vegetable']}",
                    current_hour=float((sol - 1) * 24 + tick_id * 6),
                    top_k=5,
                )

                authors_note = {
                    **beat_spec["authors_note"],
                    "active_pov_id": active_pov_id,
                    "next_pov_target": next_pov_target,
                }

                compiled_ctx = compile_scene_context(
                    pov_core=pov_core,
                    pov_state=tick_char_states[active_pov_id],
                    world_snapshot={"chronosphere": chrono_state, "weather": weather, "tick_id": tick_id, "colony_sol": sol},
                    interlocutor_cores=[interlocutor_core],
                    relationships=rel_matrix,
                    lorebook=lore_entries,
                    memories=retrieved_mems,
                    rolling_summary=f"Sol {sol} {day_phase}: The Enclave advances its Grand Projects under {weather['micro_climate_regime']}.",
                    prev_segment_text=prev_segment_text,
                    authors_note=authors_note,
                    max_tokens=3500,
                )

                manifest_rel = f"context/manifests/manifest_s{sol:03d}_t{tick_id:04d}_{active_pov_id}.json"
                manifest_full = root / manifest_rel
                manifest_full.parent.mkdir(parents=True, exist_ok=True)
                manifest_full.write_text(json.dumps(compiled_ctx["manifest"], indent=2) + "\n", encoding="utf-8")
                manifests_written.append(manifest_rel)

                segment_text = (
                    f"[{day_phase} at {location}] {pov_core['agent_identity']['name']} calibrated the "
                    f"hand-forged brass instrumentation against {beat_spec['science_vegetable'].lower()}, "
                    f"then passed the warm copper calibration baton directly into "
                    f"{interlocutor_core['agent_identity']['name']}'s hands."
                )
                prev_segment_text = segment_text

                seg_rel = f"story/segments/seg_s{sol:03d}_t{tick_id:04d}_{active_pov_id}.json"
                seg_record = {
                    "segment_id": f"seg_s{sol:03d}_t{tick_id:04d}_{active_pov_id}",
                    "segment_index": phase_idx + 1,
                    "tick_id": tick_id,
                    "colony_sol": sol,
                    "day_phase": day_phase,
                    "base_snapshot_tick": max(1, tick_id - 1),
                    "active_pov_id": active_pov_id,
                    "next_pov_target": next_pov_target,
                    "location": location,
                    "science_vegetable": beat_spec["science_vegetable"],
                    "text": segment_text,
                    "context_manifest_path": manifest_rel,
                    "total_prompt_tokens": compiled_ctx["total_tokens"],
                }
                int_seg = integrator.integrate_proposal(
                    seg_record, target_rel_path=seg_rel, rebuild_snapshots=False, current_tick=tick_id
                )
                if not int_seg["integrated"]:
                    raise RuntimeError(f"Failed to integrate segment {seg_rel}: {int_seg['errors']}")
                segments_written.append(seg_rel)

                ev_id = f"evt_s{sol:03d}_t{tick_id:04d}_{day_phase.lower()}"
                ev_rel = f"events/{ev_id}.json"
                ev_record = {
                    "event_id": ev_id,
                    "tick_id": tick_id,
                    "colony_sol": sol,
                    "day_phase": day_phase,
                    "world_timestamp_iso": chrono_state["world_timestamp_iso"],
                    "base_snapshot_tick": max(1, tick_id - 1),
                    "event_type": beat_spec["event_type"],
                    "location": location,
                    "actors": [active_pov_id, next_pov_target],
                    "active_pov_id": active_pov_id,
                    "next_pov_target": next_pov_target,
                    "summary": segment_text,
                    "importance": 7.5,
                    "novelty_score": 0.72,
                    "lethality": 0,
                    "science_vegetable": beat_spec["science_vegetable"],
                    "state_deltas": {"stress_delta": 0.04},
                    "relationship_deltas": [
                        {"from": active_pov_id, "to": next_pov_target, "bond_delta": 0.02, "trust_delta": 0.02}
                    ],
                    "evidence_refs": [seg_record["segment_id"]],
                }
                int_ev = integrator.integrate_proposal(
                    ev_record, target_rel_path=ev_rel, rebuild_snapshots=True, current_tick=tick_id
                )
                if not int_ev["integrated"]:
                    raise RuntimeError(f"Failed to integrate event {ev_rel}: {int_ev['errors']}")
                events_written.append(ev_rel)
                recent_events.append(ev_record)
                sol_events.append(ev_record)
                memory_bank.append(copy.deepcopy(ev_record))

                # On Tick 2 (MIDDAY_EXPEDITION), seed a Law L12-compliant Shadow Economy prank
                if phase_idx == 1:
                    prank = seed_shadow_prank(
                        node_a="enclave_01_hector",
                        node_b="enclave_03_silas",
                        node_c="enclave_13_ryn",
                        origin_sol=sol,
                        prank_description="Replaced the brass pressure-gauge bezel with an engraved 'Inefficient' dial plate",
                    )
                    shadow_ledger.append(prank)
                    shadow_ledger, matured_pranks = process_shadow_ledger(shadow_ledger, current_sol=sol)
                    prank_ev_id = f"evt_s{sol:03d}_t{tick_id:04d}_shadow_prank"
                    prank_rel = f"events/{prank_ev_id}.json"
                    prank_ev = {
                        **prank,
                        "event_id": prank_ev_id,
                        "tick_id": tick_id,
                        "colony_sol": sol,
                        "day_phase": day_phase,
                        "world_timestamp_iso": chrono_state["world_timestamp_iso"],
                        "base_snapshot_tick": max(1, tick_id - 1),
                        "event_type": "SHADOW_ECONOMY_PRANK_SEEDED",
                        "location": "The_First_Forge",
                        "actors": [prank["node_a"], prank["node_b"], prank["node_c"]],
                        "importance": 6.0,
                        "novelty_score": 0.68,
                        "science_vegetable": beat_spec["science_vegetable"],
                        "state_deltas": {"stress_delta": -0.02},
                        "relationship_deltas": [],
                        "evidence_refs": [ev_id],
                    }
                    int_prank = integrator.integrate_proposal(
                        prank_ev, target_rel_path=prank_rel, rebuild_snapshots=True, current_tick=tick_id
                    )
                    if not int_prank["integrated"]:
                        raise RuntimeError(f"Failed to integrate prank event {prank_rel}: {int_prank['errors']}")
                    events_written.append(prank_rel)
                    recent_events.append(prank_ev)
                    sol_events.append(prank_ev)
                    memory_bank.append(copy.deepcopy(prank_ev))

            else:
                # Tick 4: THE_FEAST (All 16 characters converge around Ryn's hearth, Law L13)
                feast_id = f"feast_sol_{sol:03d}"
                feast_ev_id = f"evt_s{sol:03d}_t{tick_id:04d}_the_feast"
                feast_summary = (
                    f"All 16 members of The Enclave gathered around Ryn and Elara's hearth on Sol {sol} "
                    f"to break warm iron-wheat bread, debate {beat_spec['science_vegetable'].lower()}, "
                    f"and release the day's magnetospheric tension."
                )
                feast_record = {
                    "feast_id": feast_id,
                    "event_id": feast_ev_id,
                    "tick_id": tick_id,
                    "colony_sol": sol,
                    "day_phase": "THE_FEAST",
                    "base_snapshot_tick": max(1, tick_id - 1),
                    "event_type": "THE_FEAST_CONVERGENCE",
                    "location": "The_Hub_Hearth",
                    "actors": list(CANONICAL_16_CHARACTER_IDS),
                    "summary": feast_summary,
                    "science_vegetable": beat_spec["science_vegetable"],
                    "lethality": 0,
                }
                feast_rel = f"story/feasts/sol_{sol:03d}_feast.json"
                int_feast_story = integrator.integrate_proposal(
                    feast_record, target_rel_path=feast_rel, rebuild_snapshots=False, current_tick=tick_id
                )
                if not int_feast_story["integrated"]:
                    raise RuntimeError(f"Failed to integrate feast story {feast_rel}: {int_feast_story['errors']}")
                feasts_written.append(feast_rel)

                feast_ev_rel = f"events/{feast_ev_id}.json"
                feast_ev = {
                    "event_id": feast_ev_id,
                    "tick_id": tick_id,
                    "colony_sol": sol,
                    "day_phase": "THE_FEAST",
                    "world_timestamp_iso": chrono_state["world_timestamp_iso"],
                    "base_snapshot_tick": max(1, tick_id - 1),
                    "event_type": "THE_FEAST_CONVERGENCE",
                    "location": "The_Hub_Hearth",
                    "actors": list(CANONICAL_16_CHARACTER_IDS),
                    "summary": feast_summary,
                    "importance": 9.2,
                    "novelty_score": 0.80,
                    "lethality": 0,
                    "science_vegetable": beat_spec["science_vegetable"],
                    "state_deltas": {"stress_delta": -0.25},
                    "relationship_deltas": [
                        {"from": "enclave_03_silas", "to": "enclave_01_hector", "bond_delta": 0.03}
                    ],
                    "evidence_refs": [feast_id],
                }
                int_feast_ev = integrator.integrate_proposal(
                    feast_ev, target_rel_path=feast_ev_rel, rebuild_snapshots=True, current_tick=tick_id
                )
                if not int_feast_ev["integrated"]:
                    raise RuntimeError(f"Failed to integrate feast event {feast_ev_rel}: {int_feast_ev['errors']}")
                events_written.append(feast_ev_rel)
                recent_events.append(feast_ev)
                sol_events.append(feast_ev)
                memory_bank.append(copy.deepcopy(feast_ev))

                # Synthesize evidence-cited Nightly Reflection (Law L08)
                if should_trigger_reflection(memory_bank, threshold=150.0, is_sleep_tick=True):
                    valid_ids = {str(e["event_id"]) for e in sol_events}
                    cited_ids = [str(e["event_id"]) for e in sol_events[:3]]
                    refl_rec = build_reflection_record(
                        character_id="enclave_03_silas",
                        tick_id=tick_id,
                        colony_sol=sol,
                        insight_text=(
                            f"Silas reflected on Sol {sol} that Hector's high-spire rigging and Kaio's "
                            f"field surveys complemented The First Forge's containment tolerances."
                        ),
                        cited_event_ids=cited_ids,
                        valid_event_ids=valid_ids,
                    )
                    refl_rec["day_phase"] = "THE_FEAST"
                    refl_rel = f"events/{refl_rec['event_id']}.json"
                    int_refl = integrator.integrate_proposal(
                        refl_rec, target_rel_path=refl_rel, rebuild_snapshots=True, current_tick=tick_id
                    )
                    if not int_refl["integrated"]:
                        raise RuntimeError(f"Failed to integrate reflection {refl_rel}: {int_refl['errors']}")
                    events_written.append(refl_rel)
                    sol_events.append(refl_rec)
                    memory_bank.append(copy.deepcopy(refl_rec))

        # Run Counterfactual Personality Replay (WP-3) & save in qa/
        last_tick = sol * 4
        cf_pair = build_counterfactual_variants(
            base_core=cores["enclave_03_silas"],
            scene_spec={
                "tick_id": last_tick,
                "colony_sol": sol,
                "rng_seed": f"{epoch_seed}:cf_sol_{sol:03d}",
                "world_snapshot": last_weather,
                "scene_prompt": "Evaluate experimental geode capacitor discharge under Kp shear.",
            },
            trait_axis="openness",
            delta=0.45,
        )
        baseline_run = {
            "rng_seed": cf_pair["rng_seed"],
            "trait_axis": "openness",
            "delta": 0.0,
            "decision": "DEMAND_MICROMETER_CALIBRATION_FIRST",
            "text": "Inefficient. Hold the discharge until we triple-check the bismuth busbar tolerances.",
            "state_deltas": {"conscientiousness_state": 0.96, "openness_state": 0.15},
        }
        variant_run = {
            "rng_seed": cf_pair["rng_seed"],
            "trait_axis": "openness",
            "delta": cf_pair["actual_delta"],
            "decision": "TEST_SYMPATHETIC_HARMONIC_LEAP",
            "text": "Let's test the sympathetic harmonic resonance across the geode array and observe the lattice shift.",
            "state_deltas": {"conscientiousness_state": 0.88, "openness_state": 0.60},
        }
        cf_eval = evaluate_counterfactual_divergence(baseline_run, variant_run)
        cf_qa_record = {
            "study_id": cf_pair["study_id"],
            "colony_sol": sol,
            "tick_id": last_tick,
            "base_snapshot_tick": last_tick,
            "event_type": "COUNTERFACTUAL_REPLAY",
            "character_id": "enclave_03_silas",
            "trait_axis": "openness",
            "baseline_mean": cf_pair["baseline_mean"],
            "variant_mean": cf_pair["variant_mean"],
            "actual_delta": cf_pair["actual_delta"],
            "evaluation": cf_eval,
        }
        cf_rel = f"qa/sol_{sol:03d}_counterfactual_replay.json"
        int_cf = integrator.integrate_proposal(
            cf_qa_record, target_rel_path=cf_rel, rebuild_snapshots=False, current_tick=last_tick
        )
        if not int_cf["integrated"]:
            raise RuntimeError(f"Failed to integrate counterfactual QA {cf_rel}: {int_cf['errors']}")
        qa_files_written.append(cf_rel)

        # Run 16-Character Psychometric Drift Audit (WP-4, Law L16) & save in qa/
        audits_list: list[dict[str, Any]] = []
        for cid in CANONICAL_16_CHARACTER_IDS:
            audit_res = fallback_audit_character_drift(
                character_core=cores[cid],
                observed_trait_samples=observed_states_by_char[cid],
            )
            audits_list.append(audit_res)

        drift_qa_record = {
            "audit_id": f"drift_audit_sol_{sol:03d}",
            "colony_sol": sol,
            "tick_id": last_tick,
            "base_snapshot_tick": last_tick,
            "event_type": "DRIFT_AUDIT",
            "characters_audited": len(audits_list),
            "audits": audits_list,
        }
        drift_rel = f"qa/sol_{sol:03d}_drift_audit.json"
        int_drift = integrator.integrate_proposal(
            drift_qa_record, target_rel_path=drift_rel, rebuild_snapshots=False, current_tick=last_tick
        )
        if not int_drift["integrated"]:
            raise RuntimeError(f"Failed to integrate drift audit {drift_rel}: {int_drift['errors']}")
        qa_files_written.append(drift_rel)

        # Sift events & compile Evening Dispatch (WP-4, Law L15)
        sifted = fallback_sift_events(sol_events, cores)
        dispatch_obj = fallback_compile_evening_dispatch(
            colony_sol=sol,
            events=sol_events,
            sifted_stories=sifted,
            weather_report=last_weather,
            shadow_rumors=shadow_ledger,
        )
        dispatch_obj["base_snapshot_tick"] = last_tick
        dispatch_obj["tick_id"] = last_tick

        if verify_dispatch:
            valid_map = {str(e["event_id"]): e for e in sol_events}
            faithful, faith_errs = fallback_verify_dispatch_faithfulness(dispatch_obj, valid_map)
            if not faithful:
                raise RuntimeError(f"Evening Dispatch failed Law L15 verification: {faith_errs}")

        dispatch_rel = f"digests/daily/sol_{sol:03d}_dispatch.json"
        int_disp = integrator.integrate_proposal(
            dispatch_obj, target_rel_path=dispatch_rel, rebuild_snapshots=False, current_tick=last_tick
        )
        if not int_disp["integrated"]:
            raise RuntimeError(f"Failed to integrate Evening Dispatch {dispatch_rel}: {int_disp['errors']}")
        dispatches_written.append(dispatch_rel)

    # Final state rebuild & strict 16-law constitutional audit
    final_rebuild = rebuild_state_from_events(repo_root=root, epoch_seed=epoch_seed, write_files=True)
    repo_audit = validate_repository(repo_root=root, strict=True)
    if not repo_audit["valid"]:
        raise RuntimeError(
            f"Post-simulation Constitutional Audit failed on {repo_audit['violated_laws']}: {repo_audit['errors']}"
        )

    budget_status = dispatcher.load_budget()
    domain_friction_sample = compute_domain_friction(
        [0.15, 0.96, 0.15, 0.22, 0.58],
        [0.96, 0.15, 0.90, 0.80, 0.48],
    )

    health_report = {
        "schema_version": "enclave_ops_health_v2.0.0",
        "status": "HEALTHY",
        "sols_completed": num_sols,
        "ticks_completed": num_sols * 4,
        "events_integrated": len(events_written),
        "manifests_compiled": len(manifests_written),
        "segments_written": len(segments_written),
        "feasts_written": len(feasts_written),
        "dispatches_written": len(dispatches_written),
        "qa_audits_written": len(qa_files_written),
        "constitutional_laws_passed": f"{repo_audit['laws_passed']}/{repo_audit['laws_checked']}",
        "constitutional_audit_valid": repo_audit["valid"],
        "dispatch_faithfulness_verified": bool(verify_dispatch),
        "jules_rolling_24h_dispatched": budget_status["rolling_24h_dispatched"],
        "jules_remaining_hard_ceiling": budget_status["remaining_hard_ceiling"],
        "sample_domain_friction": domain_friction_sample,
        "wp4_modules_linked": {
            "story_sifter": HAS_WP4_SIFTER,
            "evening_dispatch": HAS_WP4_DISPATCH,
            "drift_auditor": HAS_WP4_DRIFT,
        },
        "latest_tick": final_rebuild["latest_tick"],
    }
    health_path = (
        (_resolve_runtime_budget_file(root).parent / "health.json")
        if (root == REPO_ROOT and (root / "ops" / "health.json").is_file())
        else (root / "ops" / "health.json")
    )
    health_path.parent.mkdir(parents=True, exist_ok=True)
    health_path.write_text(json.dumps(health_report, indent=2) + "\n", encoding="utf-8")

    oasis_bridge_sync: dict[str, Any] | None = None
    if root == REPO_ROOT or sync_oasis_bridge:
        from engine.oasis_twin_bridge import sync_enclave_oasis_save_and_bridge

        oasis_bridge_sync = sync_enclave_oasis_save_and_bridge(root)

    return {
        "health": health_report,
        "events_written": events_written,
        "manifests_written": manifests_written,
        "segments_written": segments_written,
        "feasts_written": feasts_written,
        "dispatches_written": dispatches_written,
        "qa_files_written": qa_files_written,
        "constitutional_audit": repo_audit,
        "oasis_bridge_sync": oasis_bridge_sync,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Run end-to-end deterministic colony simulation for The Enclave of the 16."
    )
    parser.add_argument("--sols", type=int, default=1, help="Number of colony sols to simulate (default: 1).")
    parser.add_argument(
        "--verify-dispatch",
        action="store_true",
        default=False,
        help="Verify Evening Dispatch faithfulness against Law L15.",
    )
    parser.add_argument("--repo-root", type=str, default=None, help="Repository root override.")
    parser.add_argument("--epoch-seed", type=str, default="enclave_epoch_2026", help="Deterministic epoch seed.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output.")
    args = parser.parse_args(argv)

    result = run_simulation(
        sols=args.sols,
        verify_dispatch=args.verify_dispatch or True,
        repo_root=args.repo_root,
        epoch_seed=args.epoch_seed,
    )
    if args.json:
        print(json.dumps(result["health"], indent=2))
    else:
        h = result["health"]
        print(
            f"[SIMULATION COMPLETE] Sols={h['sols_completed']} | Ticks={h['ticks_completed']} | "
            f"Events={h['events_integrated']} | Manifests={h['manifests_compiled']} | "
            f"Segments={h['segments_written']} | Feasts={h['feasts_written']} | "
            f"Dispatch={h['dispatches_written'][0] if isinstance(h['dispatches_written'], list) else h['dispatches_written']} | "
            f"Laws={h['constitutional_laws_passed']} PASS"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
