"""Winnow & Felt Incremental Story Sifter & Salience Scorer (WP-4).

Implements Kreminski/Ryan Felt & Winnow-inspired declarative story-sifting patterns
over the append-only Enclave event log, plus Whole-Trait salience scoring.

Supported multi-event narrative patterns:
- RIVALRY_TO_BREAKTHROUGH: Intellectual clash followed by shared discovery.
- GENIUS_VS_MUNDANE_COMEDY: PhD breakthrough interrupted by manual maintenance.
- SCHRODINGER_HARVEST_STANDOFF: 3-squad resource claim resolved by compromise or Hub veto.
- MAGNETIC_CRISIS_RESCUE: High kp_exo hazard resolved by Anchor+Prodigy teamwork.
- SHADOW_GRID_MISATTRIBUTION: Matured 3-Feast prank blamed on the wrong genius.
- POLARITY_INVERSION_ANOMALY: Stress-gated cortical polarity inversion under geomagnetic storm.

Exports:
- score_event_salience(event: dict, actor_core: dict | None) -> float
- sift_events(events: list[dict], character_cores: dict[str, dict]) -> dict
"""

from __future__ import annotations

import hashlib
from typing import Any

SUPPORTED_PATTERNS: tuple[str, ...] = (
    "RIVALRY_TO_BREAKTHROUGH",
    "GENIUS_VS_MUNDANE_COMEDY",
    "SCHRODINGER_HARVEST_STANDOFF",
    "MAGNETIC_CRISIS_RESCUE",
    "SHADOW_GRID_MISATTRIBUTION",
    "POLARITY_INVERSION_ANOMALY",
)

BIG_FIVE_AXES: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

ALL_TRAIT_AXES: tuple[str, ...] = BIG_FIVE_AXES + ("hexaco_honesty_humility",)

# Canonical fallback dialectic roles for the 16 Enclave nodes when character_cores is partial
CANON_ROLES_BY_ID: dict[str, str] = {
    "enclave_01_hector": "Prodigy",
    "enclave_02_jane": "Prodigy",
    "enclave_03_silas": "Anchor",
    "enclave_04_leo": "Anchor",
    "enclave_05_kaio": "Prodigy",
    "enclave_06_zara": "Prodigy",
    "enclave_07_willow": "Anchor",
    "enclave_08_terra": "Anchor",
    "enclave_09_orion": "Prodigy",
    "enclave_10_isla": "Prodigy",
    "enclave_11_kenna": "Anchor",
    "enclave_12_elias": "Anchor",
    "enclave_13_ryn": "Prodigy",
    "enclave_14_vex": "Prodigy",
    "enclave_15_dorian": "Anchor",
    "enclave_16_elara": "Anchor",
}

CANON_NAMES_BY_ID: dict[str, str] = {
    "enclave_01_hector": "Hector",
    "enclave_02_jane": "Jane",
    "enclave_03_silas": "Silas",
    "enclave_04_leo": "Leo",
    "enclave_05_kaio": "Kaio",
    "enclave_06_zara": "Zara",
    "enclave_07_willow": "Willow",
    "enclave_08_terra": "Terra",
    "enclave_09_orion": "Orion",
    "enclave_10_isla": "Isla",
    "enclave_11_kenna": "Kenna",
    "enclave_12_elias": "Elias",
    "enclave_13_ryn": "Ryn",
    "enclave_14_vex": "Vex",
    "enclave_15_dorian": "Dorian",
    "enclave_16_elara": "Elara",
}


def _clip(val: float, low: float = 0.0, high: float = 1.0) -> float:
    return min(high, max(low, float(val)))


def _extract_trait_distribution(
    actor_core: dict[str, Any] | None, axis: str
) -> tuple[float, float] | None:
    """Return (mean, sd) for a given trait axis from actor_core if available."""
    if not isinstance(actor_core, dict):
        return None
    tier1 = actor_core.get("tier_1_causal_trait_distributions")
    if not isinstance(tier1, dict):
        tier1 = actor_core
    if axis == "hexaco_honesty_humility":
        hh = tier1.get("hexaco_honesty_humility") or actor_core.get("hexaco_honesty_humility")
        if isinstance(hh, dict) and "mean" in hh:
            return float(hh.get("mean", 0.75)), max(0.02, float(hh.get("sd", 0.06)))
        return None
    b5 = tier1.get("big_five_distributions") or actor_core.get("big_five_distributions") or tier1
    if isinstance(b5, dict):
        spec = b5.get(axis)
        if isinstance(spec, dict) and "mean" in spec:
            return float(spec.get("mean", 0.50)), max(0.02, float(spec.get("sd", 0.08)))
    return None


