"""Budgeted 10-Block Deterministic Context Compiler (WP-3).

Synthesizes architectural patterns from:
- AI Dungeon: ~70/30 Required/Dynamic token split and verbatim recency protection.
- NovelAI: Ordered token reservations and Context Viewer inclusion/exclusion manifest.
- SillyTavern: Swap-mode single active character card (Law L06), pinned voice
  dialogue anchors, and keyword + `and_keys` + `sticky_ticks` lorebook matching.

Enforces:
- Law L06: Strictly 1 full character card (`pov_core`) loaded per scene; interlocutors
  are rendered exclusively as asymmetric dyadic views (`bond_strength`, phase, and
  how the active POV perceives them), never leaking interlocutors' private core cards.
- Law L07: Total compiled tokens <= `max_tokens` (default 3500) with a complete
  10-block NovelAI-style inspection manifest.
- Law L10: Bracketed `[Author's Note: ...]` placed at depth 0 (Block 10) right
  before generation carrying `next_pov_target` for the Rashomon baton handoff.
"""

import math
import re
from typing import Any

from engine.memory_stream import retrieve_top_memories

TOKEN_MULTIPLIER: float = 1.35

BLOCK_SPECS: tuple[dict[str, Any], ...] = (
    {
        "block_index": 1,
        "block_id": "system_contract",
        "cap_tokens": 300,
        "required": True,
        "never_trim": True,
    },
    {
        "block_index": 2,
        "block_id": "pov_core_and_voice",
        "cap_tokens": 450,
        "required": True,
        "never_trim": True,
    },
    {
        "block_index": 3,
        "block_id": "momentary_state_and_caps",
        "cap_tokens": 150,
        "required": True,
        "never_trim": False,
    },
    {
        "block_index": 4,
        "block_id": "world_chronosphere_slice",
        "cap_tokens": 200,
        "required": True,
        "never_trim": False,
    },
    {
        "block_index": 5,
        "block_id": "dyadic_interlocutor_views",
        "cap_tokens": 300,
        "required": True,
        "never_trim": False,
    },
    {
        "block_index": 6,
        "block_id": "triggered_lore_cards",
        "cap_tokens": 450,
        "required": False,
        "never_trim": False,
    },
    {
        "block_index": 7,
        "block_id": "retrieved_memories",
        "cap_tokens": 550,
        "required": False,
        "never_trim": False,
    },
    {
        "block_index": 8,
        "block_id": "rolling_coarse_summary",
        "cap_tokens": 300,
        "required": False,
        "never_trim": False,
    },
    {
        "block_index": 9,
        "block_id": "verbatim_prev_handoff",
        "cap_tokens": 650,
        "required": True,
        "never_trim": False,
    },
    {
        "block_index": 10,
        "block_id": "authors_note_depth_zero",
        "cap_tokens": 120,
        "required": True,
        "never_trim": True,
    },
)

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def estimate_tokens(text: str) -> int:
    """Deterministic subword token estimator: ceil(len(text.split()) * 1.35)."""
    if not text or not text.strip():
        return 0
    word_count = len(text.split())
    return int(math.ceil(word_count * TOKEN_MULTIPLIER))


def _max_words_for_tokens(token_cap: int) -> int:
    """Return the maximum word count whose estimated tokens <= token_cap."""
    if token_cap <= 0:
        return 0
    w = int(math.floor(token_cap / TOKEN_MULTIPLIER))
    while w > 0 and int(math.ceil(w * TOKEN_MULTIPLIER)) > token_cap:
        w -= 1
    return max(0, w)


def _trim_at_sentence_boundary(
    text: str, token_cap: int, keep_tail: bool = False
) -> tuple[str, bool]:
    """Trim text cleanly to fit within `token_cap` tokens.

    Prefers sentence boundaries; falls back to word-boundary truncation if a
    single sentence exceeds `token_cap`. When `keep_tail=True`, preserves the
    most recent (trailing) text so baton handoffs are never lost.
    """
    clean = (text or "").strip()
    if not clean:
        return "", False
    if token_cap <= 0:
        return "", True
    if estimate_tokens(clean) <= token_cap:
        return clean, False

    sentences = [s.strip() for s in _SENTENCE_SPLIT_RE.split(clean) if s.strip()]
    if len(sentences) > 1:
        selected: list[str] = []
        iterable = reversed(sentences) if keep_tail else sentences
        for sent in iterable:
            candidate_list = (
                [sent] + selected if keep_tail else selected + [sent]
            )
            candidate_text = " ".join(candidate_list)
            if estimate_tokens(candidate_text) <= token_cap:
                selected = candidate_list
            else:
                break
        if selected:
            return " ".join(selected), True

    max_words = _max_words_for_tokens(token_cap)
    if max_words <= 0:
        return "", True
    words = clean.split()
    trimmed_words = words[-max_words:] if keep_tail else words[:max_words]
    return " ".join(trimmed_words), True


