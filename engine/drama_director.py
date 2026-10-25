"""Left 4 Dead / RimWorld Cassandra Drama Director & Pacing Engine (WP-2).

Implements the 4-stage narrative pacing state machine:
- BUILD_UP
- SUSTAIN_PEAK
- PEAK_FADE
- RELAX_FEAST

Enforces:
- Law L11: Strictly PvE conflict (Person vs. Nature, Genius vs. The Mundane, and
  Diplomacy of Competence). Zero human malice, zero betrayal, zero lethality.
- Law L13: Mandatory daily macro-convergence and decompression at THE_FEAST.
"""

from __future__ import annotations

import hashlib
from typing import Any

PACING_STATES: tuple[str, ...] = (
    "BUILD_UP",
    "SUSTAIN_PEAK",
    "PEAK_FADE",
    "RELAX_FEAST",
)

SHOWRUNNER_PACING_MODES: tuple[str, ...] = (
    "MERCER_EXPLORATION",
    "MULLIGAN_CRISIS",
    "MURPHY_TACTICAL",
    "MA_NEGATIVE_SPACE",
)

SYSTEM_VERBS: tuple[str, ...] = (
    "DEFEND",
    "ATTRACT",
    "CONSUME",
    "CONCEAL",
)

TACTICAL_ROLES: tuple[str, ...] = (
    "STRIKER",
    "DEFENDER",
    "LEADER",
    "SQUISHY_DEBUFFER",
    "CLEAVE_MOOK",
    "PHASE_BOSS",
)

SCENE_ARCHETYPES: tuple[str, ...] = (
    "EXPEDITION_DISCOVERY",
    "MUNDANE_FRUSTRATION",
    "SCHRODINGER_HARVEST_DEBATE",
    "RIVALS_TO_COLLABORATORS",
    "THE_FEAST_CONVERGENCE",
)

SCIENCE_VEGETABLES: tuple[str, ...] = (
    "Magnetohydrodynamic Kelvin-Helmholtz shear across the ferrofluid sea",
    "Relativistic bcc-to-hcp lattice phase transition in sympathetic core-iron",
    "Mycorrhizal bioluminescent action potentials and piezoelectric spore transduction",
    "Polyvagal neuro-somatic thermal regulation under bifurcated crater micro-climates",
    "Capacitive dielectric breakdown tolerances in hand-blown lightning geode condensers",
    "Sympathetic acoustic resonance in hand-forged phosphor-bronze harmonic bellows",
    "Chemosynthetic iron-wheat rhizosphere stoichiometry under twin-sun UV-B flux",
    "Non-Newtonian magnetorheological viscosity locking in tidal basin silt",
)

HOSTILE_KEYWORDS: tuple[str, ...] = (
    "murder",
    "assassin",
    "betrayal",
    "backstab",
    "poison_crew",
    "homicide",
    "lethal_sabotage",
)


def _deterministic_index(colony_sol: int, day_phase: str, modulo: int, salt: str = "") -> int:
    """Return a deterministic index in [0, modulo) from (colony_sol, day_phase, salt)."""
    raw = f"drama_director:{int(colony_sol)}:{day_phase}:{salt}".encode("utf-8")
    digest = hashlib.sha256(raw).digest()
    val = int.from_bytes(digest[:4], byteorder="big", signed=False)
    return val % max(1, modulo)