def _compute_trait_deviation_novelty(
    event: dict[str, Any], actor_core: dict[str, Any] | None
) -> float:
    """Compute normalized trait-state deviation novelty in [0.0, 1.0].

    Evaluates observed momentary states or state_deltas in `event` against
    `actor_core["tier_1_causal_trait_distributions"]`, combined with event
    `novelty_score` and stress/inversion shifts.
    """
    base_novelty = _clip(float(event.get("novelty_score", 0.0) or 0.0), 0.0, 1.0)

    state_deltas = event.get("state_deltas")
    if not isinstance(state_deltas, dict):
        state_deltas = {}

    trait_states = (
        event.get("trait_states")
        or event.get("sampled_traits")
        or event.get("momentary_state")
        or state_deltas.get("trait_states")
    )
    if not isinstance(trait_states, dict):
        trait_states = {}

    z_values: list[float] = []
    raw_shifts: list[float] = []

    for axis in ALL_TRAIT_AXES:
        dist = _extract_trait_distribution(actor_core, axis)

        # 1. Explicit momentary state value in trait_states or top-level event
        state_val: float | None = None
        for key in (axis, f"{axis}_state"):
            if key in trait_states and isinstance(trait_states[key], (int, float)):
                state_val = float(trait_states[key])
                break
            if key in event and isinstance(event[key], (int, float)):
                state_val = float(event[key])
                break

        if state_val is not None:
            if dist is not None:
                mu, sd = dist
                z_values.append(abs(state_val - mu) / sd)
            else:
                raw_shifts.append(abs(state_val - 0.50) * 2.0)

        # 2. Entry in state_deltas
        for delta_key in (f"{axis}_delta", f"{axis}_state", axis):
            if delta_key in state_deltas and isinstance(state_deltas[delta_key], (int, float)):
                val = float(state_deltas[delta_key])
                if dist is not None:
                    mu, sd = dist
                    if delta_key.endswith("_delta") or val < 0.0:
                        # Signed shift delta: normalize by sd and amplify if counter-dispositional
                        counter_disp = 1.0 + 0.5 * abs(mu - 0.50)
                        z_values.append((abs(val) * counter_disp) / sd)
                    else:
                        # Could be either a sampled state in [0, 1] or a positive delta
                        # If val is far from mu or > 0.30, measure state deviation from mu;
                        # also respect raw delta / sd so neither convention is under-scored.
                        state_z = abs(val - mu) / sd
                        delta_z = abs(val) / sd
                        z_values.append(state_z if abs(val) > 0.30 else max(state_z * 0.5, delta_z))
                else:
                    raw_shifts.append(min(1.0, abs(val) / 0.30))
                break

    # Check non-trait state deltas (e.g. stress_delta, fatigue_delta)
    for k, v in state_deltas.items():
        if isinstance(v, (int, float)) and not any(k.startswith(ax) for ax in ALL_TRAIT_AXES):
            raw_shifts.append(min(1.0, abs(float(v)) / 0.35))

    ev_type = str(event.get("event_type", "")).upper()
    if (
        ev_type == "POLARITY_INVERSION"
        or bool(event.get("polarity_inversion_active"))
        or bool(state_deltas.get("polarity_inversion_active"))
    ):
        if isinstance(actor_core, dict):
            # Polarity inversion flips dominant traits against Tier-1 baseline
            z_values.append(3.8)
        else:
            raw_shifts.append(0.95)

    if z_values:
        max_z = max(z_values)
        mean_z = sum(z_values) / len(z_values)
        # Map z-deviation to [0.0, 1.0], where z >= 3.5 saturates novelty
        z_norm = _clip((0.65 * max_z + 0.35 * mean_z) / 3.5, 0.0, 1.0)
        return _clip(0.35 * base_novelty + 0.65 * z_norm, 0.0, 1.0)

    if raw_shifts:
        shift_norm = _clip(max(raw_shifts), 0.0, 1.0)
        return _clip(0.55 * base_novelty + 0.45 * shift_norm, 0.0, 1.0)

    return base_novelty


def _extract_relationship_delta_magnitude(rel_deltas: Any) -> float:
    """Sum absolute numeric relationship delta values from dict or list representations."""
    if not rel_deltas:
        return 0.0

    total = 0.0
    if isinstance(rel_deltas, dict):
        for k, v in rel_deltas.items():
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                total += abs(float(v))
            elif isinstance(v, dict):
                for sub_k, sub_v in v.items():
                    if isinstance(sub_v, (int, float)) and not isinstance(sub_v, bool):
                        total += abs(float(sub_v))
            elif isinstance(v, list):
                total += _extract_relationship_delta_magnitude(v)
    elif isinstance(rel_deltas, (list, tuple)):
        for item in rel_deltas:
            if isinstance(item, (int, float)) and not isinstance(item, bool):
                total += abs(float(item))
            elif isinstance(item, dict):
                for k, v in item.items():
                    if (
                        isinstance(v, (int, float))
                        and not isinstance(v, bool)
                        and k not in ("tick_id", "colony_sol", "origin_sol", "maturity_sol")
                    ):
                        total += abs(float(v))
    return total