def _extract_char_identity(card: dict[str, Any]) -> dict[str, Any]:
    """Extract public identity metadata from a v2 or flat character card."""
    ident = card.get("agent_identity", {})
    if not isinstance(ident, dict):
        ident = {}
    char_id = str(
        ident.get("character_id")
        or card.get("character_id")
        or card.get("id")
        or "unknown_character"
    )
    name = str(ident.get("name") or card.get("name") or char_id)
    epithet = str(
        ident.get("epithet")
        or card.get("epithet")
        or card.get("title")
        or "Specialist"
    )
    squad = str(ident.get("squad") or card.get("squad") or "The_Enclave")
    role = str(
        ident.get("dialectic_role")
        or card.get("dialectic_role")
        or card.get("role")
        or "Anchor"
    )
    grand_project = str(
        ident.get("grand_project")
        or card.get("grand_project")
        or "Enclave Sanctuary"
    )
    return {
        "character_id": char_id,
        "name": name,
        "epithet": epithet,
        "squad": squad,
        "dialectic_role": role,
        "grand_project": grand_project,
    }


def _build_block_1_system_contract(
    pov_ident: dict[str, Any], next_pov_target: str, cap: int
) -> tuple[str, bool]:
    text = (
        "[BLOCK 1: SYSTEM CONTRACT & ENCLAVE NARRATIVE LAWS]\n"
        "Setting: The Enclave of the 16 (Exoplanet PvE Sanctuary — Steampunk Cyberpunk by Hand).\n"
        "Conflict Law: Strictly Player-vs-Environment (Person vs. Nature + Person vs. Self / "
        "Genius vs. The Mundane). Zero human villains, zero betrayals.\n"
        f"Rashomon Scalpel & Relay (Law L06 / L10): Write strictly from the single limited third-person "
        f"or close POV of {pov_ident['name']} ({pov_ident['character_id']}, {pov_ident['epithet']}). "
        f"Never access private internal thoughts of other characters. Conclude the segment with a concrete "
        f"physical or interpersonal baton handoff to {next_pov_target}.\n"
        "Vegetables Covered in Cheese: Ground technical problem-solving in real physics, metallurgy, "
        "mycology, or magnetohydrodynamics wrapped in warm, witty family banter."
    )
    return _trim_at_sentence_boundary(text, cap)


def _build_block_2_pov_core_and_voice(
    pov_core: dict[str, Any], pov_ident: dict[str, Any], cap: int
) -> tuple[str, bool]:
    tier1 = pov_core.get("tier_1_causal_trait_distributions", {})
    b5 = tier1.get("big_five_distributions", {}) if isinstance(tier1, dict) else {}
    trait_parts: list[str] = []
    for axis in (
        "openness",
        "conscientiousness",
        "extraversion",
        "agreeableness",
        "neuroticism",
    ):
        axis_obj = b5.get(axis, {})
        if isinstance(axis_obj, dict) and "mean" in axis_obj:
            trait_parts.append(f"{axis[0].upper()}:{float(axis_obj['mean']):.2f}")
    if not trait_parts and isinstance(pov_core.get("ocean_mean"), list):
        vals = pov_core["ocean_mean"]
        for lbl, val in zip(("O", "C", "E", "A", "N"), vals):
            trait_parts.append(f"{lbl}:{float(val):.2f}")

    tier4 = pov_core.get("tier_4_self_concept_and_narrative_arc", {})
    if not isinstance(tier4, dict):
        tier4 = {}
    lens = tier4.get("cognitive_lens", {}) if isinstance(tier4.get("cognitive_lens"), dict) else {}
    voice = (
        tier4.get("voice_and_syntax_anchors", {})
        if isinstance(tier4.get("voice_and_syntax_anchors"), dict)
        else {}
    )
    arc = tier4.get("narrative_arc", {}) if isinstance(tier4.get("narrative_arc"), dict) else {}

    mbti = lens.get("mbti_type") or pov_core.get("mbti") or "ISTJ"
    enneagram = lens.get("enneagram_self_concept") or "1w9"
    problem_lens = lens.get("problem_solving_lens") or "Empirical structural craftsmanship."
    tagline = voice.get("tagline") or pov_core.get("tagline") or "Measured, hyper-competent specialist."
    cadence = voice.get("baseline_cadence") or pov_core.get("baseline_cadence") or "Crisp, technical, affectionate."
    dialogues = (
        voice.get("pinned_example_dialogues")
        or pov_core.get("pinned_example_dialogues")
        or []
    )
    lie_believed = arc.get("the_lie_believed") or ""
    mundane_frustration = arc.get("genius_vs_mundane_frustration") or ""

    dialogue_lines = " | ".join(str(d).strip() for d in dialogues[:2] if d)
    lines = [
        f"[BLOCK 2: ACTIVE POV CORE & VOICE ANCHORS — {pov_ident['name']} ({pov_ident['character_id']})]",
        f"Identity: {pov_ident['name']}, {pov_ident['epithet']} | Squad: {pov_ident['squad']} | "
        f"Role: {pov_ident['dialectic_role']} | Grand Project: {pov_ident['grand_project']}.",
        f"Causal Trait Baseline (OCEAN): {', '.join(trait_parts) if trait_parts else 'Balanced'}. "
        f"Self-Concept Lens: {mbti} / {enneagram} — {problem_lens}",
        f"Voice Tagline: {tagline} Cadence: {cadence}",
    ]
    if lie_believed or mundane_frustration:
        lines.append(
            f"Arc Tension: {lie_believed} Mundane Friction: {mundane_frustration}".strip()
        )
    if dialogue_lines:
        lines.append(f"Pinned Voice Examples: {dialogue_lines}")

    return _trim_at_sentence_boundary("\n".join(lines), cap)


