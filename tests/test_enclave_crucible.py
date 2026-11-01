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
        retry_prompt = reap_res["retried"][0]["payload"]["prompt"]
        assert "# Aegis 5-Section Jules Task Card" in retry_prompt
        assert "## 2. MCP Directives" in retry_prompt
        saved_state = dispatcher.load_budget(now_iso="2026-10-25T01:00:00Z")
        assert saved_state["rolling_24h_dispatched"] == 3
        assert saved_state["retry_dispatched_24h"] == 1
        assert len(saved_state["eav_lessons"]) == 1
        assert saved_state["active_sessions"][0]["nudges"] == 1
        assert saved_state["active_sessions"][0]["last_nudge_at"] == "2026-10-25T01:00:00Z"


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
    assert "@ENT[" not in card["prompt"]
    assert "Natural-Language Verification Constraint" in card["prompt"]

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

    def test_11_live_jules_api_request_schema_oasis_twin_bridge_and_4fleet_governor(self) -> None:
        test_live_jules_api_schema_oasis_twin_bridge_and_4fleet_governor()

    def test_12_enclave_voxel_city_and_willow_animal_crossing_sim(self) -> None:
        test_enclave_voxel_city_and_willow_animal_crossing_sim()

    def test_13_pokemon_emerald_5_districts_and_6_step_tutorial(self) -> None:
        test_pokemon_emerald_5_districts_and_6_step_tutorial()

    def test_14_16_character_rashomon_scalpel_17th_node_and_atlas_compiler(self) -> None:
        test_16_character_rashomon_scalpel_17th_node_and_atlas_compiler()

    def test_15_cross_medium_narrative_and_computational_prose_calibration(self) -> None:
        test_cross_medium_narrative_and_computational_prose_calibration()

    def test_16_sovereign_march_tower_defense_and_4stage_epoch_merge(self) -> None:
        test_sovereign_march_tower_defense_and_4stage_epoch_merge()


def test_pokemon_emerald_5_districts_and_6_step_tutorial() -> None:
    from engine.enclave_city_sim import (
        ENCLAVE_BUILDINGS,
        ENCLAVE_EMERALD_DISTRICTS,
        ENCLAVE_INDOOR_ROOMS,
        ENCLAVE_ONBOARDING_TUTORIAL_STEPS,
        EnclaveVoxelCityEngine,
        perform_willow_ac_action,
    )

    # 1. Verify 5 Hoenn Districts partition all 18 buildings and 16 citizens cleanly
    assert set(ENCLAVE_EMERALD_DISTRICTS.keys()) == {
        "zone_01_homestead_grove",
        "zone_02_hearth_plaza",
        "zone_03_atlas_terrace",
        "zone_04_ferro_pier",
        "zone_05_forge_summit",
    }
    mapped_bldg_ids: list[str] = []
    mapped_cit_ids: list[str] = []
    for z in ENCLAVE_EMERALD_DISTRICTS.values():
        mapped_bldg_ids.extend(z["buildings"])
        mapped_cit_ids.extend(z["citizens"])
    assert len(mapped_bldg_ids) == 18
    assert set(mapped_bldg_ids) == {b["building_id"] for b in ENCLAVE_BUILDINGS}
    assert len(mapped_cit_ids) == 16
    assert set(mapped_cit_ids) == set(CANONICAL_16_CHARACTER_IDS)

    # 2. Verify 3 Enterable Indoor Rooms
    assert set(ENCLAVE_INDOOR_ROOMS.keys()) == {
        "room_willow_home",
        "room_hearth_galley",
        "room_atlas_museum",
    }

    # 3. Verify 6-Step Guided Onboarding Tutorial & Zone Warping
    assert [s["step_id"] for s in ENCLAVE_ONBOARDING_TUTORIAL_STEPS] == [
        "STEP_1_MEET_SOREN",
        "STEP_2_DIG_GEODE",
        "STEP_3_WATER_SPROUT",
        "STEP_4_CATCH_MOTH",
        "STEP_5_PLAZA_MEET_RYN",
        "STEP_6_MUSEUM_OR_HOMESTEAD",
    ]

    eng = EnclaveVoxelCityEngine(repo_root=REPO_ROOT, seed="enclave_sol_001")
    assert eng.state["active_zone_id"] == "zone_01_homestead_grove"
    assert eng.state["onboarding_tutorial"]["current_step_index"] == 1
    assert eng.state["onboarding_tutorial"]["completed"] is False

    # Step 1: advance_tutorial (Meet Mentor Soren & Terra)
    r1 = perform_willow_ac_action(eng.state, "advance_tutorial", {"step_id": "STEP_1_MEET_SOREN"})
    assert r1["ok"] is True
    assert eng.state["onboarding_tutorial"]["current_step_id"] == "STEP_2_DIG_GEODE"

    # Step 2..6 via matching actions
    for act, payload in (
        ("forage_dig", {"specimen_id": "spec_geode_bismuth"}),
        ("water_crop", {}),
        ("catch_critter", {"specimen_id": "spec_critter_prism_moth"}),
        (" warp_zone".strip(), {"zone_id": "zone_02_hearth_plaza"}),
        ("gift_citizen", {"target_id": "enclave_13_ryn", "item_id": "diy_herbal_liniment"}),
        ("warp_zone", {"room_id": "room_atlas_museum"}),
        ("donate_museum", {"specimen_id": "spec_geode_bismuth"}),
    ):
        res = perform_willow_ac_action(eng.state, act, payload)
        assert res["ok"] is True
        assert res["feed_entry"]["lethality"] == 0

    assert eng.state["onboarding_tutorial"]["completed"] is True
    assert len(eng.state["onboarding_tutorial"]["completed_step_ids"]) == 6
    assert eng.state["active_indoor_room_id"] == "room_atlas_museum"