def score_event_salience(event: dict, actor_core: dict | None = None) -> float:
    """Compute composite narrative salience in [0.0, 100.0].

    Combines:
    1. Event `importance` (1-10 scale) -> up to 35.0 points
    2. Trait-state deviation novelty against `actor_core["tier_1_causal_trait_distributions"]`
       and `novelty_score` -> up to 30.0 points
    3. Magnitude of `relationship_deltas` -> up to 20.0 points
    4. Number of `actors` involved -> up to 15.0 points
    """
    if not isinstance(event, dict) or not event:
        return 0.0

    # 1. Importance (0..35 pts)
    raw_imp = event.get("importance", 0.0)
    try:
        imp_val = float(raw_imp or 0.0)
    except (TypeError, ValueError):
        imp_val = 0.0
    imp_norm = _clip(imp_val / 10.0, 0.0, 1.0)
    imp_points = 35.0 * imp_norm

    # 2. Trait-state deviation novelty (0..30 pts)
    trait_nov_norm = _compute_trait_deviation_novelty(event, actor_core)
    trait_points = 30.0 * trait_nov_norm

    # 3. Relationship delta magnitude (0..20 pts)
    rel_mag = _extract_relationship_delta_magnitude(event.get("relationship_deltas"))
    rel_norm = _clip(rel_mag / 0.45, 0.0, 1.0)
    rel_points = 20.0 * rel_norm

    # 4. Actors count (0..15 pts)
    actors = event.get("actors")
    if isinstance(actors, (list, tuple, set)):
        actor_count = len([a for a in actors if a])
    else:
        actor_count = 0

    if actor_count <= 0:
        actor_points = 0.0
    elif actor_count == 1:
        actor_points = 4.0
    elif actor_count == 2:
        actor_points = 8.5
    elif actor_count == 3:
        actor_points = 11.5
    else:
        actor_points = min(15.0, 11.5 + 3.5 * ((min(actor_count, 16) - 3) / 13.0))

    total = imp_points + trait_points + rel_points + actor_points
    return round(_clip(total, 0.0, 100.0), 4)


def _resolve_actor_role(actor_id: str, character_cores: dict[str, dict[str, Any]]) -> str:
    """Resolve whether an actor is an 'Anchor' or 'Prodigy'."""
    core = (character_cores or {}).get(actor_id)
    if isinstance(core, dict):
        ident = core.get("agent_identity")
        if isinstance(ident, dict) and ident.get("dialectic_role"):
            return str(ident["dialectic_role"])
        if core.get("dialectic_role"):
            return str(core["dialectic_role"])
        if core.get("role"):
            return str(core["role"])
    return CANON_ROLES_BY_ID.get(actor_id, "Specialist")


def _resolve_actor_name(actor_id: str, character_cores: dict[str, dict[str, Any]]) -> str:
    """Resolve display name for an actor ID."""
    core = (character_cores or {}).get(actor_id)
    if isinstance(core, dict):
        ident = core.get("agent_identity")
        if isinstance(ident, dict) and ident.get("name"):
            return str(ident["name"])
        if core.get("name"):
            return str(core["name"])
    return CANON_NAMES_BY_ID.get(actor_id, actor_id)


def _extract_event_kp_exo(event: dict[str, Any]) -> float:
    """Extract kp_exo associated with an event if present."""
    for key in ("kp_exo", "magnetic_polarity_shear_kp_exo"):
        if key in event and isinstance(event[key], (int, float)):
            return float(event[key])
    for sub_key in ("magnetosphere", "weather", "state_deltas", "chronosphere"):
        sub = event.get(sub_key)
        if isinstance(sub, dict):
            for k in ("kp_exo", "magnetic_polarity_shear_kp_exo"):
                if k in sub and isinstance(sub[k], (int, float)):
                    return float(sub[k])
    summary = str(event.get("summary", "")).lower()
    if "kp_exo" in summary or "kp 7" in summary or "kp 8" in summary or "kp-7" in summary or "supercharge" in summary:
        return 7.4
    if "magnetic" in summary or "ferrofluid" in summary or "flux" in summary or "geode" in summary:
        return 6.6
    return 4.5


def _merge_events_metadata(
    chain_events: list[dict[str, Any]],
    scored_by_id: dict[str, float],
) -> dict[str, Any]:
    """Aggregate cited_event_ids, union of actors, location, day_phases, science_vegetable, and salience."""
    cited_ids: list[str] = []
    actors_union: list[str] = []
    locations: list[str] = []
    day_phases: list[str] = []
    science_veg = ""

    for ev in chain_events:
        eid = str(ev.get("event_id", "")).strip()
        if eid and eid not in cited_ids:
            cited_ids.append(eid)
        for act in ev.get("actors") or []:
            act_s = str(act).strip()
            if act_s and act_s not in actors_union:
                actors_union.append(act_s)
        loc = str(ev.get("location", "")).strip()
        if loc and loc not in locations:
            locations.append(loc)
        phase = str(ev.get("day_phase", "")).strip()
        if phase and phase not in day_phases:
            day_phases.append(phase)
        veg = str(ev.get("science_vegetable", "")).strip()
        if veg and not science_veg:
            science_veg = veg

    if not science_veg:
        science_veg = "Magnetohydrodynamic flux calibration and sympathetic metallurgy"

    base_scores = [scored_by_id.get(eid, 50.0) for eid in cited_ids]
    max_s = max(base_scores) if base_scores else 50.0
    chain_bonus = min(12.0, 4.5 * max(0, len(cited_ids) - 1))
    salience = round(_clip(max_s + chain_bonus, 0.0, 100.0), 4)

    primary_location = locations[0] if locations else "Enclave_Crater_Valley"

    return {
        "cited_event_ids": cited_ids,
        "event_ids": list(cited_ids),
        "actors": actors_union,
        "location": primary_location,
        "locations": locations,
        "day_phases": day_phases,
        "science_vegetable": science_veg,
        "salience_score": salience,
        "salience": salience,
    }