def _build_block_3_momentary_state_and_caps(
    pov_core: dict[str, Any], pov_state: dict[str, Any], cap: int
) -> tuple[str, bool]:
    tier3 = pov_core.get("tier_3_momentary_state_and_override_physics", {})
    default_vec = (
        tier3.get("current_state_vector", {}) if isinstance(tier3, dict) else {}
    )
    state_src = pov_state if isinstance(pov_state, dict) and pov_state else default_vec

    stress = float(state_src.get("stress", default_vec.get("stress", 0.30)))
    fatigue = float(state_src.get("fatigue", default_vec.get("fatigue", 0.20)))
    inverted = bool(
        state_src.get(
            "polarity_inversion_active",
            default_vec.get("polarity_inversion_active", False),
        )
    )

    caps_directives: list[str] = []
    if isinstance(state_src.get("active_caps_directives"), list):
        caps_directives.extend(str(x) for x in state_src["active_caps_directives"] if x)
    elif isinstance(state_src.get("behavioral_directive"), str):
        caps_directives.append(state_src["behavioral_directive"])
    else:
        tier2 = pov_core.get("tier_2_caps_situational_signatures", {})
        rules = tier2.get("rules", []) if isinstance(tier2, dict) else []
        for rule in rules[:2]:
            if isinstance(rule, dict) and rule.get("behavioral_directive"):
                caps_directives.append(
                    f"{rule.get('rule_id', 'CAPS')}: {rule['behavioral_directive']}"
                )

    inversion_note = "Inactive (Standard Causal Persona)."
    if inverted:
        inv_prof = (
            tier3.get("polarity_inversion_profile", {})
            if isinstance(tier3, dict)
            else {}
        )
        sign = inv_prof.get("ironic_star_sign", "Polarity Inverted")
        beh = inv_prof.get(
            "inverted_behavior", "Acts on sudden uncharacteristic intuition."
        )
        inversion_note = f"ACTIVE [{sign}]: {beh}"

    lines = [
        "[BLOCK 3: MOMENTARY STATE & CAPS SITUATIONAL SIGNATURES]",
        f"Stress: {stress:.2f} | Fatigue: {fatigue:.2f} | Polarity Inversion: {inversion_note}",
    ]
    if caps_directives:
        lines.append(f"Active CAPS Directives: {' ; '.join(caps_directives[:2])}")
    return _trim_at_sentence_boundary("\n".join(lines), cap)


def _build_block_4_world_chronosphere_slice(
    world_snapshot: dict[str, Any], cap: int
) -> tuple[str, bool]:
    host = world_snapshot.get("deterministic_host_physics_engine", world_snapshot)
    if not isinstance(host, dict):
        host = {}
    chrono = host.get("chronosphere", world_snapshot.get("chronosphere", world_snapshot))
    if not isinstance(chrono, dict):
        chrono = {}
    meteo = host.get(
        "fictitious_exoplanet_meteorology",
        world_snapshot.get("fictitious_exoplanet_meteorology", world_snapshot.get("weather", {})),
    )
    if not isinstance(meteo, dict):
        meteo = {}
    gov = host.get(
        "colony_governance_and_friction_ledger",
        world_snapshot.get("colony_governance_and_friction_ledger", {}),
    )
    if not isinstance(gov, dict):
        gov = {}

    sol = chrono.get("colony_sol", world_snapshot.get("colony_sol", 1))
    tick_id = chrono.get("tick_id", world_snapshot.get("tick_id", 1))
    phase = chrono.get("day_phase", world_snapshot.get("day_phase", "DAWN_SHIFT"))
    suns = chrono.get("twin_suns_orbital_state", {})
    kp_exo = (
        suns.get("magnetic_polarity_shear_kp_exo", 4.5)
        if isinstance(suns, dict)
        else 4.5
    )

    biome = meteo.get("active_biome_cell", "Enclave_Crater_Valley")
    regime = meteo.get("micro_climate_regime", "Bifurcated_Thermal_Shear")
    temp_v = meteo.get("valley_floor_temp_c", 14.0)
    hazard = meteo.get("active_environmental_hazard", "Nominal_Spore_Drift")
    geode_pct = meteo.get("geode_charge_capacity_pct", 75.0)
    harvest_item = gov.get(
        "active_schrodinger_harvest_item", "Crystalline Iron-Wheat"
    )

    text = (
        "[BLOCK 4: WORLD CHRONOSPHERE & EXOPLANET METEOROLOGY]\n"
        f"Colony Sol {sol} | Tick {tick_id} | Phase: {phase} | Kp_exo Magnetic Shear: {kp_exo}.\n"
        f"Biome: {biome} ({regime}, Valley {temp_v}C) | Hazard: {hazard} | "
        f"Geode Charge: {geode_pct}% | Active Resource Debate: {harvest_item}."
    )
    return _trim_at_sentence_boundary(text, cap)