def test_enclave_voxel_city_and_willow_animal_crossing_sim() -> None:
    from engine.enclave_city_sim import (
        DIY_RECIPES,
        ENCLAVE_BIOMES,
        ENCLAVE_BUILDINGS,
        ENCLAVE_EMERALD_DISTRICTS,
        ENCLAVE_INDOOR_ROOMS,
        ENCLAVE_ONBOARDING_TUTORIAL_STEPS,
        MUSEUM_CATALOG,
        SUITE_SYNERGY_ATLAS,
        WILLOW_AC_TOOLS,
        EnclaveVoxelCityEngine,
        generate_enclave_city_state,
        perform_willow_ac_action,
        summarize_enclave_city_state,
    )
    from engine.oasis_twin_bridge import (
        extract_enclave_twin_live_state,
        sync_enclave_oasis_save_and_bridge,
    )

    # 1. Verify 5 Biomes, 18 Buildings, 6 Tools, 16 Museum Specimens, 12 DIY Recipes & Suite Synergy Atlas
    assert len(ENCLAVE_BIOMES) == 5
    assert len(ENCLAVE_EMERALD_DISTRICTS) == 5
    assert len(ENCLAVE_INDOOR_ROOMS) == 3
    assert len(ENCLAVE_ONBOARDING_TUTORIAL_STEPS) == 6
    assert len(ENCLAVE_BUILDINGS) == 18
    assert len(WILLOW_AC_TOOLS) == 6
    assert len(MUSEUM_CATALOG) == 16
    assert len(DIY_RECIPES) == 12
    assert {"SR-02", "SR-04", "SR-05", "SR-08"} <= set(SUITE_SYNERGY_ATLAS.keys())

    recipe_ids = {r["recipe_id"] for r in DIY_RECIPES}
    assert "theme_enclave_first_forge" in recipe_ids
    assert "theme_enclave_living_atlas" in recipe_ids

    hearth_biomes = {b["hearth_biome"] for b in ENCLAVE_BUILDINGS}
    assert hearth_biomes == {"Porch Hearth", "Rain Garden", "Flow Hourglass", "Alchemist Crucible"}

    epistemic_tiers = {m["epistemic_tier"] for m in MUSEUM_CATALOG}
    assert epistemic_tiers == {
        "TIER_1_VERIFIED_EVENT",
        "TIER_2_EMPIRICAL_SPECIMEN",
        "TIER_3_ORAL_BALLAD",
        "TIER_4_SPECULATIVE_HYPOTHESIS",
    }

    city_a = generate_enclave_city_state(REPO_ROOT, seed="enclave_sol_001", biome_id="crater_valley")
    city_b = generate_enclave_city_state(REPO_ROOT, seed="enclave_sol_001", biome_id="crater_valley")
    assert city_a == city_b
    assert city_a["schema"] == "enclave-voxel-city-v2"
    assert city_a["grid_size"] == 48
    assert len(city_a["citizens"]) == 16
    assert len(city_a["buildings"]) == 18
    assert {c["character_id"] for c in city_a["citizens"]} == set(CANONICAL_16_CHARACTER_IDS)
    assert {c["mbti_type"] for c in city_a["citizens"]} == CANONICAL_16_MBTI
    assert "chronosphere" in city_a
    assert "weather" in city_a
    assert "drama_beat" in city_a
    assert "willow_silas_domain_friction" in city_a
    assert "cross_capsule_synergies" in city_a

    building_ids = {b["building_id"] for b in city_a["buildings"]}
    assert "bldg_willow_homestead" in building_ids
    assert "proj_07_living_atlas" in building_ids
    assert "proj_08_hearth_metabolic_engine" in building_ids

    # 2. Verify all Willow Animal Crossing Actions, 5 Constitutional Catalysts & Direct Engine Tick Reuse
    engine = EnclaveVoxelCityEngine(repo_root=REPO_ROOT, seed="enclave_sol_001")
    for act_type, payload in (
        ("forage_dig", {"specimen_id": "spec_geode_bismuth"}),
        ("catch_critter", {"specimen_id": "spec_critter_prism_moth"}),
        ("catch_fish", {"specimen_id": "spec_fish_ammonite"}),
        ("water_crop", {}),
        ("craft_diy", {"recipe_id": "diy_herbal_liniment"}),
        ("craft_diy", {"recipe_id": "theme_enclave_first_forge"}),
        ("place_decor", {"recipe_id": "diy_bismuth_lantern", "x": 19, "y": 29}),
        ("gift_citizen", {"target_id": "enclave_03_silas", "item_id": "diy_herbal_liniment"}),
        ("complete_daily_favor", {}),
        ("donate_museum", {"specimen_id": "spec_geode_bismuth"}),
    ):
        res = engine.perform_action(act_type, payload)
        assert res["ok"] is True
        assert res["rup_earned"] > 0
        assert res["feed_entry"]["lethality"] == 0

    for cat in ("feast", "prank", "expedition", "solar_flare", "harvest_moot"):
        cat_res = perform_willow_ac_action(engine.state, "trigger_catalyst", {"catalyst": cat})
        assert cat_res["ok"] is True
        assert cat_res["feed_entry"]["lethality"] == 0
        if cat == "feast":
            assert len(cat_res["feed_entry"]["actors"]) == 16

    tick_res = engine.advance_tick()
    assert tick_res["schema"] == "enclave-voxel-city-v2"
    assert engine.state["chronosphere"]["tick_id"] >= 2
    assert "kp_exo" in engine.state["weather"]

    summary = summarize_enclave_city_state(engine.state)
    assert summary["currency_code"] == "RUP"
    assert summary["in_world_economy_monetary"] is False
    assert summary["museum_donations_count"] >= 3
    assert summary["daily_favors_completed"] >= 1
    assert summary["willow_homestead_comfort_score"] > 100
    assert summary["bridge_global"] == "window.ArcadeAssetBridge"

    # 3. Verify Oasis Twin Bridge integration (enclaveCitySummary & enclave_city_state.json)
    live_state = extract_enclave_twin_live_state(REPO_ROOT)
    assert "enclaveCitySummary" in live_state
    assert live_state["enclaveCitySummary"]["schema"] == "enclave-voxel-city-v2"

    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        save_dir = base / "saves"
        bridge_file = base / "aegis_asset_bridge.json"
        sync_out = engine.sync_oasis_bridge(save_root=save_dir, bridge_path=bridge_file)
        assert (save_dir / "enclave_city_state.json").is_file()
        assert "enclave_city_state.json" in sync_out["sync_result"]["saved_files"]
        bridge_data = json.loads(bridge_file.read_text(encoding="utf-8"))
        assert bridge_data["currency_code"] == "RUP"
        assert bridge_data["currencyCode"] == "RUP"
        assert "enclaveCitySummary" in bridge_data

    # 4. Verify UI files (ui/enclave_city.html & ui/dispatch_viewer.html link + SR-02/04/05/08)
    city_html_path = REPO_ROOT / "ui" / "enclave_city.html"
    dispatch_html_path = REPO_ROOT / "ui" / "dispatch_viewer.html"
    assert city_html_path.is_file()
    city_html = city_html_path.read_text(encoding="utf-8")
    assert 'id="town-canvas"' in city_html
    assert "evergreen-dark" in city_html
    assert "evergreen-light" in city_html
    assert "high-contrast" in city_html
    assert "enclave_07_willow" in city_html
    assert "theme_enclave_first_forge" in city_html
    assert "theme_enclave_living_atlas" in city_html
    assert "Porch Hearth" in city_html
    assert "TIER_1_VERIFIED_EVENT" in city_html
    assert "window.ArcadeAssetBridge" in city_html
    assert "enclave_art_lighting.js" in city_html
    assert "EnclaveArtLighting.renderWorldPass" in city_html
    assert "EnclaveArtLighting.renderScreenPass" in city_html
    assert "dispatch_viewer.html" in city_html
    assert "LITTLEROOT HOMESTEAD GROVE" in city_html
    assert "STEP_1_MEET_SOREN" in city_html
    assert "01_front_0deg_rgba.png" in city_html
    assert "https://cdn." not in city_html

    art_lighting_path = REPO_ROOT / "ui" / "enclave_art_lighting.js"
    assert art_lighting_path.is_file()
    art_lighting_js = art_lighting_path.read_text(encoding="utf-8")
    assert "computeAtmosphericState" in art_lighting_js
    assert "renderWorldPass" in art_lighting_js
    assert "renderScreenPass" in art_lighting_js
    assert "reducedMotion" in art_lighting_js

    antifragile_schema_path = REPO_ROOT / "canon" / "schemas" / "enclave_city_antifragile_contract.json"
    assert antifragile_schema_path.is_file()
    antifragile_contract = json.loads(antifragile_schema_path.read_text(encoding="utf-8"))
    assert antifragile_contract["schema_version"] == "enclave_city_antifragile_contract_v2.0.0"
    assert antifragile_contract["contract_id"] == "lfs-enclave-city-antifragile-contract-v2"

    dispatch_html = dispatch_html_path.read_text(encoding="utf-8")
    assert 'href="enclave_city.html"' in dispatch_html