def _build_chain_record(
    pattern_type: str,
    title: str,
    narrative_summary: str,
    chain_events: list[dict[str, Any]],
    scored_by_id: dict[str, float],
    status: str = "COMPLETED",
    missing_payoff_step: str = "",
) -> dict[str, Any]:
    meta = _merge_events_metadata(chain_events, scored_by_id)
    raw_hash = hashlib.sha256(
        f"{pattern_type}:{status}:{','.join(meta['cited_event_ids'])}".encode("utf-8")
    ).hexdigest()[:10]
    story_id = f"story_{pattern_type.lower()}_{raw_hash}"

    record: dict[str, Any] = {
        "story_id": story_id,
        "pattern_id": pattern_type,
        "pattern_type": pattern_type,
        "pattern": pattern_type,
        "status": status,
        "story_title": title,
        "title": title,
        "narrative_summary": narrative_summary,
        "summary": narrative_summary,
        **meta,
    }
    if missing_payoff_step:
        record["missing_payoff_step"] = missing_payoff_step
        record["foreshadowing_hook"] = narrative_summary
    return record


def _is_clash_or_friction_event(ev: dict[str, Any]) -> bool:
    ev_type = str(ev.get("event_type", "")).upper()
    archetype = str(ev.get("scene_archetype", "")).upper()
    summary = str(ev.get("summary", "")).lower()
    if archetype == "RIVALS_TO_COLLABORATORS":
        return True
    if ev_type in ("SCHRODINGER_HARVEST_DEBATE", "MUNDANE_FRUSTRATION"):
        return True
    clash_words = (
        "clash",
        "rivalry",
        "debate",
        "disagree",
        "friction",
        "argument",
        "inefficient",
        "skeptic",
        "dispute",
        "reject",
        "standoff",
        "tension",
        "challenge",
    )
    if any(w in summary for w in clash_words):
        return True
    rel = ev.get("relationship_deltas")
    if isinstance(rel, dict):
        for v in rel.values():
            if isinstance(v, (int, float)) and float(v) < 0:
                return True
            if isinstance(v, dict) and any(
                isinstance(sv, (int, float)) and float(sv) < 0 for sv in v.values()
            ):
                return True
    return False


def _is_breakthrough_or_discovery_event(ev: dict[str, Any]) -> bool:
    ev_type = str(ev.get("event_type", "")).upper()
    archetype = str(ev.get("scene_archetype", "")).upper()
    summary = str(ev.get("summary", "")).lower()
    if ev_type == "EXPEDITION_DISCOVERY" or archetype == "RIVALS_TO_COLLABORATORS":
        return True
    breakthrough_words = (
        "breakthrough",
        "discover",
        "synthesi",
        "solved",
        "calibrat",
        "resonance",
        "collaborat",
        "eureka",
        "success",
        "stabiliz",
        "aligned",
        "harmonic",
    )
    return any(w in summary for w in breakthrough_words)


def _is_mundane_maintenance_event(ev: dict[str, Any]) -> bool:
    ev_type = str(ev.get("event_type", "")).upper()
    archetype = str(ev.get("scene_archetype", "")).upper()
    summary = str(ev.get("summary", "")).lower()
    if ev_type == "MUNDANE_FRUSTRATION" or archetype == "MUNDANE_FRUSTRATION":
        return True
    mundane_words = (
        "mundane",
        "chisel",
        "fungus",
        "bellows",
        "hinge",
        "wrench",
        "spanner",
        "scrub",
        "polish",
        "latch-key",
        "stuck",
        "clogged",
        "grease",
        "boiler",
        "gasket",
        "maintenance",
        "manual",
    )
    return any(w in summary for w in mundane_words)


def _is_high_science_setup_event(ev: dict[str, Any]) -> bool:
    ev_type = str(ev.get("event_type", "")).upper()
    summary = str(ev.get("summary", "")).lower()
    sci_veg = str(ev.get("science_vegetable", "")).strip()
    if ev_type in ("EXPEDITION_DISCOVERY", "MORNING_INTENT", "POV_SCENE_SEGMENT") and sci_veg:
        return True
    sci_words = (
        "phd",
        "relativistic",
        "magnetohydrodynamic",
        "lattice",
        "quantum",
        "mycorrhizal",
        "piezoelectric",
        "stoichiometry",
        "astrolabe",
        "calculus",
        "eigenvalue",
        "condenser",
        "theorem",
    )
    return any(w in summary for w in sci_words)


