#!/usr/bin/env python3
"""Comprehensive Crucible Test Suite for The Enclave of the 16 (WP-5).

Supports execution via `pytest`, `python3 -m unittest`, and `python3 tests/test_enclave_crucible.py`.
Tests:
1. All 16 Constitutional Laws (L01..L16) on the canonical repository.
2. All 16 Hostile Negative-Control Fixtures (hostile_01..16.json -> 16/16 REJECTED by exact law).
3. Wave 1 Modules:
   - WP-1: 16 character cores, 8 Grand Projects, lorebook, 120-pair relationship matrix.
   - WP-2: Chronosphere, Magneto-Weather, Whole-Trait State ODE, Centered Domain Friction,
     Cassandra Drama Director, and 3-Sol Shadow Economy Ledger.
   - WP-3: 10-Block Budgeted Context Compiler, Smallville Memory Stream & Evidence-Cited
     Reflections, and Controlled Big Five Counterfactual Lab.
4. Wave 2 Modules:
   - WP-4: Story Sifter, Evening Dispatch Newscaster & Faithfulness Verifier, and
     Psychometric Drift Z-Score Auditor (with seamless WP-4 / fallback linking).
   - WP-5: JulesEnclaveDispatcher (Law L14 270/300 ceiling & F-120 stalled-session reaper),
     SingleIntegrator, Deterministic Replay, Rollback/Rebuild Self-Repair, and Full Sol 1 Simulation.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Any
import unittest

try:
    import pytest  # type: ignore[import-not-found]
except ImportError:
    pytest = None

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
    CANONICAL_16_MBTI,
    LAWS_REGISTRY,
    validate_proposal,
    validate_repository,
)
from tools.check_hostile_proposals import (
    EXPECTED_HOSTILE_FIXTURES,
    run_hostile_suite,
)
from tools.integrator import (
    SingleIntegrator,
    rebuild_state_from_events,
    rollback_to_tick,
)
from tools.jules_enclave_dispatcher import (
    HARD_DISPATCH_CEILING_24H,
    JulesEnclaveDispatcher,
    build_session_payload,
)
from tools.run_sol_simulation import (
    fallback_audit_character_drift,
    fallback_compile_evening_dispatch,
    fallback_sift_events,
    fallback_verify_dispatch_faithfulness,
    run_simulation,
)


def _create_sandbox_repo(base_dir: Path) -> Path:
    """Create an isolated sandbox copy of canonical files for stateful simulation tests."""
    sandbox = base_dir / "enclave_sandbox"
    shutil.copytree(REPO_ROOT / "canon", sandbox / "canon")
    shutil.copytree(REPO_ROOT / "relationships", sandbox / "relationships")
    return sandbox


# ============================================================================
# 1. 16 CONSTITUTIONAL LAWS & 16 HOSTILE FIXTURES
# ============================================================================
def test_repository_passes_all_16_constitutional_laws() -> None:
    res = validate_repository(repo_root=REPO_ROOT, strict=True)
    assert res["valid"] is True, f"Repository failed laws {res['violated_laws']}: {res['errors']}"
    assert res["laws_checked"] == 16
    assert res["laws_passed"] == 16


def test_hostile_suite_rejects_all_16_fixtures() -> None:
    summary = run_hostile_suite(repo_root=REPO_ROOT)
    assert summary["total_fixtures"] == 16
    assert summary["rejected_count"] == 16
    assert summary["all_passed"] is True


def _check_single_hostile_fixture(filename: str, expected_law: str) -> None:
    fpath = REPO_ROOT / "tests" / "hostile_proposals" / filename
    assert fpath.is_file(), f"Missing hostile fixture {fpath}"
    proposal = json.loads(fpath.read_text(encoding="utf-8"))
    res = validate_proposal(proposal, repo_root=REPO_ROOT)
    assert res["valid"] is False, f"{filename} was unexpectedly accepted!"
    assert res["violated_laws"] == [expected_law], (
        f"{filename} expected violation [{expected_law}], got {res['violated_laws']}: {res['errors']}"
    )


if pytest is not None:

    @pytest.mark.parametrize("filename,expected_law", EXPECTED_HOSTILE_FIXTURES)
    def test_individual_hostile_fixture_rejected_by_exact_law(filename: str, expected_law: str) -> None:
        _check_single_hostile_fixture(filename, expected_law)
else:

    def test_individual_hostile_fixture_rejected_by_exact_law() -> None:
        for filename, expected_law in EXPECTED_HOSTILE_FIXTURES:
            _check_single_hostile_fixture(filename, expected_law)


# ============================================================================
# 2. WAVE 1 MODULES (WP-1, WP-2, WP-3)
# ============================================================================
def test_wp1_canon_bijection_and_120_pair_matrix() -> None:
    char_files = sorted((REPO_ROOT / "canon" / "characters").glob("*.core.json"))
    assert len(char_files) == 16
    seen_mbtis = set()
    for cf in char_files:
        data = json.loads(cf.read_text(encoding="utf-8"))
        mbti = data["tier_4_self_concept_and_narrative_arc"]["cognitive_lens"]["mbti_type"]
        seen_mbtis.add(mbti)
    assert seen_mbtis == CANONICAL_16_MBTI

    projects = json.loads((REPO_ROOT / "canon" / "projects" / "grand_projects.json").read_text(encoding="utf-8"))
    assert len(projects["projects"]) == 8

    rel_matrix = json.loads((REPO_ROOT / "relationships" / "initial_matrix_120.json").read_text(encoding="utf-8"))
    assert len(rel_matrix["pairs"]) == 120
    assert all(0.35 <= float(p["bond_strength"]) <= 1.0 for p in rel_matrix["pairs"])


def test_wp2_deterministic_physics_state_ode_and_shadow_economy() -> None:
    c1_a = initial_chronosphere("seed_alpha")
    c1_b = initial_chronosphere("seed_alpha")
    assert c1_a == c1_b
    assert c1_a["day_phase"] == "DAWN_SHIFT"

    c2 = advance_tick(c1_a, "seed_alpha")
    assert c2["tick_id"] == 2
    assert c2["day_phase"] == "MIDDAY_EXPEDITION"

    w2_a = compute_exoplanet_weather(2, 1, "MIDDAY_EXPEDITION", "seed_alpha")
    w2_b = compute_exoplanet_weather(2, 1, "MIDDAY_EXPEDITION", "seed_alpha")
    assert w2_a == w2_b
    assert 1.0 <= w2_a["kp_exo"] <= 9.0

    silas_core = json.loads(
        (REPO_ROOT / "canon" / "characters" / "enclave_03_silas.core.json").read_text(encoding="utf-8")
    )
    orig_core = copy.deepcopy(silas_core)
    st = sample_character_state(
        core_card=silas_core,
        prev_state={"stress": 0.35, "fatigue": 0.20, "polarity_inversion_cooldown_days": 0},
        world_slice=w2_a,
        active_situation={"tick_id": 2, "day_phase": "MIDDAY_EXPEDITION", "location": "The_First_Forge"},
        rng_seed="seed_alpha:silas",
    )
    assert silas_core == orig_core, "Law L05: core_card must never be mutated in place"
    assert 0.0 <= st["stress"] <= 1.0
    assert st["polarity_inversion_active"] is False

    assert compute_domain_friction([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]) == 0.0
    assert compute_domain_friction([0.2, 0.2, 0.2], [0.8, 0.8, 0.8]) == 0.0
    diff_f = compute_domain_friction([0.9, 0.1, 0.2], [0.1, 0.9, 0.8])
    assert 0.0 < diff_f <= 1.0

    feast_beat = evaluate_pacing_and_beat([], colony_sol=1, day_phase="THE_FEAST")
    assert feast_beat["pacing_state"] == "RELAX_FEAST"
    assert feast_beat["scene_archetype"] == "THE_FEAST_CONVERGENCE"
    assert feast_beat["lethality"] == 0

    prank = seed_shadow_prank("enclave_01_hector", "enclave_03_silas", "enclave_13_ryn", origin_sol=1)
    pending_s2, matured_s2 = process_shadow_ledger([prank], current_sol=2)
    assert len(pending_s2) == 1 and len(matured_s2) == 0
    pending_s4, matured_s4 = process_shadow_ledger(pending_s2, current_sol=4)
    assert len(pending_s4) == 0 and len(matured_s4) == 1
    assert matured_s4[0]["lethality"] == 0
    assert len({matured_s4[0]["node_a"], matured_s4[0]["node_b"], matured_s4[0]["node_c"]}) == 3


def test_wp3_context_compiler_memory_stream_and_counterfactual_lab() -> None:
    silas_core = json.loads(
        (REPO_ROOT / "canon" / "characters" / "enclave_03_silas.core.json").read_text(encoding="utf-8")
    )
    hector_core = json.loads(
        (REPO_ROOT / "canon" / "characters" / "enclave_01_hector.core.json").read_text(encoding="utf-8")
    )
    rel_matrix = json.loads((REPO_ROOT / "relationships" / "initial_matrix_120.json").read_text(encoding="utf-8"))
    lorebook = json.loads((REPO_ROOT / "canon" / "lore_cards" / "lorebook.json").read_text(encoding="utf-8"))
    lore_entries = lorebook.get("entries") or lorebook.get("cards") or []

    ctx = compile_scene_context(
        pov_core=silas_core,
        pov_state={"tick_id": 1, "stress": 0.34, "fatigue": 0.22},
        world_snapshot={"tick_id": 1, "colony_sol": 1, "chronosphere": initial_chronosphere("seed")},
        interlocutor_cores=[hector_core],
        relationships=rel_matrix,
        lorebook=lore_entries,
        memories=[],
        rolling_summary="Sol 1 Dawn Shift.",
        prev_segment_text="Silas checked the gauge.",
        authors_note={"next_pov_target": "enclave_01_hector", "science_vegetable": "Metallurgy"},
        max_tokens=3500,
    )
    assert ctx["full_cards_loaded_count"] == 1
    assert ctx["total_tokens"] <= 3500
    assert [b["block_index"] for b in ctx["manifest"]["blocks"]] == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]

    for bad_cites in ([], ["evt_fake"]):
        raised = False
        try:
            build_reflection_record("enclave_03_silas", 4, 1, "Invalid", bad_cites, {"evt_1"})
        except ValueError as exc:
            raised = "Law L08" in str(exc)
        assert raised is True

    valid_refl = build_reflection_record("enclave_03_silas", 4, 1, "Grounded insight", ["evt_1"], {"evt_1"})
    assert valid_refl["cited_event_ids"] == ["evt_1"]

    retrieved = retrieve_top_memories([valid_refl], "Grounded insight", current_hour=30.0, top_k=1)
    assert len(retrieved) == 1
    assert retrieved[0]["last_accessed_hour"] == 30.0

    cf = build_counterfactual_variants(silas_core, {"rng_seed": "fixed_seed"}, "openness", 0.50)
    assert cf["baseline"]["rng_seed"] == cf["variant"]["rng_seed"] == "fixed_seed"
    assert 0.05 <= cf["variant_mean"] <= 0.95


# ============================================================================
# 3. WAVE 2 MODULES (WP-4 LINKING, DISPATCHER, INTEGRATOR, SIMULATION & SELF-REPAIR)
# ============================================================================
def test_wp4_drift_circuit_breaker_and_dispatch_verification() -> None:
    silas_core = json.loads(
        (REPO_ROOT / "canon" / "characters" / "enclave_03_silas.core.json").read_text(encoding="utf-8")
    )
    drifted_samples = [{"openness": 0.85, "conscientiousness": 0.96, "extraversion": 0.15, "agreeableness": 0.22, "neuroticism": 0.58}]
    audit = fallback_audit_character_drift(silas_core, drifted_samples)
    assert audit["max_abs_z"] > 2.0
    assert audit["drift_alert"] is True
    assert audit["re_anchor_ticks"] == 3
    assert len(audit["corrective_authors_note"].strip()) > 0


def test_jules_dispatcher_budget_guard_and_f120_reaper(tmp_path: Path | None = None) -> None:
    with tempfile.TemporaryDirectory() as td:
        base = tmp_path if tmp_path is not None else Path(td)
        budget_file = base / "budget.json"
        dispatcher = JulesEnclaveDispatcher(repo_root=REPO_ROOT, budget_file=budget_file, dry_run=True)

        tick_res = dispatcher.dispatch_tick_sessions(tick_id=1, colony_sol=1, persist=True)
        assert tick_res["sessions_dispatched"] == 2
        assert tick_res["rolling_24h_dispatched"] == 2

        stalled_list = [
            {
                "session_id": "sess_awaiting_plan",
                "state": "AWAITING_PLAN_APPROVAL",
                "started_at_iso": "2026-10-25T00:00:00Z",
                "task_bucket": "POV_RASHOMON_RELAY_SCENES",
            },
            {
                "session_id": "sess_timed_out",
                "state": "RUNNING",
                "started_at_iso": "2026-10-25T00:00:00Z",
                "task_bucket": "POV_RASHOMON_RELAY_SCENES",
                "tick_id": 1,
                "colony_sol": 1,
                "target_path": "story/segments/seg_retry.json",
            },
        ]
        reap_res = dispatcher.reap_stalled_sessions(
            sessions=stalled_list,
            now_iso="2026-10-25T01:00:00Z",
            timeout_minutes=25,
            persist=True,
        )
        assert reap_res["auto_replied_count"] == 1
        assert reap_res["reaped_count"] == 1
        assert reap_res["retried_count"] == 1


def test_full_sol_simulation_deterministic_replay_and_rollback_self_repair(tmp_path: Path | None = None) -> None:
    with tempfile.TemporaryDirectory() as td:
        base = tmp_path if tmp_path is not None else Path(td)
        sandbox_a = _create_sandbox_repo(base / "run_a")
        sandbox_b = _create_sandbox_repo(base / "run_b")

        res_a = run_simulation(sols=1, verify_dispatch=True, repo_root=sandbox_a, epoch_seed="crucible_seed_42")
        res_b = run_simulation(sols=1, verify_dispatch=True, repo_root=sandbox_b, epoch_seed="crucible_seed_42")

        assert res_a["health"]["status"] == "HEALTHY"
        assert res_a["health"]["constitutional_audit_valid"] is True
        assert res_a["health"]["ticks_completed"] == 4

        snap_a = json.loads((sandbox_a / "snapshots" / "latest.json").read_text(encoding="utf-8"))
        snap_b = json.loads((sandbox_b / "snapshots" / "latest.json").read_text(encoding="utf-8"))
        assert snap_a == snap_b

        dispatch_a = json.loads((sandbox_a / "digests" / "daily" / "sol_001_dispatch.json").read_text(encoding="utf-8"))
        dispatch_b = json.loads((sandbox_b / "digests" / "daily" / "sol_001_dispatch.json").read_text(encoding="utf-8"))
        assert dispatch_a == dispatch_b

        shutil.rmtree(sandbox_a / "snapshots")
        (sandbox_a / "relationships" / "graph.json").unlink()
        rebuilt = rebuild_state_from_events(repo_root=sandbox_a, epoch_seed="crucible_seed_42", write_files=True)
        assert rebuilt["latest_snapshot"] == snap_b
        assert (sandbox_a / "snapshots" / "latest.json").is_file()
        assert (sandbox_a / "relationships" / "graph.json").is_file()

        rb = rollback_to_tick(tick_id=2, repo_root=sandbox_a, epoch_seed="crucible_seed_42")
        assert rb["rolled_back_to_tick"] == 2
        assert rb["latest_tick"] == 2
        assert rb["latest_snapshot"]["day_phase"] == "MIDDAY_EXPEDITION"


def test_showrunner_dm_lpi_local_ai_manager_and_300_session_standby() -> None:
    from engine.drama_director import compute_living_playability_index
    from engine.local_ai_manager import LocalContextAwareManager, verify_calypso_narrative_purity
    from tools.check_enclave_constitutions import validate_showrunner_storytelling_contract
    from tools.enclave_fleet_ctl import compute_cross_fleet_rolling_telemetry, run_reaper_tick, run_wave_tick
    from tools.jules_enclave_dispatcher import CANONICAL_TASK_BUCKETS

    # 1. Verify Showrunner DM ledger & LPI classification
    beat = evaluate_pacing_and_beat([], colony_sol=1, day_phase="MIDDAY_EXPEDITION")
    assert "showrunner_ledger" in beat
    sr_val = validate_showrunner_storytelling_contract(beat)
    assert sr_val["valid"] is True, f"Showrunner validation failed: {sr_val['errors']}"
    assert beat["lpi_metrics"]["classification"] == "Campaign-Ready"

    unplayable = compute_living_playability_index(0.15, 0.20, 0.10, 0.15)
    assert unplayable["classification"] == "Unplayable Draft"
    bad_val = validate_showrunner_storytelling_contract(
        {"lpi_metrics": unplayable, "prose": "Hector rolled against AC: 18 and took HP = 24 damage."}
    )
    assert bad_val["valid"] is False
    assert any("Unplayable Draft" in e for e in bad_val["errors"])
    assert any("CALYPSO violation" in e for e in bad_val["errors"])

    cal_ok, _ = verify_calypso_narrative_purity("Silas adjusted the phosphor-bronze louver as sparks danced.")
    assert cal_ok is True

    # 2. Verify LocalContextAwareManager & 5-Section Task Card
    mgr = LocalContextAwareManager(repo_root=REPO_ROOT)
    sympathy = mgr.evaluate_hardware_sympathy()
    assert "allowed" in sympathy
    card = mgr.compile_enclave_5section_task_card(
        task_bucket="POV_RASHOMON_RELAY_SCENES",
        colony_sol=1,
        tick_id=2,
        day_phase="MIDDAY_EXPEDITION",
        target_path="story/segments/seg_s001_t0002_test.json",
        showrunner_pacing_mode="MULLIGAN_CRISIS",
        failure_lesson="Ensure strict single-POV Rashomon baton handoff.",
        use_local_ollama=False,
    )
    assert card["status"] == "COMPILED"
    assert len(card["sections"]) == 6
    assert "DO NOT call get_workspace on Linear" in card["prompt"]
    assert "@ENT[" in card["prompt"]

    # 3. Verify 36-Wave x 40m = 1,440m (300-Session Rolling-24h) Schedule Simulation
    dispatcher = JulesEnclaveDispatcher(repo_root=REPO_ROOT, dry_run=True)
    sim24 = dispatcher.simulate_24h_300_session_plan()
    assert sim24["valid_300_session_plan"] is True
    assert sim24["total_waves"] == 36
    assert sim24["total_span_minutes"] == 1440
    assert sim24["scheduled_dispatched_24h"] == 225
    assert sim24["auto_retry_reserve_available"] == 30
    assert sim24["rolling_safety_buffer"] == 45
    assert sim24["max_concurrent_vms_per_wave"] == 8
    assert sim24["task_buckets_consumed"] == CANONICAL_TASK_BUCKETS
    assert sim24["slot_reclamation_verified_at_24h02m"]["reclaimed_slots"] == 4

    # 4. Verify Standby Launch Gate & CP-11 Manifest
    wave_noop = run_wave_tick(repo_root=REPO_ROOT)
    assert wave_noop["status"] == "STANDBY_NOOP"
    assert wave_noop["sessions_dispatched"] == 0
    reap_noop = run_reaper_tick(repo_root=REPO_ROOT)
    assert reap_noop["status"] == "STANDBY_REAPER_HEARTBEAT"
    telemetry = compute_cross_fleet_rolling_telemetry(repo_root=REPO_ROOT)
    assert telemetry["enclave_launch_state"] == "STANDBY"
    assert (REPO_ROOT / "capsule.manifest.json").is_file()
    assert (REPO_ROOT / "aegis_lds_theme.tres").is_file()


class TestEnclaveCrucible(unittest.TestCase):
    """Unittest runner wrapper for environments without pytest installed."""

    def test_01_repository_passes_all_16_constitutional_laws(self) -> None:
        test_repository_passes_all_16_constitutional_laws()

    def test_02_hostile_suite_rejects_all_16_fixtures(self) -> None:
        test_hostile_suite_rejects_all_16_fixtures()

    def test_03_each_hostile_fixture_rejected_by_exact_law(self) -> None:
        for filename, expected_law in EXPECTED_HOSTILE_FIXTURES:
            with self.subTest(filename=filename, expected_law=expected_law):
                _check_single_hostile_fixture(filename, expected_law)

    def test_04_wp1_canon_bijection_and_120_pair_matrix(self) -> None:
        test_wp1_canon_bijection_and_120_pair_matrix()

    def test_05_wp2_deterministic_physics_state_ode_and_shadow_economy(self) -> None:
        test_wp2_deterministic_physics_state_ode_and_shadow_economy()

    def test_06_wp3_context_compiler_memory_stream_and_counterfactual_lab(self) -> None:
        test_wp3_context_compiler_memory_stream_and_counterfactual_lab()

    def test_07_wp4_drift_circuit_breaker_and_dispatch_verification(self) -> None:
        test_wp4_drift_circuit_breaker_and_dispatch_verification()

    def test_08_jules_dispatcher_budget_guard_and_f120_reaper(self) -> None:
        test_jules_dispatcher_budget_guard_and_f120_reaper()

    def test_09_full_sol_simulation_deterministic_replay_and_rollback_self_repair(self) -> None:
        test_full_sol_simulation_deterministic_replay_and_rollback_self_repair()

    def test_10_showrunner_dm_lpi_local_ai_manager_and_300_session_standby(self) -> None:
        test_showrunner_dm_lpi_local_ai_manager_and_300_session_standby()


if __name__ == "__main__":
    unittest.main(verbosity=2)