def test_live_jules_api_schema_oasis_twin_bridge_and_4fleet_governor() -> None:
    from engine.oasis_twin_bridge import sync_enclave_oasis_save_and_bridge
    from tools.enclave_fleet_ctl import compute_cross_fleet_rolling_telemetry
    from tools.jules_enclave_dispatcher import (
        JulesRestClient,
        build_live_jules_api_request,
    )

    # 1. Verify canonical live Google Jules /v1alpha/sessions request schema (CRUCIBLE-11)
    payload = build_session_payload(
        task_bucket="MORNING_INTENTS_16_NODES",
        tick_id=1,
        colony_sol=1,
        target_path="events/evt_s001_t0001_morning_intent.json",
        prompt_text="Synthesize Dawn Shift morning intents.",
    )
    live_req = build_live_jules_api_request(payload)
    assert live_req["requirePlanApproval"] is False
    assert live_req["automationMode"] == "AUTO_CREATE_PR"
    assert live_req["sourceContext"] == {
        "source": "sources/github/SyrisBruhh42/enclave-digital-twin",
        "githubRepoContext": {"startingBranch": "main"},
    }

    # 2. Verify live JulesRestClient + 5-part antifragile reaper/integrator in sandbox
    with tempfile.TemporaryDirectory() as td:
        base = Path(td)
        sandbox = _create_sandbox_repo(base)
        shutil.copytree(REPO_ROOT / "ops", sandbox / "ops")
        run_simulation(sols=1, verify_dispatch=True, repo_root=sandbox, epoch_seed="crucible_seed_42")

        recorded_calls: list[tuple[str, str, Any]] = []
        valid_salvage_event = {
            "event_id": "evt_s001_t0004_salvaged_note",
            "tick_id": 4,
            "colony_sol": 1,
            "day_phase": "THE_FEAST",
            "world_timestamp_iso": "2026-10-25T18:00:00Z",
            "base_snapshot_tick": 4,
            "event_type": "MORNING_INTENT",
            "location": "The_Hub_Hearth",
            "actors": ["enclave_07_willow", "enclave_03_silas"],
            "summary": "Willow calibrated the acoustic damper beside Silas's bench.",
            "importance": 6.5,
            "novelty_score": 0.65,
            "lethality": 0,
            "science_vegetable": "Magnetohydrodynamic damper tuning",
            "state_deltas": {"stress_delta": -0.02},
            "relationship_deltas": [],
            "evidence_refs": ["feast_sol_001"],
        }
        diff_lines = [
            "--- /dev/null",
            "+++ b/events/evt_s001_t0004_salvaged_note.json",
            "@@ -0,0 +1,20 @@",
        ] + [f"+{line}" for line in json.dumps(valid_salvage_event, indent=2).splitlines()]
        unidiff_str = "\n".join(diff_lines)

        def mock_transport(method: str, url: str, body: dict[str, Any] | None) -> dict[str, Any]:
            recorded_calls.append((method, url, body))
            if method == "POST" and url.endswith("/v1alpha/sessions"):
                return {"name": "sessions/9988776655", "state": "RUNNING"}
            if method == "GET" and url.endswith("/sessions/sess_open_pr"):
                return {
                    "name": "sessions/sess_open_pr",
                    "state": "AWAITING_USER_FEEDBACK",
                    "outputs": [{"pullRequest": {"url": "https://github.com/SyrisBruhh42/enclave-digital-twin/pull/12"}}],
                }
            if method == "GET" and url.endswith("/sessions/sess_plan"):
                return {"name": "sessions/sess_plan", "state": "AWAITING_PLAN_APPROVAL"}
            if method == "GET" and url.endswith("/sessions/sess_completed_cs"):
                return {"name": "sessions/sess_completed_cs", "state": "COMPLETED", "outputs": []}
            if method == "GET" and "/activities" in url:
                return {
                    "activities": [
                        {"artifacts": [{"changeSet": {"gitPatch": {"unidiffPatch": unidiff_str}}}]}
                    ]
                }
            return {"ok": True}

        client = JulesRestClient(base_url="http://127.0.0.1:9445", api_key="test_key", transport=mock_transport)
        live_disp = JulesEnclaveDispatcher(
            repo_root=sandbox,
            budget_file=base / "live_budget.json",
            dry_run=False,
            rest_client=client,
        )
        d_res = live_disp.dispatch_session(payload, now_iso="2026-10-25T12:00:00Z", persist=True)
        assert d_res["dispatched"] is True
        assert d_res["remote_session_id"] == "9988776655"

        # Verify 4-fleet live quota governor blocks when peer factories consume ceiling
        capped_state = live_disp.load_budget(now_iso="2026-10-25T12:05:00Z")
        capped_state["peer_live_dispatched_24h"] = 269
        allowed_4fleet, reason_4fleet = live_disp.can_dispatch(capped_state, requested_count=1)
        assert allowed_4fleet is False
        assert "unified 4-fleet hard ceiling" in reason_4fleet

        reap_live = live_disp.reap_stalled_sessions(
            sessions=[
                {
                    "session_id": "sess_open_pr",
                    "state": "AWAITING_USER_FEEDBACK",
                    "started_at_iso": "2026-10-25T10:00:00Z",
                    "pr_checks_green": True,
                },
                {
                    "session_id": "sess_plan",
                    "state": "AWAITING_PLAN_APPROVAL",
                    "started_at_iso": "2026-10-25T11:50:00Z",
                },
                {
                    "session_id": "sess_completed_cs",
                    "state": "COMPLETED",
                    "started_at_iso": "2026-10-25T11:45:00Z",
                    "tick_id": 4,
                    "target_path": "events/evt_s001_t0004_salvaged_note.json",
                },
            ],
            now_iso="2026-10-25T12:05:00Z",
            persist=True,
        )
        assert reap_live["auto_replied_count"] == 1
        assert reap_live["integrated_count"] == 1
        assert (sandbox / "events" / "evt_s001_t0004_salvaged_note.json").is_file()
        assert any(":approvePlan" in u for _, u, _ in recorded_calls)

        # 3. Verify Oasis Twin Bridge (CRUCIBLE-14): save.lineage.json + RUP meta-rewards + enclave_07_willow ODE
        save_dir = base / "oasis_saves" / "enclave-digital-twin"
        bridge_file = base / "lfs-aegis" / "aegis_asset_bridge.json"
        sync_res = sync_enclave_oasis_save_and_bridge(
            repo_root=sandbox,
            save_root=save_dir,
            bridge_path=bridge_file,
        )
        assert (save_dir / "save.lineage.json").is_file()
        assert (save_dir / "enclave_city_state.json").is_file()
        assert sync_res["lineage"]["schema"] == "aegisEnvelopeV1-save-lineage"
        assert sync_res["lineage"]["project_id"] == "PA-15"
        assert sync_res["meta_rewards"]["currency_code"] == "RUP"
        assert sync_res["meta_rewards"]["total_earned_rupees"] >= 35
        assert sync_res["meta_rewards"]["in_world_economy_monetary"] is False
        bridge_json = json.loads(bridge_file.read_text(encoding="utf-8"))
        assert bridge_json["currency_code"] == "RUP"
        assert bridge_json["currencyCode"] == "RUP"
        assert "enclave_07_willow" in bridge_json["enclaveTwinLiveState"]["character_states"]
        assert bridge_json["enclaveTwinLiveState"]["willow_resonance"]["character_id"] == "enclave_07_willow"
        assert bridge_json["enclaveCitySummary"]["schema"] == "enclave-voxel-city-v2"

    # 4. Verify 4-factory telemetry, PA-15 project_id, manifest entrypoint & zero hardcoded home paths (UMB-01)
    telemetry = compute_cross_fleet_rolling_telemetry(repo_root=REPO_ROOT)
    assert len(telemetry["cross_fleet_rolling_24h"]["factories_tracked"]) == 4
    assert "willow-guild-factory" in telemetry["cross_fleet_rolling_24h"]["factories_tracked"]
    cfg = json.loads((REPO_ROOT / "ops" / "config.json").read_text(encoding="utf-8"))
    assert cfg["project_id"] == "PA-15"
    manifest = json.loads((REPO_ROOT / "capsule.manifest.json").read_text(encoding="utf-8"))
    assert manifest["entrypoint"] == "tools/run_sol_simulation.py"

    forbidden_home = "/home/" + "joe"
    for p in REPO_ROOT.rglob("*"):
        if not p.is_file() or "__pycache__" in p.parts or ".git" in p.parts:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except Exception:
            continue
        assert forbidden_home not in text, f"UMB-01 violation: {forbidden_home} found in {p}"