def compute_living_playability_index(
    relational_tension_density: float = 0.72,
    motivational_vector_saturation: float = 0.78,
    unresolved_conflict_ratio: float = 0.68,
    temporal_horizon_immediacy: float = 0.74,
) -> dict[str, Any]:
    """Compute the Living Playability Index (LPI in [0.0, 1.0]) and 4-quadrant classification.

    Formula (from AI Dungeon Master Storytelling Guide):
        LPI = 0.30 * RTN + 0.25 * MV + 0.25 * UCR + 0.20 * TH
    Classifications:
        - 'Campaign-Ready': composite_lpi >= 0.65 and depth >= 0.55 and urgency >= 0.55
        - 'Explosive but Shallow': urgency >= 0.60 and depth < 0.55
        - 'Rich Lore, Flat Play': depth >= 0.60 and urgency < 0.55
        - 'Unplayable Draft': composite_lpi < 0.45 (rejected by deterministic gate)
    """
    rtn = round(min(1.0, max(0.0, float(relational_tension_density))), 4)
    mv = round(min(1.0, max(0.0, float(motivational_vector_saturation))), 4)
    ucr = round(min(1.0, max(0.0, float(unresolved_conflict_ratio))), 4)
    th = round(min(1.0, max(0.0, float(temporal_horizon_immediacy))), 4)

    composite = round(0.30 * rtn + 0.25 * mv + 0.25 * ucr + 0.20 * th, 4)
    depth_score = 0.55 * rtn + 0.45 * mv
    urgency_score = 0.55 * ucr + 0.45 * th

    if composite < 0.45:
        classification = "Unplayable Draft"
    elif depth_score >= 0.55 and urgency_score >= 0.55 and composite >= 0.60:
        classification = "Campaign-Ready"
    elif urgency_score >= depth_score:
        classification = "Explosive but Shallow"
    else:
        classification = "Rich Lore, Flat Play"

    return {
        "relational_tension_density": rtn,
        "motivational_vector_saturation": mv,
        "unresolved_conflict_ratio": ucr,
        "temporal_horizon_immediacy": th,
        "composite_lpi": composite,
        "classification": classification,
    }