def _lookup_dyadic_relationship(
    pov_id: str, other_id: str, relationships: dict[str, Any]
) -> dict[str, Any]:
    """Lookup how `pov_id` perceives `other_id` from any relationship map layout."""
    if not isinstance(relationships, dict):
        return {}

    # 1. Direct nested lookup: relationships[pov_id][other_id]
    if isinstance(relationships.get(pov_id), dict):
        sub = relationships[pov_id].get(other_id)
        if isinstance(sub, dict):
            return sub

    # 2. Composite string key lookup
    candidate_keys = (
        f"{pov_id}->{other_id}",
        f"{pov_id}:{other_id}",
        f"{pov_id}__{other_id}",
        f"{pov_id}_{other_id}",
        f"{pov_id}|{other_id}",
        f"{other_id}->{pov_id}",
        f"{other_id}:{pov_id}",
        f"{other_id}__{pov_id}",
        f"{other_id}_{pov_id}",
        other_id,
    )
    for k in candidate_keys:
        val = relationships.get(k)
        if isinstance(val, dict):
            return val

    # 3. List of edges under 'edges', 'pairs', 'matrix', or 'relationships'
    for list_key in ("edges", "pairs", "matrix", "relationships", "dyads"):
        edges = relationships.get(list_key)
        if isinstance(edges, list):
            for edge in edges:
                if not isinstance(edge, dict):
                    continue
                src = edge.get("source") or edge.get("from") or edge.get("actor_a") or edge.get("character_a")
                dst = edge.get("target") or edge.get("to") or edge.get("actor_b") or edge.get("character_b")
                if (src == pov_id and dst == other_id) or (
                    src == other_id and dst == pov_id
                ):
                    return edge

    return {}