def test_wp4_predispatch_verifier_constraint_compiler_and_crdt_commutativity() -> None:
    """Verify WP-4 PreDispatchContractVerifier, FailureToConstraintCompiler, Lockstep Barrier & CRDT Commutativity."""
    from engine.local_ai_manager import FailureToConstraintCompiler
    from tools.check_enclave_constitutions import (
        PreDispatchContractVerifier,
        PreDispatchVerificationError,
        check_no_hallucinated_diagnostic_keys,
    )
    from tools.enclave_fleet_ctl import _compute_disk_verified_barrier
    from tools.integrator import _riemannian_logit_step

    try:
        PreDispatchContractVerifier.verify_brief_before_dispatch(
            "Create lore/proposals/card.json", "lore/proposals/card.json"
        )
        raise AssertionError("Expected PreDispatchVerificationError for lore/proposals/")
    except PreDispatchVerificationError:
        pass

    PreDispatchContractVerifier.verify_brief_before_dispatch(
        "Create lore/proposed/card.json", "lore/proposed/card.json"
    )
    ok_clean, _ = check_no_hallucinated_diagnostic_keys({"segment_id": "seg_test"})
    assert ok_clean is True
    ok_polluted, _ = check_no_hallucinated_diagnostic_keys(
        {"segment_id": "seg_test", "retry_recovery_mode": "SECOND_PASS_SELF_REPAIR"}
    )
    assert ok_polluted is False

    compiled_constraint = FailureToConstraintCompiler.compile_constraint(
        entity="enclave:test",
        attr="second_pass_repair_constraint",
        value="@ENT[enclave:1] | @ATTR[changeset_gate_rejection] = error_type",
    )
    assert "@ENT" not in compiled_constraint
    assert "second_pass_repair_constraint" not in compiled_constraint
    assert FailureToConstraintCompiler.compile_constraint(value=compiled_constraint) == compiled_constraint

    next_sol_barrier, next_tick_barrier = _compute_disk_verified_barrier(REPO_ROOT)
    assert next_sol_barrier >= 8
    assert next_tick_barrier >= 32

    latest_snap = json.loads((REPO_ROOT / "snapshots" / "latest.json").read_text(encoding="utf-8"))
    assert latest_snap["tick_id"] >= 30
    assert latest_snap["colony_sol"] >= 8
    assert len(latest_snap.get("recent_segments", [])) > 0
    assert 8 in latest_snap.get("available_sols", [])

    # Verify Riemannian logit step commutativity: step(step(x, d1), d2) == step(step(x, d2), d1) == step(x, d1 + d2)
    s_ab = _riemannian_logit_step(_riemannian_logit_step(0.42, -0.06), 0.09)
    s_ba = _riemannian_logit_step(_riemannian_logit_step(0.42, 0.09), -0.06)
    s_sum = _riemannian_logit_step(0.42, -0.06 + 0.09)
    assert abs(s_ab - s_ba) < 1e-12
    assert abs(s_ab - s_sum) < 1e-12