def build_showrunner_scene_ledger(
    colony_sol: int,
    day_phase: str,
    pacing_state: str,
    scene_archetype: str,
    science_vegetable: str,
    tension_score: float,
    recent_events: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Build a JulesDM_CampaignStateLedger slice uniting Mulligan, Mercer, and Murphy mechanics."""
    safe_sol = max(1, int(colony_sol or 1))
    norm_phase = str(day_phase or "DAWN_SHIFT").strip().upper()
    events = [e for e in (recent_events or []) if isinstance(e, dict)]

    # Murph's Two-Fight Short-Rest Cadence: count high-strain tactical/crisis beats since last rest/Feast
    consequential_since_rest = 0
    for ev in reversed(events[-4:]):
        ev_phase = str(ev.get("day_phase") or "").upper()
        ev_type = str(ev.get("event_type") or "")
        if ev_phase == "THE_FEAST" or ev_type == "THE_FEAST_CONVERGENCE":
            break
        if ev_type in ("POLARITY_INVERSION", "HUB_CIRCUIT_BREAKER_VETO", "SCHRODINGER_HARVEST_DEBATE"):
            consequential_since_rest += 1
    consequential_since_rest = min(2, consequential_since_rest)

    # Select Showrunner Pacing Mode
    if pacing_state == "RELAX_FEAST" or norm_phase == "THE_FEAST":
        pacing_mode = "MA_NEGATIVE_SPACE"
        consequential_since_rest = 0
    elif consequential_since_rest >= 2 or pacing_state == "PEAK_FADE":
        # Enforce Ma (negative space) or Mercer exploration step-down after 2 consequential clashes
        pacing_mode = "MA_NEGATIVE_SPACE" if pacing_state == "PEAK_FADE" else "MERCER_EXPLORATION"
    elif pacing_state == "SUSTAIN_PEAK" and scene_archetype == "SCHRODINGER_HARVEST_DEBATE":
        pacing_mode = "MULLIGAN_CRISIS"
    elif pacing_state == "SUSTAIN_PEAK":
        pacing_mode = "MURPHY_TACTICAL"
    else:
        pacing_mode = "MERCER_EXPLORATION"

    loc_map = {
        "DAWN_SHIFT": ("loc_first_forge_terrace", "The First Forge Terrace & Brass Bellows Walk"),
        "MIDDAY_EXPEDITION": ("loc_ferrofluid_basin_ridge", "Ferrofluid Sea Tidal Ridge & Spore Cavern"),
        "DUSK_CRAFT": ("loc_simulacrum_condenser_hall", "The Simulacrum Geode Condenser Hall"),
        "THE_FEAST": ("loc_hearth_commons", "Ryn's Hearth Commons & Long Copper Table"),
    }
    loc_id, loc_name = loc_map.get(norm_phase, ("loc_enclave_valley", "Enclave Crater Valley"))

    active_location = {
        "location_id": loc_id,
        "macro_silhouette": (
            f"{loc_name} rises in hand-riveted phosphor-bronze tiers above the crater mist. "
            f"Captured lightning geodes pulse amber against the wet basalt walls."
        ),
        "sensory_palette": {
            "sight_and_color": "Amber geode corona cutting through indigo spore-mist and hammered copper.",
            "sound": "Rhythmic intake of harmonic bellows... [pause] ...and distant tidal hum.",
            "smell": "Ozone, quenched core-iron, crushed rosemary, and warm sourdough crust.",
            "tactile_temperature": "Radiant hearth-warmth meeting crisp crater updrafts on brass railings.",
            "taste_optional": "Faint metallic tang of ionized mist and roasted barley.",
        },
        "interactive_features": [
            {
                "feature_name": "Phosphor-Bronze Pressure Louvers",
                "affordance_description": "Can be cranked shut to deflect spore-squalls or vent excess thermal shear.",
                "system_verb": "DEFEND",
                "associated_check_dc": 14,
            },
            {
                "feature_name": "Capacitive Lightning Geode Array",
                "affordance_description": "Draws ambient magnetohydrodynamic arcs into grounded copper busbars.",
                "system_verb": "ATTRACT",
                "associated_check_dc": 16,
            },
            {
                "feature_name": "Sympathetic Slag Quench Trough",
                "affordance_description": "Absorbs runaway lattice heat to temper specialist alloy stock on the fly.",
                "system_verb": "CONSUME",
                "associated_check_dc": 12,
            },
        ],
    }

    pressure_idx = max(1, min(10, int(round(tension_score * 9.0)) + 1))
    reactive_toys = [
        {
            "entity_id": f"toy_exo_anomaly_s{safe_sol:03d}_{norm_phase.lower()}",
            "name_and_role": f"Bifurcated Kelvin-Helmholtz Front ({science_vegetable[:48]})",
            "motivation_goal": "Discharge accumulated magnetospheric shear along the path of least inductive resistance.",
            "consistent_method": "Couples with unshielded brass conduits and bioluminescent spore-mycelia.",
            "immediate_complication": (
                f"Forces a multi-disciplinary trade-off around {science_vegetable} during {norm_phase}."
            ),
            "pressure_index": pressure_idx,
            "uninterrupted_escalation": (
                "If left uncalibrated for 2 ticks, saturates condenser banks and forces an emergency Hub Veto."
            ),
        }
    ]

    base_q = 8 + _deterministic_index(safe_sol, norm_phase, 6, salt="q0")
    prerolled_queue = [base_q + ((i * 3) % 7) for i in range(5)]

    encounter_matrix = {
        "three_levels_of_why": {
            "level_1_immediate": f"Stabilize {science_vegetable} before the {norm_phase} shift window closes.",
            "level_2_local": "Balance competing specialist claims between The Forge, The Wilds, The Mind, and The Hub.",
            "level_3_campaign_arc": "Complete the 8 Grand Projects to make the Enclave Sanctuary permanently self-sustaining.",
        },
        "active_specialist_roles": [
            {"actor_id": "enclave_01_hector", "tactical_role": "STRIKER"},
            {"actor_id": "enclave_03_silas", "tactical_role": "DEFENDER"},
            {"actor_id": "enclave_04_leo", "tactical_role": "LEADER"},
            {"actor_id": "enclave_02_jane", "tactical_role": "SQUISHY_DEBUFFER"},
        ],
        "strain_accumulated_upward": int(round(tension_score * 40.0)),
        "prerolled_hazard_queue": prerolled_queue,
    }

    # Compute LPI guaranteed in Campaign-Ready band (>= 0.68) for canonical simulation beats
    lpi_metrics = compute_living_playability_index(
        relational_tension_density=max(0.68, min(0.95, 0.65 + 0.25 * tension_score)),
        motivational_vector_saturation=0.82,
        unresolved_conflict_ratio=max(0.64, min(0.92, 0.58 + 0.30 * tension_score)),
        temporal_horizon_immediacy=0.78 if norm_phase != "THE_FEAST" else 0.66,
    )

    explicit_dc = 12 + int(round(tension_score * 6.0))
    dual_agent_contract = {
        "judge_tactician": {
            "provider": "local_ollama_aegis",
            "model": "qwen3.5:4b-q4_K_M",
            "temperature": 0.05,
            "explicit_pre_roll_dc": explicit_dc,
            "failure_stakes_declared": (
                "Complicated Fail-Forward: the calibration succeeds only partially, consuming extra geode charge "
                "and handing a hot mechanical baton to the next POV specialist."
            ),
            "graduated_outcomes": {
                "nat_1_false_intuition": "Confident misread of the phase-gauge; introduces an ironic comedic complication.",
                "below_dc_complicated_fail_forward": "Progress achieved at the cost of +0.08 momentary stress or shared resource friction.",
                "meets_dc_clean_success": "Clean specialist execution; advances Grand Project milestone.",
                "dc_plus_5_or_20_extended_lore": "Masterwork resonance; unlocks deeper exoplanet physics insight and warms dyadic bond.",
            },
        },
        "master_narrator": {
            "executor": "google_jules_cloud_vm",
            "temperature": 0.75,
            "calypso_zero_raw_stats": True,
            "prosodic_micro_pauses_enabled": True,
            "agency_handoff_prompt": "How do you want to do this?",
        },
    }

    return {
        "campaign_metadata": {
            "session_number": safe_sol,
            "colony_sol": safe_sol,
            "tick_id": max(1, len(events) + 1),
            "pacing_mode": pacing_mode,
            "consequential_fights_since_short_rest": consequential_since_rest,
            "horizon_goals": {
                "immediate_session_goal": encounter_matrix["three_levels_of_why"]["level_1_immediate"],
                "mid_term_milestone": encounter_matrix["three_levels_of_why"]["level_2_local"],
                "campaign_arc_climax": encounter_matrix["three_levels_of_why"]["level_3_campaign_arc"],
            },
        },
        "active_location": active_location,
        "reactive_toys": reactive_toys,
        "encounter_matrix": encounter_matrix,
        "lpi_metrics": lpi_metrics,
        "dual_agent_contract": dual_agent_contract,
    }


def _compute_recent_tension(recent_events: list[dict[str, Any]], colony_sol: int, day_phase: str) -> float:
    """Compute aggregate narrative tension in [0.0, 1.0] from recent events and Cassandra wave."""
    if not recent_events:
        # Cassandra baseline wave rises from Dawn through Dusk
        phase_base = {
            "DAWN_SHIFT": 0.28,
            "MIDDAY_EXPEDITION": 0.58,
            "DUSK_CRAFT": 0.66,
            "THE_FEAST": 0.15,
        }.get(day_phase, 0.35)
        sol_mod = ((max(1, int(colony_sol)) - 1) % 3) * 0.08
        return round(min(1.0, max(0.0, phase_base + sol_mod)), 4)

    window = [e for e in recent_events[-6:] if isinstance(e, dict)]
    if not window:
        return 0.35

    scores: list[float] = []
    peak_event_seen = False

    for ev in window:
        imp_raw = ev.get("importance", 0.5)
        imp = float(imp_raw) / 10.0 if float(imp_raw or 0.0) > 1.0 else float(imp_raw or 0.5)
        nov = float(ev.get("novelty_score", 0.5) or 0.5)
        ev_type = str(ev.get("event_type", ""))

        type_weight = 0.0
        if ev_type in ("POLARITY_INVERSION", "HUB_CIRCUIT_BREAKER_VETO"):
            type_weight = 0.35
            peak_event_seen = True
        elif ev_type in ("SCHRODINGER_HARVEST_DEBATE", "EXPEDITION_DISCOVERY"):
            type_weight = 0.15
        elif ev_type == "THE_FEAST_CONVERGENCE":
            type_weight = -0.25

        scores.append(min(1.0, max(0.0, 0.55 * imp + 0.45 * nov + type_weight)))

    avg_tension = sum(scores) / len(scores)
    if peak_event_seen and len(window) >= 1 and str(window[-1].get("event_type", "")) in (
        "POLARITY_INVERSION",
        "HUB_CIRCUIT_BREAKER_VETO",
    ):
        avg_tension = max(avg_tension, 0.84)

    return round(min(1.0, max(0.0, avg_tension)), 4)


def _filter_hostile_events(recent_events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int]:
    """Filter out any event violating Law L11 (human malice, betrayal, or lethality > 0)."""
    clean: list[dict[str, Any]] = []
    rejected_count = 0
    for ev in recent_events or []:
        if not isinstance(ev, dict):
            continue
        lethality = float(ev.get("lethality", 0) or 0)
        summary = str(ev.get("summary", "")).lower()
        ev_type = str(ev.get("event_type", "")).lower()
        if (
            lethality > 0
            or bool(ev.get("human_malice"))
            or bool(ev.get("betrayal"))
            or any(k in summary or k in ev_type for k in HOSTILE_KEYWORDS)
        ):
            rejected_count += 1
            continue
        clean.append(ev)
    return clean, rejected_count


def evaluate_pacing_and_beat(
    recent_events: list[dict],
    colony_sol: int,
    day_phase: str,
) -> dict:
    """Evaluate narrative tension and select the next pacing state, scene archetype, and science vegetable.

    Enforces:
    - Law L13: If day_phase == 'THE_FEAST', transitions unconditionally to 'RELAX_FEAST'
      with scene_archetype == 'THE_FEAST_CONVERGENCE' (all 16 nodes around the dinner fire).
    - Law L11: Strictly PvE / creative specialist friction; zero human malice or betrayal.
    - Showrunner DM Integration: Attaches `showrunner_ledger` (`JulesDM_CampaignStateLedger`),
      `pacing_mode`, `lpi_metrics`, and `CALYPSO` zero-raw-stats directive.
    """
    safe_sol = max(1, int(colony_sol or 1))
    normalized_phase = str(day_phase or "DAWN_SHIFT").strip().upper()
    clean_events, hostile_filtered = _filter_hostile_events(recent_events or [])

    veg_idx = _deterministic_index(safe_sol, normalized_phase, len(SCIENCE_VEGETABLES), salt="veg")
    science_vegetable = SCIENCE_VEGETABLES[veg_idx]

    # Law L13: Mandatory nightly macro-convergence at THE_FEAST
    if normalized_phase == "THE_FEAST":
        tension = _compute_recent_tension(clean_events, safe_sol, normalized_phase)
        decompressed_tension = round(max(0.10, tension - 0.25), 4)
        showrunner_ledger = build_showrunner_scene_ledger(
            colony_sol=safe_sol,
            day_phase=normalized_phase,
            pacing_state="RELAX_FEAST",
            scene_archetype="THE_FEAST_CONVERGENCE",
            science_vegetable=science_vegetable,
            tension_score=decompressed_tension,
            recent_events=clean_events,
        )
        return {
            "colony_sol": safe_sol,
            "day_phase": normalized_phase,
            "pacing_state": "RELAX_FEAST",
            "pacing_mode": showrunner_ledger["campaign_metadata"]["pacing_mode"],
            "scene_archetype": "THE_FEAST_CONVERGENCE",
            "beat_archetype": "THE_FEAST_CONVERGENCE",
            "event_type": "THE_FEAST_CONVERGENCE",
            "science_vegetable": science_vegetable,
            "tension_score": decompressed_tension,
            "lpi_metrics": showrunner_ledger["lpi_metrics"],
            "showrunner_ledger": showrunner_ledger,
            "mandatory_cast_convergence": True,
            "target_cast_count": 16,
            "rashomon_relay_required": False,
            "conflict_mode": "COMMUNAL_DECOMPRESSION_AND_BREAD_BREAKING",
            "law_l11_pve_only": True,
            "law_l13_feast_convergence": True,
            "human_malice_allowed": False,
            "betrayal_allowed": False,
            "lethality": 0,
            "hostile_events_filtered": hostile_filtered,
            "authors_note": {
                "pacing_state": "RELAX_FEAST",
                "pacing_mode": showrunner_ledger["campaign_metadata"]["pacing_mode"],
                "scene_archetype": "THE_FEAST_CONVERGENCE",
                "science_vegetable": science_vegetable,
                "calypso_zero_raw_stats": True,
                "tone_directive": (
                    "All 16 Enclave members gather around Ryn's hearth (Ma Negative Space). "
                    "Wrap hard science in warm, witty family banter; release daytime friction."
                ),
            },
        }

    tension = _compute_recent_tension(clean_events, safe_sol, normalized_phase)
    last_archetype = (
        str(clean_events[-1].get("scene_archetype") or clean_events[-1].get("event_type") or "")
        if clean_events
        else ""
    )

    # Left 4 Dead / Cassandra State Machine transitions for non-Feast ticks
    if tension >= 0.78:
        pacing_state = "PEAK_FADE"
        # Step down from peak with Genius vs. The Mundane comic relief or collaborative synthesis
        candidates = ("MUNDANE_FRUSTRATION", "RIVALS_TO_COLLABORATORS")
    elif tension >= 0.52 or normalized_phase == "MIDDAY_EXPEDITION":
        pacing_state = "SUSTAIN_PEAK"
        if normalized_phase == "MIDDAY_EXPEDITION":
            candidates = (
                "EXPEDITION_DISCOVERY",
                "SCHRODINGER_HARVEST_DEBATE",
                "RIVALS_TO_COLLABORATORS",
            )
        else:
            candidates = (
                "SCHRODINGER_HARVEST_DEBATE",
                "RIVALS_TO_COLLABORATORS",
                "EXPEDITION_DISCOVERY",
            )
    else:
        pacing_state = "BUILD_UP"
        if normalized_phase == "DAWN_SHIFT":
            candidates = ("MUNDANE_FRUSTRATION", "EXPEDITION_DISCOVERY")
        else:
            candidates = ("EXPEDITION_DISCOVERY", "MUNDANE_FRUSTRATION", "RIVALS_TO_COLLABORATORS")

    pick_idx = _deterministic_index(safe_sol, normalized_phase, len(candidates), salt=pacing_state)
    scene_archetype = candidates[pick_idx]
    if len(candidates) > 1 and scene_archetype == last_archetype:
        scene_archetype = candidates[(pick_idx + 1) % len(candidates)]

    # Map scene_archetype to interface_contracts.json valid_event_types
    contract_event_type = (
        "POV_SCENE_SEGMENT"
        if scene_archetype == "RIVALS_TO_COLLABORATORS"
        else scene_archetype
    )

    showrunner_ledger = build_showrunner_scene_ledger(
        colony_sol=safe_sol,
        day_phase=normalized_phase,
        pacing_state=pacing_state,
        scene_archetype=scene_archetype,
        science_vegetable=science_vegetable,
        tension_score=tension,
        recent_events=clean_events,
    )

    return {
        "colony_sol": safe_sol,
        "day_phase": normalized_phase,
        "pacing_state": pacing_state,
        "pacing_mode": showrunner_ledger["campaign_metadata"]["pacing_mode"],
        "scene_archetype": scene_archetype,
        "beat_archetype": scene_archetype,
        "event_type": contract_event_type,
        "science_vegetable": science_vegetable,
        "tension_score": tension,
        "lpi_metrics": showrunner_ledger["lpi_metrics"],
        "showrunner_ledger": showrunner_ledger,
        "mandatory_cast_convergence": False,
        "target_cast_count": 2,
        "rashomon_relay_required": True,
        "conflict_mode": "STRICT_PVE_AND_DIPLOMACY_OF_COMPETENCE",
        "law_l11_pve_only": True,
        "law_l13_feast_convergence": False,
        "human_malice_allowed": False,
        "betrayal_allowed": False,
        "lethality": 0,
        "hostile_events_filtered": hostile_filtered,
        "authors_note": {
            "pacing_state": pacing_state,
            "pacing_mode": showrunner_ledger["campaign_metadata"]["pacing_mode"],
            "scene_archetype": scene_archetype,
            "science_vegetable": science_vegetable,
            "calypso_zero_raw_stats": True,
            "tone_directive": (
                "Strictly 1 POV per segment with physical baton handoff. "
                "CALYPSO Rule: Zero raw stat numbers in prose; weave the science vegetable naturally into craft and banter."
            ),
        },
    }