def _is_harvest_claim_event(ev: dict[str, Any]) -> bool:
    ev_type = str(ev.get("event_type", "")).upper()
    summary = str(ev.get("summary", "")).lower()
    if ev_type == "SCHRODINGER_HARVEST_DEBATE":
        return True
    harvest_words = (
        "schrodinger",
        "iron-wheat",
        "harvest",
        "three-squad",
        "3-squad",
        "competing claim",
        "resource debate",
        "seed stock",
        "flux-core shielding",
    )
    return any(w in summary for w in harvest_words)


def _is_harvest_resolution_event(ev: dict[str, Any]) -> bool:
    ev_type = str(ev.get("event_type", "")).upper()
    summary = str(ev.get("summary", "")).lower()
    if ev_type == "HUB_CIRCUIT_BREAKER_VETO":
        return True
    res_words = (
        "circuit-breaker",
        "circuit breaker",
        "veto",
        "compromise",
        "allocation",
        "partitioned",
        "settled",
        "ration",
        "consensus",
    )
    if any(w in summary for w in res_words):
        return True
    if ev_type == "THE_FEAST_CONVERGENCE" and (
        "wheat" in summary or "harvest" in summary or "compromise" in summary or "veto" in summary or "loaves" in summary
    ):
        return True
    return False


def _is_magnetic_crisis_event(ev: dict[str, Any]) -> bool:
    ev_type = str(ev.get("event_type", "")).upper()
    summary = str(ev.get("summary", "")).lower()
    kp = _extract_event_kp_exo(ev)
    if kp >= 6.0:
        return True
    if ev_type in ("POLARITY_INVERSION", "EXPEDITION_DISCOVERY") and (
        "storm" in summary or "flux" in summary or "magnetic" in summary or "squall" in summary
    ):
        return True
    crisis_words = (
        "kp_exo",
        "geomagnetic",
        "ferrofluid squall",
        "flux spike",
        "supercharge",
        "containment",
        "arc",
        "shear",
        "riptide",
    )
    return any(w in summary for w in crisis_words)


def _has_anchor_prodigy_teamwork(
    chain_events: list[dict[str, Any]], character_cores: dict[str, dict[str, Any]]
) -> bool:
    roles: set[str] = set()
    for ev in chain_events:
        for actor_id in ev.get("actors") or []:
            role = _resolve_actor_role(str(actor_id), character_cores)
            roles.add(role)
        summary = str(ev.get("summary", "")).lower()
        if "anchor" in summary and "prodigy" in summary:
            return True
    return "Anchor" in roles and "Prodigy" in roles


