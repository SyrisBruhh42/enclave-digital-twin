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
        return {
            "colony_sol": safe_sol,
            "day_phase": normalized_phase,
            "pacing_state": "RELAX_FEAST",
            "scene_archetype": "THE_FEAST_CONVERGENCE",
            "beat_archetype": "THE_FEAST_CONVERGENCE",
            "event_type": "THE_FEAST_CONVERGENCE",
            "science_vegetable": science_vegetable,
            "tension_score": decompressed_tension,
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
                "scene_archetype": "THE_FEAST_CONVERGENCE",
                "science_vegetable": science_vegetable,
                "tone_directive": (
                    "All 16 Enclave members gather around Ryn's hearth. "
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

    return {
        "colony_sol": safe_sol,
        "day_phase": normalized_phase,
        "pacing_state": pacing_state,
        "scene_archetype": scene_archetype,
        "beat_archetype": scene_archetype,
        "event_type": contract_event_type,
        "science_vegetable": science_vegetable,
        "tension_score": tension,
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
            "scene_archetype": scene_archetype,
            "science_vegetable": science_vegetable,
            "tone_directive": (
                "Strictly 1 POV per segment with physical baton handoff. "
                "Zero human villains; weave the science vegetable naturally into craft and banter."
            ),
        },
    }