def test_16_character_rashomon_scalpel_17th_node_and_atlas_compiler() -> None:
    """Verify full 16-character Rashomon Scalpel rotation, 17th-Node Clean-Slate Learner, and Atlas Bundle."""
    from engine.local_ai_manager import LocalContextAwareManager
    from engine.reader_character_learner import ReaderCharacterLearner
    from tools.check_enclave_constitutions import (
        CANONICAL_16_CHARACTER_IDS,
        get_rashomon_scalpel_pov_pair,
    )
    from tools.compile_enclave_to_atlas import compile_enclave_atlas_bundle
    from tools.local_enclave_showrunner import run_local_oasis_cycle

    # 1. Verify all 16 characters rotate across 16 ticks (4 Sols) with Dorian & Vex and Elara & Ryn
    seen_povs: set[str] = set()
    for tick in range(1, 17):
        sol = ((tick - 1) // 4) + 1
        pov, nxt = get_rashomon_scalpel_pov_pair(tick, sol)
        seen_povs.add(pov)
        assert pov != nxt
    assert seen_povs == set(CANONICAL_16_CHARACTER_IDS)
    assert "enclave_15_dorian" in seen_povs
    assert "enclave_14_vex" in seen_povs
    assert "enclave_16_elara" in seen_povs
    assert "enclave_13_ryn" in seen_povs

    # 2. Verify all 16 exemplars load cleanly and task cards include LOTR x Hollow Knight x Martian + Bourne competence
    mgr = LocalContextAwareManager(repo_root=REPO_ROOT)
    for cid in CANONICAL_16_CHARACTER_IDS:
        bundle = mgr.load_character_exemplar_and_core(cid)
        assert bundle["character_id"] == cid
        assert len(bundle["exemplar_opening"]) > 80

    sci = mgr.select_grand_project_science_vegetable(colony_sol=3, tick_id=9, active_pov_id="enclave_01_hector")
    assert "science_vegetable" in sci and "hollow_knight_atmosphere" in sci

    card = mgr.compile_enclave_5section_task_card(
        task_bucket="POV_RASHOMON_RELAY_SCENES",
        colony_sol=3,
        tick_id=9,
        day_phase="DAWN_SHIFT",
        target_path="story/segments/seg_s003_t0009_enclave_01_hector.json",
        active_pov_id="enclave_01_hector",
        next_pov_target="enclave_10_isla",
    )
    prompt = card["prompt"]
    assert "Hollow Knight" in prompt
    assert "The Martian" in prompt
    assert "NEVER print literal ALL-CAPS system verbs" in prompt

    # 3. Verify 17th-Node 100% Clean-Slate Onboarding + Margin Comment Learning + Offline Ghost-Pilot Evolution
    with tempfile.TemporaryDirectory() as td:
        state_file = Path(td) / "node17.json"
        learner = ReaderCharacterLearner(state_path=state_file, repo_root=REPO_ROOT)
        clean = learner.load_state()
        assert clean["initialized"] is False
        assert clean["onboarding_required"] is True
        assert clean["identity"]["name"] == ""

        init_state = learner.initialize_player_character(
            name="Vanguard",
            title="The Deep-Trench Cartographer",
            squad_affinity="VANGUARD",
            cognitive_style="COMPETENCE_TACTICIAN",
            signature_tool="Brass Resonance Theodolite",
            initial_question="What lies beneath the obsidian root-vault?",
        )
        assert init_state["initialized"] is True
        assert init_state["identity"]["name"] == "Vanguard"

        comment_state = learner.record_player_interaction(
            chapter_id="vol1_ch03_enclave_15_dorian",
            comment_text="Why didn't Dorian check the shear-strain gauge on the obsidian pylon before pressurizing?",
            focal_character_id="enclave_15_dorian",
            stance_tag="TACTICAL_HYPOTHESIS",
            colony_sol=22,
        )
        assert len(comment_state["margin_comments"]) == 1
        assert comment_state["margin_comments"][0]["responder_id"] == "enclave_15_dorian"
        assert "Vanguard" in comment_state["margin_comments"][0]["character_reply"]

        ghost_state = learner.advance_autonomous_offline_arc(sols_elapsed=2, current_sol=23)
        assert len(ghost_state["autonomous_offline_log"]) >= 3

        showrunner_res = run_local_oasis_cycle(
            repo_root=REPO_ROOT,
            advance_sim_sols=0,
            evolve_17th_node=False,
            compile_atlas=False,
        )
        assert showrunner_res["ok"] is True
        assert showrunner_res["constitutional_laws_passed"] == 16

    # 4. Verify Atlas Bundle compilation produces 16 Foundational Modules (Vol I) and >=22 Living Sols (Vol II)
    atlas_res = compile_enclave_atlas_bundle(repo_root=REPO_ROOT, with_audio=True)
    assert atlas_res["volume_1_count"] == 16
    assert atlas_res["volume_2_count"] >= 22


def test_cross_medium_narrative_and_computational_prose_calibration() -> None:
    """Verify the 6-Pillar Cross-Medium Narrative Architecture & Computational Prose Calibration Engine."""
    from engine.local_ai_manager import LocalContextAwareManager
    from engine.narrative_calibration_engine import (
        CHARACTER_SPINES,
        DiscoveryNode,
        EmergentTopologyEngine,
        FactionPowerMatrixEntry,
        MametDramaticCompressionGate,
        OralityAndAudioCalibrationEngine,
        PlantedClueNode,
        SceneBeat,
        SceneSequelPropulsionEngine,
        SequelBeat,
        TemporalInformationAsymmetryEngine,
        run_three_pass_de_ai_calibration,
        score_stop_slop_5d,
    )

    # 1. Verify all 16 character spines exist (including Dorian & Vex and Elara & Ryn)
    assert set(CHARACTER_SPINES.keys()) == set(CANONICAL_16_CHARACTER_IDS)

    # 2. Verify Swain Scene/Sequel + Parker-Stone But/Therefore + Stanton '2 + 2' + Micro MRU
    scene = SceneBeat(
        scene_id="sc_s028_t01",
        pov_character_id="enclave_15_dorian",
        goal="Anchor the obsidian vault compression ring before the twin-sun thermal tide peaks.",
        conflict="A hairline shear in the basalt footing threatens to buckle the primary tie-rod.",
        disaster_type="YES_BUT",
        disaster_outcome="The compression ring locks into place, but Vex's contraband bypass conduit ruptures the secondary coolant seal.",
        stanton_clue_a="A faint smell of ozonated copper lingered near the unsealed junction box.",
        stanton_clue_b="Three brass lock-washers from Vex's workbench sat on the warm manifold.",
        withheld_inference_4="Vex tapped the vault manifold to power the hidden shadow-market relay.",
        act_number=2,
    )
    sequel = SequelBeat(
        sequel_id="sq_s028_t01",
        pov_character_id="enclave_15_dorian",
        visceral_reaction="Steam stung Dorian's knuckles as his grip tightened on the torque wrench.",
        dilemma_option_a_cost="Vent the main manifold and lose twelve hours of vault pressurization.",
        dilemma_option_b_cost="Cross-couple Vex's uncertified splice directly into the load-bearing ring.",
        decision_therefore_goal="Cross-couple the rogue splice and haul Vex onto the catwalk to balance the phase load.",
    )
    prop_res = SceneSequelPropulsionEngine.validate_scene_sequel_pair(
        scene, sequel, connector_history=["BUT", "THEREFORE", "BUT"]
    )
    assert prop_res["valid"] is True
    assert prop_res["macro_bridge_scene_to_sequel"] == "BUT"
    assert prop_res["macro_bridge_sequel_to_next_scene"] == "THEREFORE"

    mru_res = SceneSequelPropulsionEngine.validate_mru_paragraph(
        stimulus="The Bourdon pressure gauge spiked past forty megapascals with a metallic ping.",
        visceral_reflex="Cold sweat prickled across Dorian's collarbones.",
        physical_action="He slammed the bronze bypass lever down to the second detent.",
        speech_or_thought='"Hold the manifold steady, Vex."',
    )
    assert mru_res["valid"] is True

    # 3. Verify David Mamet's 3-Question Litmus Gate, Danger Signals & Silent Movie Constraint
    mamet_ok = MametDramaticCompressionGate.evaluate_scene_unit(
        active_characters=["enclave_15_dorian", "enclave_14_vex"],
        who_wants_what="Dorian wants Vex to torque the secondary relief valve before the seal blows.",
        what_happens_if_denied="Superheated brine floods the lower arboretum root-vault.",
        why_now="The manifold pressure relief timer has ninety seconds remaining.",
        scene_logline="Dorian and Vex race to cross-couple a ruptured coolant manifold under load.",
        physical_actions_observed=[
            "Dorian wedges the phosphor-bronze crowbar beneath the jammed flange.",
            "Vex crimps the braided silver grounding strap across the live terminal.",
        ],
        dialogue_lines=['"Hand me the seven-millimeter socket before the gasket shears."'],
    )
    assert mamet_ok["passed"] is True

    mamet_bad = MametDramaticCompressionGate.evaluate_scene_unit(
        active_characters=["enclave_15_dorian", "enclave_14_vex"],
        who_wants_what="Talk",
        what_happens_if_denied="Nothing",
        why_now="Now",
        scene_logline="Dorian and Vex discuss what Silas did yesterday.",
        physical_actions_observed=["Sit"],
        dialogue_lines=['"As you both know, Silas built this forge three years ago."'],
        third_party_subject_id="enclave_03_silas",
    )
    assert mamet_bad["passed"] is False
    assert len(mamet_bad["danger_signals"]) == 3

    # 4. Verify Hitchcock Suspense & Knox/Christie Fair-Play Camouflage
    bomb = TemporalInformationAsymmetryEngine.build_hitchcock_bomb_ledger(
        threat_id="threat_prank_fuse_01",
        physical_mechanism="A 3-turn fermented spore timer ticking inside the Hearth spice rack.",
        countdown_ticks_remaining=3,
        mundane_foreground_activity="Ryn ladles warm root-stew while Augusta audits the salt ledger.",
        audience_informed=True,
        characters_informed=False,
    )
    assert bomb["mode"] == "HITCHCOCK_SUSPENSE"
    assert bomb["dramatic_irony_active"] is True

    fair_play = TemporalInformationAsymmetryEngine.verify_knox_christie_fair_play(
        [
            PlantedClueNode(
                clue_id="clue_01",
                revelation_id="rev_vault_harmonic",
                sensory_object="A cracked bismuth tuning fork wedged behind the tea tin",
                anchor_scene_id="vol1_ch07_enclave_13_ryn",
                camouflage_tactic="BURY_IN_TEXTURE",
                immediate_mundane_reading="Kitchen clutter on Ryn's prep shelf.",
                retroactive_reframed_meaning="Exact 432 Hz acoustic key required to unseal the Ediacaran sluice.",
            )
        ]
    )
    assert fair_play["valid"] is True

    # 5. Verify Orality (Glass / Abumrad / Carlin) & Emergent Topology (Alexander Inverted 3-Clue Rule)
    oral = OralityAndAudioCalibrationEngine.compose_calibrated_acoustic_script(
        chapter_id="vol1_ch14_enclave_16_elara",
        lead_specialist_name="Elara",
        co_specialist_name="Ryn",
        anecdote_with_bait="Elara scraped the bioluminescent lichen from the basalt core.",
        abumrad_gut_churn_doubt="Half of the chromatograph looked like terrestrial moss; the other half defied every amino table.",
        carlin_conflicting_source_a="Zara's spore survey classifies the mat as dormant.",
        carlin_conflicting_source_b="Kaio's magnetometer shows the mat pulsing in phase with the twin-sun aurora.",
        visceral_extreme_prompt="Picture standing ankle-deep in glowing subterranean water when the whole cavern inhales.",
        moment_of_reflection="Adaptation begins the second we stop demanding the planet speak terrestrial Latin.",
    )
    assert oral["gut_churn_index"] == 0.47
    assert len(oral["blocks"]) == 4

    topo_res = EmergentTopologyEngine.validate_inverted_three_clue_rule(
        [
            DiscoveryNode(
                node_id="node_ediacaran_sluice",
                title="The Subterranean Ediacaran Sluice Gate",
                incoming_clue_vectors=[
                    {"source": "Isla's lidar trench scan", "modality": "Geodesy"},
                    {"source": "Zara's root-turgor gradient", "modality": "Mycology"},
                    {"source": "Silas's slag-quench isotopic trace", "modality": "Metallurgy"},
                ],
            )
        ]
    )
    assert topo_res["valid"] is True

    toolbox = EmergentTopologyEngine.build_situation_toolbox(
        situation_id="sit_sector4_brine_surge",
        initial_state="High-pressure geothermal brine is rising 4 cm per minute in Sector 4.",
        factions=[
            FactionPowerMatrixEntry(
                faction_id="fac_forge_purists",
                identity="Silas & Dorian Structural Wing",
                acute_desire="Seal the bulkhead permanently with high-entropy alloy plates",
                method="Heavy mechanical lock-down",
                two_adjective_personality=("unyielding", "methodical"),
                resource_or_power="Primary arc-welding bus and crane gantry",
            )
        ],
        environmental_rules=["Brine conductivity shorts unshielded solenoids above 60 C."],
        chandler_door_kick_trigger="If specialists debate for >2 turns, the secondary sight-glass fractures.",
        mulligan_pre_roll_dc=15,
        focal_character_id="enclave_03_silas",
    )
    assert toolbox["prep_philosophy"] == "PREP_SITUATIONS_NOT_PLOTS"

    # 6. Verify 3-Pass De-AI Calibration & 5-D Stop-Slop Scorer (>= 35/50)
    raw_sloppy = (
        "Silas realized that the pressure was rising in the realm of the forge, a rich tapestry of "
        "unwavering resilience, a stark reminder of their struggle. Why? Because he felt nervous and "
        "shivers down his spine as he delved into the cacophony. It was a reminder that hope endures. "
        "Pure silence. Nothing more."
    )
    cal = run_three_pass_de_ai_calibration(raw_sloppy)
    cleaned = cal["calibrated_text"]
    assert "tapestry" not in cleaned.lower()
    assert "delved" not in cleaned.lower()
    assert "why? because" not in cleaned.lower()
    assert "pure silence. nothing more." not in cleaned.lower()

    gold_prose = (
        "Silas wedged the seven-millimeter feeler gauge between the phosphor-bronze louver and the basalt casing. "
        "The needle held steady at forty-two megapascals. Across the catwalk, Vex flicked a brass lock-washer into "
        "her palm, grinning as the secondary turbine settled into a clean, low-frequency hum."
    )
    gold_score = score_stop_slop_5d(gold_prose)
    assert gold_score["passed"] is True
    assert gold_score["total_score"] >= 35

    mgr = LocalContextAwareManager(repo_root=REPO_ROOT)
    audit = mgr.run_judge_and_tactician_audit(
        colony_sol=27,
        day_phase="MIDDAY_EXPEDITION",
        pacing_state="RISING_COMPETENCE",
        scene_archetype="PRECISION_ENGINEERING",
        science_vegetable="Fe-Co-Cr-Ni-Mn High-Entropy Alloy lattice stabilization",
        tension_score=0.62,
        candidate_prose=gold_prose,
    )
    assert audit["passed"] is True
    assert audit["stop_slop_audit"]["total_score"] >= 35


def test_sovereign_march_tower_defense_and_4stage_epoch_merge() -> None:
    from engine.sovereign_march_bridge import (
        ATTACK_VS_ARMOR_MATRIX,
        CATALYST_REACTIONS,
        HERO_CLASS_REGISTRY,
        SovereignMarchEpochBridge,
        can_promote_specialist_to_job,
        create_enclave_specialist_tower,
        evaluate_dyadic_resonance_on_grid,
        generate_event_seeded_battlefield,
        grant_specialist_ap,
        order_specialist_move,
        promote_specialist_job,
    )

    assert len(HERO_CLASS_REGISTRY) == 20
    assert len(ATTACK_VS_ARMOR_MATRIX) == 10
    assert len(CATALYST_REACTIONS) == 8

    # 1. Verify infinite level scaling and hybrid promotion (Swordplay Lv.2 + Cryomancy Lv.2 -> Geomancy)
    dorian = create_enclave_specialist_tower("u1", "enclave_15_dorian", "swordplay", 4, 4)
    vex = create_enclave_specialist_tower("u2", "enclave_14_vex", "pyromancy", 5, 4)
    assert can_promote_specialist_to_job(dorian, "geomancy") is False

    dorian = grant_specialist_ap(dorian, 120)
    assert dorian.job_levels["swordplay"] >= 2
    dorian.job_levels["cryomancy"] = 2
    assert can_promote_specialist_to_job(dorian, "geomancy") is True
    dorian = promote_specialist_job(dorian, "geomancy")
    assert dorian.job_id == "geomancy"

    # 2. Verify Movement Speed Decay curve and Dyadic Resonance
    dorian = order_specialist_move(dorian, 7, 5, between_waves=False)
    assert dorian.move_speed_penalty_pct > 0.0
    assert dorian.move_penalty_remaining_sec > 0.8

    vex = order_specialist_move(vex, 8, 5, between_waves=True)
    dyad = evaluate_dyadic_resonance_on_grid([dorian, vex])
    assert len(dyad["active_pairs"]) == 1
    assert dyad["catalyst_damage_bonus_pct"] == 18

    # 3. Verify deterministic Event-Seeded 16x10 Battlefield Generator
    m1 = generate_event_seeded_battlefield("EVT-SOL028-VAULT-SHEAR", 28, "enclave_15_dorian")
    m2 = generate_event_seeded_battlefield("EVT-SOL028-VAULT-SHEAR", 28, "enclave_15_dorian")
    assert m1["seed"] == m2["seed"]
    assert m1["cols"] == 16 and m1["rows"] == 10
    assert m1["scouting_gold_bonus"] == 75
    assert m1["buildable_tiles"] >= 60

    # 4. Verify 4-Stage Epoch Gate ("Beat the Level to Progress to the Next Style System")
    bridge = SovereignMarchEpochBridge(sol_number=28, active_pov_id="enclave_15_dorian")
    assert bridge.current_stage == "STAGE_1_LIVING_ATLAS"
    s2 = bridge.advance_to_corridor_gate("Cross-couple Geomancy with Cryo-Stasis on the northern causeway.")
    assert s2["stage"] == "STAGE_2_CORRIDOR_GATE"
    assert s2["scouting_gold_bonus"] == 75

    s3 = bridge.enter_tactical_defense("EVT-SOL028-VAULT-SHEAR")
    assert bridge.current_stage == "STAGE_3_TACTICAL_DEFENSE"
    assert s3["cols"] == 16

    # Breach before clearing 3 waves keeps Stage 4 locked and triggers Swain YES_BUT_RECOVERY
    breach_res = bridge.resolve_tactical_battle(
        waves_cleared=1,
        victory=False,
        mvp_unit=dorian,
        total_synergies=2,
        reposition_count=1,
    )
    assert breach_res["stage3_cleared"] is False
    assert breach_res["stage"] == "STAGE_3_TACTICAL_DEFENSE"
    assert breach_res["swain_sequel_state"] == "YES_BUT_RECOVERY"

    # Clearing required waves unlocks Stage 4 Colony & Feast and passes Stop-Slop >= 35/50
    win_res = bridge.resolve_tactical_battle(
        waves_cleared=6,
        victory=True,
        mvp_unit=dorian,
        total_synergies=5,
        reposition_count=3,
    )
    assert win_res["stage3_cleared"] is True
    assert win_res["stage"] == "STAGE_4_COLONY_FEAST"
    assert win_res["passed_stop_slop_gate"] is True
    assert win_res["stop_slop_score"] >= 35


if __name__ == "__main__":
    unittest.main(verbosity=2)