def _build_block_5_dyadic_interlocutor_views(
    pov_ident: dict[str, Any],
    interlocutor_cores: list[dict[str, Any]],
    relationships: dict[str, Any],
    cap: int,
) -> tuple[str, bool, list[str]]:
    """Build Block 5 enforcing Law L06 (Swap-Mode Asymmetric Dyadic Views).

    Strictly capped at max 3 interlocutors at <= 100 tokens each (300 total).
    NEVER reads or emits interlocutors' private core card sections (traits,
    CAPS rules, voice examples, or narrative arc secrets).
    """
    pov_id = pov_ident["character_id"]
    if not interlocutor_cores or cap <= 0:
        return (
            "[BLOCK 5: DYADIC INTERLOCUTOR VIEWS]\nSolo scene segment (no interlocutors present).",
            False,
            [],
        )

    per_interlocutor_cap = min(100, max(1, cap // 3))
    views: list[str] = ["[BLOCK 5: DYADIC INTERLOCUTOR VIEWS (LAW L06 SWAP-MODE)]"]
    included_ids: list[str] = []
    any_trimmed = False

    filtered_cores = [
        c
        for c in interlocutor_cores
        if isinstance(c, dict)
        and _extract_char_identity(c)["character_id"] != pov_id
    ]
    if not filtered_cores:
        filtered_cores = [c for c in interlocutor_cores if isinstance(c, dict)]

    for other_core in filtered_cores[:3]:
        other_ident = _extract_char_identity(other_core)
        other_id = other_ident["character_id"]
        rel = _lookup_dyadic_relationship(pov_id, other_id, relationships)

        bond = float(
            rel.get(
                "bond_strength",
                rel.get("bond", other_core.get("bond_strength", 0.65)),
            )
        )
        phase = str(
            rel.get(
                "relationship_phase",
                rel.get("phase", rel.get("status", "Trusted_Enclave_Counterpart")),
            )
        )
        perception = str(
            rel.get("pov_perception")
            or rel.get("perceived_as")
            or rel.get("perception")
            or rel.get("dynamic_summary")
            or rel.get("notes")
            or (
                f"{pov_ident['name']} perceives {other_ident['name']} ({other_ident['epithet']}, "
                f"{other_ident['squad']} {other_ident['dialectic_role']}) through their shared work "
                f"around {other_ident['grand_project']}."
            )
        )

        entry_raw = (
            f"- Interlocutor {other_ident['name']} ({other_id}, {other_ident['epithet']}): "
            f"Bond={bond:.2f} | Phase={phase} | "
            f"{pov_ident['name']}'s Perception: {perception}"
        )
        entry_trimmed, was_trimmed = _trim_at_sentence_boundary(
            entry_raw, per_interlocutor_cap
        )
        if was_trimmed:
            any_trimmed = True
        if entry_trimmed:
            views.append(entry_trimmed)
            included_ids.append(other_id)

    combined, block_trimmed = _trim_at_sentence_boundary("\n".join(views), cap)
    return combined, (any_trimmed or block_trimmed), included_ids


def _extract_authors_note_text(authors_note: dict[str, Any]) -> str:
    if not isinstance(authors_note, dict):
        return str(authors_note or "")
    parts: list[str] = []
    for k in (
        "text",
        "note",
        "style_directive",
        "guidance",
        "beat",
        "science_vegetable",
        "handoff_mechanic",
        "next_pov_target",
    ):
        val = authors_note.get(k)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
        elif isinstance(val, list):
            parts.extend(str(x) for x in val if x)
    return " ".join(parts)


def _build_block_6_triggered_lore_cards(
    lorebook: list[dict[str, Any]],
    prev_segment_text: str,
    authors_note: dict[str, Any],
    current_tick: int,
    cap: int,
) -> tuple[str, bool, list[str], dict[str, str]]:
    """Evaluate keyword + `and_keys` + `sticky_ticks` lorebook triggers."""
    included_lore_ids: list[str] = []
    excluded_lore_reasons: dict[str, str] = {}

    if not lorebook:
        return "", False, included_lore_ids, excluded_lore_reasons

    scan_corpus = f"{prev_segment_text or ''} {_extract_authors_note_text(authors_note)}".lower()
    triggered_cards: list[tuple[float, str, dict[str, Any]]] = []

    for idx, card in enumerate(lorebook):
        if not isinstance(card, dict):
            continue
        card_id = str(
            card.get("id")
            or card.get("card_id")
            or card.get("lore_id")
            or f"lore_{idx:03d}"
        )

        # Check sticky persistence
        sticky_remaining = int(
            card.get("sticky_remaining", card.get("active_sticky_ticks", 0)) or 0
        )
        sticky_ticks_cfg = int(card.get("sticky_ticks", 0) or 0)
        last_trig = card.get("last_triggered_tick")
        sticky_by_tick = (
            sticky_ticks_cfg > 0
            and last_trig is not None
            and 0 <= (current_tick - int(last_trig)) <= sticky_ticks_cfg
        )
        is_sticky = (
            bool(card.get("sticky_active", False))
            or bool(card.get("always_on", False))
            or sticky_remaining > 0
            or sticky_by_tick
        )

        keys = (
            card.get("keys")
            or card.get("keywords")
            or card.get("trigger_keys")
            or []
        )
        and_keys = (
            card.get("and_keys")
            or card.get("secondary_keys")
            or card.get("require_all_keys")
            or []
        )

        primary_match = any(
            str(k).strip().lower() in scan_corpus
            for k in keys
            if str(k).strip()
        )
        and_match = (
            all(
                str(ak).strip().lower() in scan_corpus
                for ak in and_keys
                if str(ak).strip()
            )
            if and_keys
            else True
        )

        if is_sticky or (primary_match and and_match):
            priority = float(card.get("priority", card.get("order", 0.0)) or 0.0)
            triggered_cards.append((priority, card_id, card))
        else:
            if primary_match and not and_match:
                excluded_lore_reasons[card_id] = "missing_and_keys"
            else:
                excluded_lore_reasons[card_id] = "keyword_not_triggered"

    if not triggered_cards:
        return "", False, included_lore_ids, excluded_lore_reasons

    triggered_cards.sort(key=lambda item: (-item[0], item[1]))

    if cap <= 0:
        for _prio, cid, _card in triggered_cards:
            excluded_lore_reasons[cid] = "token_budget_exceeded"
        return "", True, included_lore_ids, excluded_lore_reasons

    header_line = "[BLOCK 6: TRIGGERED LOREBOOK CARDS]"
    accepted_lines: list[str] = [header_line]
    any_trimmed = False

    for _prio, cid, card in triggered_cards:
        body = str(
            card.get("content")
            or card.get("text")
            or card.get("body")
            or card.get("summary")
            or card.get("description")
            or ""
        ).strip()
        if not body:
            excluded_lore_reasons[cid] = "empty_content"
            continue

        prefix = f"[Lore:{cid}]"
        full_entry = f"{prefix} {body}"
        candidate_block = "\n".join(accepted_lines + [full_entry])
        if estimate_tokens(candidate_block) <= cap:
            accepted_lines.append(full_entry)
            included_lore_ids.append(cid)
            continue

        # Attempt clean sentence-boundary trim to fit remaining budget
        sentences = [
            s.strip() for s in _SENTENCE_SPLIT_RE.split(body) if s.strip()
        ]
        fitted_sentences: list[str] = []
        for sent in sentences:
            if not sent.endswith((".", "!", "?")):
                continue
            partial_entry = f"{prefix} {' '.join(fitted_sentences + [sent])}"
            if estimate_tokens("\n".join(accepted_lines + [partial_entry])) <= cap:
                fitted_sentences.append(sent)
            else:
                break

        if fitted_sentences:
            accepted_lines.append(f"{prefix} {' '.join(fitted_sentences)}")
            included_lore_ids.append(cid)
            any_trimmed = True
        else:
            excluded_lore_reasons[cid] = "token_budget_exceeded"
            any_trimmed = True

    if not included_lore_ids:
        return "", any_trimmed, included_lore_ids, excluded_lore_reasons

    return "\n".join(accepted_lines), any_trimmed, included_lore_ids, excluded_lore_reasons


def _build_block_7_retrieved_memories(
    memories: list[dict[str, Any]],
    query_text: str,
    current_hour: float,
    cap: int,
) -> tuple[str, bool, list[str]]:
    if not memories or cap <= 0:
        return "", bool(memories and cap <= 0), []

    top_memories = retrieve_top_memories(
        memories=memories,
        query_text=query_text,
        current_hour=current_hour,
        top_k=8,
    )
    if not top_memories:
        return "", False, []

    lines: list[str] = ["[BLOCK 7: RETRIEVED SMALLVILLE MEMORY STREAM]"]
    included_mem_ids: list[str] = []
    any_trimmed = False

    for idx, mem in enumerate(top_memories):
        mem_id = str(
            mem.get("event_id")
            or mem.get("memory_id")
            or mem.get("id")
            or f"mem_{idx:03d}"
        )
        summary = str(
            mem.get("summary")
            or mem.get("insight_text")
            or mem.get("text")
            or mem.get("content")
            or ""
        ).strip()
        if not summary:
            continue
        score = float(mem.get("retrieval_score", 0.0))
        entry = f"- ({mem_id}, score={score:.2f}) {summary}"
        candidate = "\n".join(lines + [entry])
        if estimate_tokens(candidate) <= cap:
            lines.append(entry)
            included_mem_ids.append(mem_id)
        else:
            # Try sentence trim on the memory if none or partial fit
            rem_cap = cap - estimate_tokens("\n".join(lines))
            if rem_cap >= 15:
                trimmed_entry, _ = _trim_at_sentence_boundary(entry, rem_cap)
                if trimmed_entry and estimate_tokens("\n".join(lines + [trimmed_entry])) <= cap:
                    lines.append(trimmed_entry)
                    included_mem_ids.append(mem_id)
            any_trimmed = True
            break

    if not included_mem_ids:
        return "", True, []
    return "\n".join(lines), any_trimmed, included_mem_ids


def _build_block_8_rolling_summary(
    rolling_summary: str, cap: int
) -> tuple[str, bool]:
    clean = (rolling_summary or "").strip()
    if not clean:
        return "", False
    if cap <= 0:
        return "", True
    text = f"[BLOCK 8: ROLLING COARSE SUMMARY]\n{clean}"
    return _trim_at_sentence_boundary(text, cap)


def _build_block_9_verbatim_handoff(
    prev_segment_text: str, cap: int
) -> tuple[str, bool]:
    clean = (prev_segment_text or "").strip()
    if not clean:
        clean = "Dawn shift begins across the Enclave crater valley."
    header = "[BLOCK 9: VERBATIM PREVIOUS SCENE & BATON HANDOFF]"
    header_tokens = estimate_tokens(header)
    body_cap = max(1, cap - header_tokens)
    trimmed_body, was_trimmed = _trim_at_sentence_boundary(
        clean, body_cap, keep_tail=True
    )
    full_text = f"{header}\n{trimmed_body}".strip()
    if estimate_tokens(full_text) > cap:
        full_text, was_trimmed = _trim_at_sentence_boundary(
            full_text, cap, keep_tail=True
        )
    return full_text, was_trimmed


def _build_block_10_authors_note(
    authors_note: dict[str, Any],
    pov_ident: dict[str, Any],
     cap: int,
) -> tuple[str, bool, str]:
    if not isinstance(authors_note, dict):
        authors_note = {"note": str(authors_note or "")}

    next_pov_target = str(
        authors_note.get("next_pov_target")
        or authors_note.get("handoff_target")
        or authors_note.get("next_pov_id")
        or authors_note.get("target_pov")
        or "enclave_04_leo"
    ).strip()

    style = str(
        authors_note.get("style_directive")
        or authors_note.get("note")
        or authors_note.get("text")
        or authors_note.get("guidance")
        or "Maintain Steampunk-Cyberpunk tactile precision and affectionate family banter."
    ).strip()
    sci_veg = str(authors_note.get("science_vegetable") or "").strip()
    extra = f" Science focus: {sci_veg}." if sci_veg else ""

    raw_note = (
        f"[Author's Note: Active POV={pov_ident['character_id']}. {style}{extra} "
        f"Rashomon Relay Law L10: Conclude this segment with an explicit physical/interpersonal "
        f"baton handoff to next_pov_target={next_pov_target}.]"
    )
    if estimate_tokens(raw_note) <= cap:
        return raw_note, False, next_pov_target

    # Preserve bracketed format and next_pov_target even under tight cap
    compact_note = (
        f"[Author's Note: POV={pov_ident['character_id']}; {style} "
        f"Handoff to next_pov_target={next_pov_target}.]"
    )
    if estimate_tokens(compact_note) <= cap:
        return compact_note, True, next_pov_target

    minimal_note = f"[Author's Note: next_pov_target={next_pov_target}]"
    return minimal_note, True, next_pov_target


def compile_scene_context(
    pov_core: dict,
    pov_state: dict,
    world_snapshot: dict,
    interlocutor_cores: list[dict],
    relationships: dict,
    lorebook: list[dict],
    memories: list[dict],
    rolling_summary: str,
    prev_segment_text: str,
    authors_note: dict,
    max_tokens: int = 3500,
) -> dict:
    """Compile the 10-block budgeted scene context and NovelAI-style manifest.

    Satisfies:
    - Law L06: Single active full character card (`full_cards_loaded_count == 1`),
      asymmetric dyadic views for up to 3 interlocutors.
    - Law L07: Total compiled tokens <= `max_tokens` (default 3500) with complete
      block-level manifest (`included_lore_ids`, `excluded_lore_reasons`, etc.).
    - Law L10: Depth-0 bracketed `[Author's Note: ...]` with `next_pov_target`.
    """
    effective_max_tokens = max(100, int(max_tokens))
    pov_ident = _extract_char_identity(pov_core or {})
    active_pov_id = pov_ident["character_id"]

    # Extract current tick and hour for sticky lore and Smallville retrieval
    host = (world_snapshot or {}).get(
        "deterministic_host_physics_engine", world_snapshot or {}
    )
    chrono = (
        host.get("chronosphere", (world_snapshot or {}).get("chronosphere", {}))
        if isinstance(host, dict)
        else {}
    )
    current_tick = int(
        (chrono.get("tick_id") if isinstance(chrono, dict) else None)
        or (world_snapshot or {}).get("tick_id")
        or (pov_state or {}).get("tick_id")
        or 1
    )
    colony_sol = int(
        (chrono.get("colony_sol") if isinstance(chrono, dict) else None)
        or (world_snapshot or {}).get("colony_sol")
        or 1
    )
    current_hour = float(
        (pov_state or {}).get(
            "current_hour", (colony_sol - 1) * 24.0 + float(current_tick)
        )
    )

    # First build Block 10 so `next_pov_target` is resolved for Block 1 & manifest
    b10_cap = BLOCK_SPECS[9]["cap_tokens"]
    b10_text, b10_trimmed, next_pov_target = _build_block_10_authors_note(
        authors_note or {}, pov_ident, b10_cap
    )

    b1_text, b1_trimmed = _build_block_1_system_contract(
        pov_ident, next_pov_target, BLOCK_SPECS[0]["cap_tokens"]
    )
    b2_text, b2_trimmed = _build_block_2_pov_core_and_voice(
        pov_core or {}, pov_ident, BLOCK_SPECS[1]["cap_tokens"]
    )
    b3_text, b3_trimmed = _build_block_3_momentary_state_and_caps(
        pov_core or {}, pov_state or {}, BLOCK_SPECS[2]["cap_tokens"]
    )
    b4_text, b4_trimmed = _build_block_4_world_chronosphere_slice(
        world_snapshot or {}, BLOCK_SPECS[3]["cap_tokens"]
    )
    b5_text, b5_trimmed, interlocutor_ids = (
        _build_block_5_dyadic_interlocutor_views(
            pov_ident,
            interlocutor_cores or [],
            relationships or {},
            BLOCK_SPECS[4]["cap_tokens"],
        )
    )
    b9_text, b9_trimmed = _build_block_9_verbatim_handoff(
        prev_segment_text or "", BLOCK_SPECS[8]["cap_tokens"]
    )

    # Dynamic Blocks (6, 7, 8)
    b6_text, b6_trimmed, included_lore_ids, excluded_lore_reasons = (
        _build_block_6_triggered_lore_cards(
            lorebook=lorebook or [],
            prev_segment_text=prev_segment_text or "",
            authors_note=authors_note or {},
            current_tick=current_tick,
            cap=BLOCK_SPECS[5]["cap_tokens"],
        )
    )

    memory_query = (
        f"{pov_ident['name']} {pov_ident['grand_project']} "
        f"{prev_segment_text or ''} {_extract_authors_note_text(authors_note or {})}"
    ).strip()
    b7_text, b7_trimmed, retrieved_memory_ids = (
        _build_block_7_retrieved_memories(
            memories=memories or [],
            query_text=memory_query,
            current_hour=current_hour,
            cap=BLOCK_SPECS[6]["cap_tokens"],
        )
    )

    b8_text, b8_trimmed = _build_block_8_rolling_summary(
        rolling_summary or "", BLOCK_SPECS[7]["cap_tokens"]
    )

    raw_blocks: list[dict[str, Any]] = [
        {"spec": BLOCK_SPECS[0], "text": b1_text, "trimmed": b1_trimmed},
        {"spec": BLOCK_SPECS[1], "text": b2_text, "trimmed": b2_trimmed},
        {"spec": BLOCK_SPECS[2], "text": b3_text, "trimmed": b3_trimmed},
        {"spec": BLOCK_SPECS[3], "text": b4_text, "trimmed": b4_trimmed},
        {"spec": BLOCK_SPECS[4], "text": b5_text, "trimmed": b5_trimmed},
        {"spec": BLOCK_SPECS[5], "text": b6_text, "trimmed": b6_trimmed},
        {"spec": BLOCK_SPECS[6], "text": b7_text, "trimmed": b7_trimmed},
        {"spec": BLOCK_SPECS[7], "text": b8_text, "trimmed": b8_trimmed},
        {"spec": BLOCK_SPECS[8], "text": b9_text, "trimmed": b9_trimmed},
        {"spec": BLOCK_SPECS[9], "text": b10_text, "trimmed": b10_trimmed},
    ]

    def _current_total_tokens() -> int:
        return sum(estimate_tokens(rb["text"]) for rb in raw_blocks)

    # Budget shedding when max_tokens < 3500:
    # 1. Drop/trim Block 8 (rolling_coarse_summary) FIRST before verbatim recent text
    if _current_total_tokens() > effective_max_tokens and raw_blocks[7]["text"]:
        excess = _current_total_tokens() - effective_max_tokens
        b8_curr = estimate_tokens(raw_blocks[7]["text"])
        new_b8_cap = max(0, b8_curr - excess)
        if new_b8_cap < 20:
            raw_blocks[7]["text"] = ""
            raw_blocks[7]["trimmed"] = True
        else:
            raw_blocks[7]["text"], _ = _build_block_8_rolling_summary(
                rolling_summary or "", new_b8_cap
            )
            raw_blocks[7]["trimmed"] = True

    # 2. Trim/drop Block 6 (triggered_lore_cards) if still over budget
    if _current_total_tokens() > effective_max_tokens and raw_blocks[5]["text"]:
        excess = _current_total_tokens() - effective_max_tokens
        b6_curr = estimate_tokens(raw_blocks[5]["text"])
        new_b6_cap = max(0, b6_curr - excess)
        (
            raw_blocks[5]["text"],
            raw_blocks[5]["trimmed"],
            included_lore_ids,
            excluded_lore_reasons,
        ) = _build_block_6_triggered_lore_cards(
            lorebook=lorebook or [],
            prev_segment_text=prev_segment_text or "",
            authors_note=authors_note or {},
            current_tick=current_tick,
            cap=new_b6_cap,
        )

    # 3. Trim/drop Block 7 (retrieved_memories) if still over budget
    if _current_total_tokens() > effective_max_tokens and raw_blocks[6]["text"]:
        excess = _current_total_tokens() - effective_max_tokens
        b7_curr = estimate_tokens(raw_blocks[6]["text"])
        new_b7_cap = max(0, b7_curr - excess)
        raw_blocks[6]["text"], raw_blocks[6]["trimmed"], retrieved_memory_ids = (
            _build_block_7_retrieved_memories(
                memories=memories or [],
                query_text=memory_query,
                current_hour=current_hour,
                cap=new_b7_cap,
            )
        )

    # 4. If an artificially small max_tokens is passed in tests, trim trimmable required blocks
    for trim_idx in (4, 3, 2, 8):
        if _current_total_tokens() <= effective_max_tokens:
            break
        excess = _current_total_tokens() - effective_max_tokens
        curr_t = estimate_tokens(raw_blocks[trim_idx]["text"])
        target_cap = max(15, curr_t - excess)
        raw_blocks[trim_idx]["text"], _ = _trim_at_sentence_boundary(
            raw_blocks[trim_idx]["text"],
            target_cap,
            keep_tail=(trim_idx == 8),
        )
        raw_blocks[trim_idx]["trimmed"] = True

    manifest_blocks: list[dict[str, Any]] = []
    required_tokens = 0
    dynamic_tokens = 0

    for rb in raw_blocks:
        spec = rb["spec"]
        text_val = rb["text"]
        tok_count = estimate_tokens(text_val)
        if spec["required"]:
            required_tokens += tok_count
        else:
            dynamic_tokens += tok_count

        manifest_blocks.append(
            {
                "block_index": spec["block_index"],
                "block_id": spec["block_id"],
                "name": spec["block_id"],
                "category": "required" if spec["required"] else "dynamic",
                "required": spec["required"],
                "never_trim": spec["never_trim"],
                "cap_tokens": spec["cap_tokens"],
                "max_tokens": spec["cap_tokens"],
                "tokens": tok_count,
                "included": bool(text_val.strip()),
                "trimmed": bool(rb["trimmed"]),
                "text": text_val,
            }
        )

    prompt_text = "\n\n".join(
        b["text"] for b in manifest_blocks if b["text"].strip()
    )
    total_tokens = estimate_tokens(prompt_text)

    manifest = {
        "compiler_version": "enclave_context_compiler_v2.0.0",
        "blocks": manifest_blocks,
        "total_tokens": total_tokens,
        "block_tokens_sum": required_tokens + dynamic_tokens,
        "required_tokens": required_tokens,
        "dynamic_tokens": dynamic_tokens,
        "max_tokens": effective_max_tokens,
        "active_pov_id": active_pov_id,
        "full_cards_loaded_count": 1,
        "loaded_full_card_ids": [active_pov_id],
        "interlocutor_view_ids": interlocutor_ids,
        "next_pov_target": next_pov_target,
        "included_lore_ids": included_lore_ids,
        "excluded_lore_reasons": excluded_lore_reasons,
        "retrieved_memory_ids": retrieved_memory_ids,
    }

    return {
        "prompt_text": prompt_text,
        "manifest": manifest,
        "total_tokens": total_tokens,
        "max_tokens": effective_max_tokens,
        "active_pov_id": active_pov_id,
        "full_cards_loaded_count": 1,
        "next_pov_target": next_pov_target,
        "included_lore_ids": included_lore_ids,
        "excluded_lore_reasons": excluded_lore_reasons,
    }