def sift_events(
    events: list[dict],
    character_cores: dict[str, dict],
) -> dict:
    """Sift the append-only event log into completed story chains and developing setups.

    Implements Kreminski/Ryan Felt & Winnow incremental pattern matching across:
    1. RIVALRY_TO_BREAKTHROUGH
    2. GENIUS_VS_MUNDANE_COMEDY
    3. SCHRODINGER_HARVEST_STANDOFF
    4. MAGNETIC_CRISIS_RESCUE
    5. SHADOW_GRID_MISATTRIBUTION
    6. POLARITY_INVERSION_ANOMALY
    """
    safe_cores = character_cores if isinstance(character_cores, dict) else {}
    valid_events: list[dict[str, Any]] = [
        ev for ev in (events or []) if isinstance(ev, dict) and ev.get("event_id")
    ]

    scored_events: list[dict[str, Any]] = []
    scored_by_id: dict[str, float] = {}

    for ev in valid_events:
        eid = str(ev["event_id"])
        actors = ev.get("actors") or []
        primary_actor = str(actors[0]) if actors else ""
        actor_core = safe_cores.get(primary_actor)
        salience = score_event_salience(ev, actor_core)
        scored_by_id[eid] = salience
        ev_copy = dict(ev)
        ev_copy["salience_score"] = salience
        scored_events.append(ev_copy)

    scored_events_sorted = sorted(
        scored_events,
        key=lambda e: (-float(e.get("salience_score", 0.0)), str(e.get("event_id", ""))),
    )

    completed_chains: list[dict[str, Any]] = []
    developing_stories: list[dict[str, Any]] = []

    # -------------------------------------------------------------------------
    # Pattern 1: RIVALRY_TO_BREAKTHROUGH
    # (Intellectual clash followed by shared discovery)
    # -------------------------------------------------------------------------
    clash_events = [ev for ev in valid_events if _is_clash_or_friction_event(ev)]
    discovery_events = [ev for ev in valid_events if _is_breakthrough_or_discovery_event(ev)]

    rivalry_matched = False
    for i, c_ev in enumerate(clash_events):
        c_actors = set(c_ev.get("actors") or [])
        c_idx = valid_events.index(c_ev)
        # Look for a later discovery event sharing at least 1 actor (or any later discovery)
        partner_disc: dict[str, Any] | None = None
        for d_ev in discovery_events:
            if d_ev["event_id"] == c_ev["event_id"]:
                continue
            d_idx = valid_events.index(d_ev)
            d_actors = set(d_ev.get("actors") or [])
            if d_idx > c_idx and (c_actors & d_actors):
                partner_disc = d_ev
                break
        if partner_disc is None:
            for d_ev in discovery_events:
                if d_ev["event_id"] != c_ev["event_id"] and valid_events.index(d_ev) > c_idx:
                    partner_disc = d_ev
                    break

        if partner_disc is not None:
            chain_evs = [c_ev, partner_disc]
            actor_names = [
                _resolve_actor_name(a, safe_cores)
                for a in _merge_events_metadata(chain_evs, scored_by_id)["actors"][:3]
            ]
            names_str = " & ".join(actor_names) if actor_names else "Enclave Specialists"
            completed_chains.append(
                _build_chain_record(
                    pattern_type="RIVALRY_TO_BREAKTHROUGH",
                    title=f"Friction to Breakthrough: {names_str}",
                    narrative_summary=(
                        f"What began as a sharp methodological clash ({c_ev.get('summary', '')}) "
                        f"crystallized into a shared empirical breakthrough ({partner_disc.get('summary', '')})."
                    ),
                    chain_events=chain_evs,
                    scored_by_id=scored_by_id,
                    status="COMPLETED",
                )
            )
            rivalry_matched = True
            break

    if not rivalry_matched and clash_events:
        c_ev = clash_events[0]
        actor_names = [_resolve_actor_name(a, safe_cores) for a in (c_ev.get("actors") or [])[:2]]
        names_str = " & ".join(actor_names) if actor_names else "Enclave Specialists"
        developing_stories.append(
            _build_chain_record(
                pattern_type="RIVALRY_TO_BREAKTHROUGH",
                title=f"Unresolved Methodological Clash: {names_str}",
                narrative_summary=(
                    f"Open specialist friction logged in {c_ev.get('location', 'the workshop')} "
                    f"({c_ev.get('summary', '')}); awaiting collaborative empirical synthesis."
                ),
                chain_events=[c_ev],
                scored_by_id=scored_by_id,
                status="DEVELOPING",
                missing_payoff_step="Shared empirical discovery or collaborative prototype calibration.",
            )
        )

    # -------------------------------------------------------------------------
    # Pattern 2: GENIUS_VS_MUNDANE_COMEDY
    # (PhD breakthrough interrupted by manual maintenance)
    # -------------------------------------------------------------------------
    mundane_events = [ev for ev in valid_events if _is_mundane_maintenance_event(ev)]
    sci_setup_events = [ev for ev in valid_events if _is_high_science_setup_event(ev)]

    mundane_matched = False
    if mundane_events:
        m_ev = mundane_events[0]
        m_actors = set(m_ev.get("actors") or [])
        paired_sci: dict[str, Any] | None = None
        for s_ev in sci_setup_events:
            if s_ev["event_id"] != m_ev["event_id"] and (set(s_ev.get("actors") or []) & m_actors):
                paired_sci = s_ev
                break
        if paired_sci is None:
            for s_ev in sci_setup_events:
                if s_ev["event_id"] != m_ev["event_id"]:
                    paired_sci = s_ev
                    break

        chain_evs = [paired_sci, m_ev] if paired_sci is not None else [m_ev]
        actor_names = [
            _resolve_actor_name(a, safe_cores)
            for a in _merge_events_metadata(chain_evs, scored_by_id)["actors"][:2]
        ]
        names_str = " & ".join(actor_names) if actor_names else "Enclave Prodigy"
        completed_chains.append(
            _build_chain_record(
                pattern_type="GENIUS_VS_MUNDANE_COMEDY",
                title=f"Genius vs. The Mundane: {names_str} and the Stubborn Hardware",
                narrative_summary=(
                    f"High-concept exoplanetary theory ({m_ev.get('science_vegetable', 'relativistic physics')}) "
                    f"collided headfirst with physical workshop maintenance: {m_ev.get('summary', '')}"
                ),
                chain_events=chain_evs,
                scored_by_id=scored_by_id,
                status="COMPLETED",
            )
        )
        mundane_matched = True
    elif sci_setup_events:
        s_ev = sci_setup_events[0]
        developing_stories.append(
            _build_chain_record(
                pattern_type="GENIUS_VS_MUNDANE_COMEDY",
                title="High-Theory Calibration Awaiting Physical Bench Test",
                narrative_summary=(
                    f"Theoretical calculation on '{s_ev.get('science_vegetable', 'exoplanet physics')}' "
                    f"is underway ({s_ev.get('summary', '')}), pending manual brass-and-copper assembly."
                ),
                chain_events=[s_ev],
                scored_by_id=scored_by_id,
                status="DEVELOPING",
                missing_payoff_step="Manual workshop maintenance or physical hardware bottleneck.",
            )
        )

    # -------------------------------------------------------------------------
    # Pattern 3: SCHRODINGER_HARVEST_STANDOFF
    # (3-squad resource claim resolved by compromise or Hub veto)
    # -------------------------------------------------------------------------
    harvest_claims = [ev for ev in valid_events if _is_harvest_claim_event(ev)]
    harvest_resolutions = [
        ev
        for ev in valid_events
        if _is_harvest_resolution_event(ev)
        and (not harvest_claims or ev["event_id"] != harvest_claims[0]["event_id"])
    ]

    if harvest_claims and harvest_resolutions:
        c_ev = harvest_claims[0]
        r_ev = harvest_resolutions[0]
        chain_evs = [c_ev, r_ev]
        completed_chains.append(
            _build_chain_record(
                pattern_type="SCHRODINGER_HARVEST_STANDOFF",
                title="The Schrodinger Harvest Accord: Three Squads, One Batch",
                narrative_summary=(
                    f"A three-way specialist resource standoff ({c_ev.get('summary', '')}) "
                    f"was resolved via Diplomacy of Competence and Hub adjudication ({r_ev.get('summary', '')})."
                ),
                chain_events=chain_evs,
                scored_by_id=scored_by_id,
                status="COMPLETED",
            )
        )
    elif harvest_claims:
        c_ev = harvest_claims[0]
        developing_stories.append(
            _build_chain_record(
                pattern_type="SCHRODINGER_HARVEST_STANDOFF",
                title="Developing Standoff: Competing Specialist Claims on the Harvest",
                narrative_summary=(
                    f"The Wilds, The Forge, and The Hub have staked competing domain claims "
                    f"({c_ev.get('summary', '')}); The Hub's circuit-breaker veto remains armed."
                ),
                chain_events=[c_ev],
                scored_by_id=scored_by_id,
                status="DEVELOPING",
                missing_payoff_step="Multi-squad compromise or Hub circuit-breaker veto resolution.",
            )
        )

    # -------------------------------------------------------------------------
    # Pattern 4: MAGNETIC_CRISIS_RESCUE
    # (High kp_exo hazard resolved by Anchor+Prodigy teamwork)
    # -------------------------------------------------------------------------
    crisis_events = [ev for ev in valid_events if _is_magnetic_crisis_event(ev)]
    if crisis_events:
        primary_crisis = crisis_events[0]
        crisis_idx = valid_events.index(primary_crisis)
        rescue_candidates = [primary_crisis]
        for ev in valid_events[crisis_idx + 1 :]:
            if _is_breakthrough_or_discovery_event(ev) or _has_anchor_prodigy_teamwork(
                [primary_crisis, ev], safe_cores
            ):
                rescue_candidates.append(ev)
                break

        if _has_anchor_prodigy_teamwork(rescue_candidates, safe_cores):
            actor_names = [
                _resolve_actor_name(a, safe_cores)
                for a in _merge_events_metadata(rescue_candidates, scored_by_id)["actors"][:3]
            ]
            names_str = " & ".join(actor_names) if actor_names else "Anchor & Prodigy"
            kp_val = _extract_event_kp_exo(primary_crisis)
            completed_chains.append(
                _build_chain_record(
                    pattern_type="MAGNETIC_CRISIS_RESCUE",
                    title=f"Magnetospheric Shear Contained: {names_str} Hold the Line",
                    narrative_summary=(
                        f"Under elevated geomagnetic shear (Kp_exo={kp_val:.1f}), Anchor-and-Prodigy "
                        f"teamwork stabilized the hazard ({primary_crisis.get('summary', '')})."
                    ),
                    chain_events=rescue_candidates,
                    scored_by_id=scored_by_id,
                    status="COMPLETED",
                )
            )
        else:
            kp_val = _extract_event_kp_exo(primary_crisis)
            developing_stories.append(
                _build_chain_record(
                    pattern_type="MAGNETIC_CRISIS_RESCUE",
                    title=f"Rising Geomagnetic Shear Watch (Kp_exo={kp_val:.1f})",
                    narrative_summary=(
                        f"Magnetospheric flux hazard detected at {primary_crisis.get('location', 'the ridge')} "
                        f"({primary_crisis.get('summary', '')}); Anchor-Prodigy containment team on standby."
                    ),
                    chain_events=[primary_crisis],
                    scored_by_id=scored_by_id,
                    status="DEVELOPING",
                    missing_payoff_step="Coordinated Anchor + Prodigy hazard containment.",
                )
            )

    # -------------------------------------------------------------------------
    # Pattern 5: SHADOW_GRID_MISATTRIBUTION
    # (Matured 3-Feast prank blamed on the wrong genius)
    # -------------------------------------------------------------------------
    seeded_pranks = [
        ev
        for ev in valid_events
        if str(ev.get("event_type", "")).upper() == "SHADOW_ECONOMY_PRANK_SEEDED"
    ]
    matured_pranks = [
        ev
        for ev in valid_events
        if str(ev.get("event_type", "")).upper() == "SHADOW_ECONOMY_PRANK_MATURED"
        or "blind spot" in str(ev.get("summary", "")).lower()
        or "misattribution" in str(ev.get("summary", "")).lower()
    ]

    if matured_pranks:
        m_prank = matured_pranks[0]
        chain_evs = [ seeded_pranks[0], m_prank ] if seeded_pranks else [m_prank]
        completed_chains.append(
            _build_chain_record(
                pattern_type="SHADOW_GRID_MISATTRIBUTION",
                title="Main Character Blind Spot: The Three-Feast Boomerang",
                narrative_summary=(
                    f"A delayed Sibling Grid caper matured after three Feasts with classic "
                    f"asymmetric attribution: {m_prank.get('summary', '')}"
                ),
                chain_events=chain_evs,
                scored_by_id=scored_by_id,
                status="COMPLETED",
            )
        )

    for s_prank in seeded_pranks:
        developing_stories.append(
            _build_chain_record(
                pattern_type="SHADOW_GRID_MISATTRIBUTION",
                title="Dormant Caper on the Sibling Grid (3-Feast Fuse Lit)",
                narrative_summary=(
                    f"A non-lethal workshop prank has been quietly rigged ({s_prank.get('summary', '')}); "
                    f"scheduled to mature after the 3-Feast delay."
                ),
                chain_events=[s_prank],
                scored_by_id=scored_by_id,
                status="DEVELOPING",
                missing_payoff_step="3-Feast maturity and Main Character Blind Spot collateral payoff.",
            )
        )

    # -------------------------------------------------------------------------
    # Pattern 6: POLARITY_INVERSION_ANOMALY
    # (Stress-gated cortical polarity inversion under high geomagnetic flux)
    # -------------------------------------------------------------------------
    inversion_events = [
        ev
        for ev in valid_events
        if str(ev.get("event_type", "")).upper() == "POLARITY_INVERSION"
        or bool(ev.get("polarity_inversion_active"))
        or bool((ev.get("state_deltas") or {}).get("polarity_inversion_active"))
        or "polarity inversion" in str(ev.get("summary", "")).lower()
        or "vex's effect" in str(ev.get("summary", "")).lower()
    ]

    if inversion_events:
        inv_ev = inversion_events[0]
        inv_actors = set(inv_ev.get("actors") or [])
        inv_idx = valid_events.index(inv_ev)
        precursor: dict[str, Any] | None = None
        for prev_ev in valid_events[:inv_idx]:
            if set(prev_ev.get("actors") or []) & inv_actors:
                precursor = prev_ev
                break
        chain_evs = [precursor, inv_ev] if precursor is not None else [inv_ev]
        actor_names = [
            _resolve_actor_name(a, safe_cores)
            for a in (inv_ev.get("actors") or [])[:2]
        ]
        names_str = " & ".join(actor_names) if actor_names else "Enclave Specialist"
        completed_chains.append(
            _build_chain_record(
                pattern_type="POLARITY_INVERSION_ANOMALY",
                title=f"Vex's Effect Triggered: {names_str} Under Cortical Polarity Inversion",
                narrative_summary=(
                    f"High geomagnetic shear and cumulative stress triggered a rare Polarity Inversion "
                    f"({inv_ev.get('summary', '')})."
                ),
                chain_events=chain_evs,
                scored_by_id=scored_by_id,
                status="COMPLETED",
            )
        )

    # Sort completed_chains and developing_stories by salience descending
    completed_chains.sort(
        key=lambda c: (-float(c.get("salience_score", 0.0)), str(c.get("story_id", "")))
    )
    developing_stories.sort(
        key=lambda d: (-float(d.get("salience_score", 0.0)), str(d.get("story_id", "")))
    )

    # Ensure if valid_events exist and developing_stories is empty, we surface at least 1 developing thread
    if valid_events and not developing_stories:
        seed_ev = scored_events_sorted[-1] if len(scored_events_sorted) > 1 else scored_events_sorted[0]
        developing_stories.append(
            _build_chain_record(
                pattern_type="RIVALRY_TO_BREAKTHROUGH",
                title=f"Ongoing Inquiry at {seed_ev.get('location', 'Enclave_Crater_Valley')}",
                narrative_summary=(
                    f"Open empirical thread from {seed_ev.get('day_phase', 'DAWN_SHIFT')}: "
                    f"{seed_ev.get('summary', 'Field telemetry logged for next Sol follow-up.')}"
                ),
                chain_events=[seed_ev],
                scored_by_id=scored_by_id,
                status="DEVELOPING",
                missing_payoff_step="Next-Sol experimental verification.",
            )
        )

    pattern_counts: dict[str, int] = {pat: 0 for pat in SUPPORTED_PATTERNS}
    for chain in completed_chains:
        pat = str(chain.get("pattern_type", ""))
        if pat in pattern_counts:
            pattern_counts[pat] += 1

    return {
        "supported_patterns": list(SUPPORTED_PATTERNS),
        "completed_chains": completed_chains,
        "developing_stories": developing_stories,
        "scored_events": scored_events_sorted,
        "top_events": scored_events_sorted[:5],
        "pattern_counts": pattern_counts,
        "total_events_sifted": len(valid_events),
    }
