"""Counterfactual Personality Lab (`WP-3`).

Supports longitudinal controlled personality experiments across the 40 daily
Jules counterfactual replay sessions by holding the RNG seed, world snapshot,
and scene prompt strictly constant while shifting a single Big Five axis
(`openness`, `conscientiousness`, `extraversion`, `agreeableness`, or
`neuroticism`) by `delta`, clipped to [0.05, 0.95].
"""

import copy
import hashlib
import math
import re
from collections import Counter
from typing import Any

TRAIT_MIN_BOUND: float = 0.05
TRAIT_MAX_BOUND: float = 0.95

BIG_FIVE_AXES: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

_AXIS_ALIASES: dict[str, str] = {
    "o": "openness",
    "openness": "openness",
    "c": "conscientiousness",
    "conscientiousness": "conscientiousness",
    "e": "extraversion",
    "extraversion": "extraversion",
    "a": "agreeableness",
    "agreeableness": "agreeableness",
    "n": "neuroticism",
    "neuroticism": "neuroticism",
}

_WORD_RE = re.compile(r"[a-z0-9_]+")


def _clip_trait(val: float) -> float:
    return round(min(TRAIT_MAX_BOUND, max(TRAIT_MIN_BOUND, float(val))), 4)


def _normalize_axis(trait_axis: str) -> str:
    if not isinstance(trait_axis, str) or not trait_axis.strip():
        raise ValueError("trait_axis must be a non-empty Big Five axis string.")
    key = trait_axis.strip().lower()
    if key not in _AXIS_ALIASES:
        raise ValueError(
            f"Unsupported Big Five trait_axis '{trait_axis}'. "
            f"Must be one of {BIG_FIVE_AXES}."
        )
    return _AXIS_ALIASES[key]


def _read_axis_mean(core: dict[str, Any], axis: str) -> float:
    tier1 = core.get("tier_1_causal_trait_distributions", {})
    if isinstance(tier1, dict):
        b5 = tier1.get("big_five_distributions", {})
        if isinstance(b5, dict) and isinstance(b5.get(axis), dict):
            if "mean" in b5[axis]:
                return float(b5[axis]["mean"])
        if isinstance(b5, dict) and isinstance(b5.get(axis), (int, float)):
            return float(b5[axis])

    if isinstance(core.get("big_five"), dict) and axis in core["big_five"]:
        val = core["big_five"][axis]
        if isinstance(val, dict) and "mean" in val:
            return float(val["mean"])
        if isinstance(val, (int, float)):
            return float(val)

    if isinstance(core.get("ocean_mean"), list) and len(core["ocean_mean"]) == 5:
        idx = BIG_FIVE_AXES.index(axis)
        return float(core["ocean_mean"][idx])

    return 0.50


def _apply_axis_shift(
    variant_core: dict[str, Any], axis: str, new_mean: float, actual_delta: float
) -> None:
    """Apply the clipped trait mean shift onto `variant_core` in-place."""
    tier1 = variant_core.setdefault("tier_1_causal_trait_distributions", {})
    if isinstance(tier1, dict):
        b5 = tier1.setdefault("big_five_distributions", {})
        if isinstance(b5, dict):
            axis_obj = b5.get(axis)
            if isinstance(axis_obj, dict):
                axis_obj["mean"] = new_mean
                facets = axis_obj.get("facets")
                if isinstance(facets, dict):
                    for f_key, f_val in list(facets.items()):
                        if isinstance(f_val, (int, float)):
                            facets[f_key] = _clip_trait(float(f_val) + actual_delta)
            else:
                b5[axis] = {"mean": new_mean, "sd": 0.08, "facets": {}}

    if isinstance(variant_core.get("big_five"), dict):
        bf_entry = variant_core["big_five"].get(axis)
        if isinstance(bf_entry, dict):
            bf_entry["mean"] = new_mean
        else:
            variant_core["big_five"][axis] = new_mean

    if (
        isinstance(variant_core.get("ocean_mean"), list)
        and len(variant_core["ocean_mean"]) == 5
    ):
        idx = BIG_FIVE_AXES.index(axis)
        variant_core["ocean_mean"][idx] = new_mean


def build_counterfactual_variants(
    base_core: dict,
    scene_spec: dict,
    trait_axis: str,
    delta: float,
) -> dict:
    """Construct a controlled baseline + counterfactual variant pair.

    Holds `rng_seed`, `world_snapshot`, and `scene_prompt` strictly constant
    while shifting `trait_axis` by `delta` clipped to [0.05, 0.95].
    """
    if not isinstance(base_core, dict):
        raise ValueError("base_core must be a dictionary.")
    if not isinstance(scene_spec, dict):
        scene_spec = {}

    canonical_axis = _normalize_axis(trait_axis)
    requested_delta = float(delta)

    baseline_core = copy.deepcopy(base_core)
    variant_core = copy.deepcopy(base_core)

    baseline_mean = _clip_trait(_read_axis_mean(baseline_core, canonical_axis))
    variant_mean = _clip_trait(baseline_mean + requested_delta)
    actual_delta = round(variant_mean - baseline_mean, 4)

    _apply_axis_shift(variant_core, canonical_axis, variant_mean, actual_delta)

    ident = baseline_core.get("agent_identity", {})
    char_id = str(
        (ident.get("character_id") if isinstance(ident, dict) else None)
        or baseline_core.get("character_id")
        or baseline_core.get("id")
        or "enclave_03_silas"
    )

    frozen_scene_spec = copy.deepcopy(scene_spec)
    world_snapshot = copy.deepcopy(
        frozen_scene_spec.get(
            "world_snapshot", frozen_scene_spec.get("world_slice", {})
        )
    )
    scene_prompt = str(
        frozen_scene_spec.get("scene_prompt")
        or frozen_scene_spec.get("prompt")
        or frozen_scene_spec.get("summary")
        or frozen_scene_spec.get("situation")
        or "Controlled Enclave counterfactual scene evaluation."
    )
    tick_id = int(
        frozen_scene_spec.get("tick_id")
        or (world_snapshot.get("tick_id") if isinstance(world_snapshot, dict) else 1)
        or 1
    )
    rng_seed = str(
        frozen_scene_spec.get("rng_seed")
        or frozen_scene_spec.get("epoch_seed")
        or frozen_scene_spec.get("seed")
        or hashlib.sha256(
            f"cf_seed:{char_id}:{tick_id}:{scene_prompt}".encode("utf-8")
        ).hexdigest()[:16]
    )

    variant_core["counterfactual_metadata"] = {
        "is_counterfactual": True,
        "trait_axis": canonical_axis,
        "requested_delta": requested_delta,
        "actual_delta": actual_delta,
        "baseline_mean": baseline_mean,
        "variant_mean": variant_mean,
        "rng_seed": rng_seed,
    }

    study_hash = hashlib.sha256(
        f"{char_id}:{canonical_axis}:{requested_delta:.4f}:{rng_seed}".encode("utf-8")
    ).hexdigest()[:10]
    study_id = f"cf_{char_id}_{canonical_axis}_{requested_delta:+.2f}_{study_hash}"

    baseline_arm = {
        "arm": "baseline",
        "character_id": char_id,
        "core": baseline_core,
        "core_card": baseline_core,
        "trait_axis": canonical_axis,
        "trait_mean": baseline_mean,
        "delta": 0.0,
        "rng_seed": rng_seed,
        "world_snapshot": copy.deepcopy(world_snapshot),
        "scene_prompt": scene_prompt,
        "scene_spec": copy.deepcopy(frozen_scene_spec),
    }
    variant_arm = {
        "arm": "counterfactual",
        "character_id": char_id,
        "core": variant_core,
        "core_card": variant_core,
        "trait_axis": canonical_axis,
        "trait_mean": variant_mean,
        "delta": actual_delta,
        "requested_delta": requested_delta,
        "rng_seed": rng_seed,
        "world_snapshot": copy.deepcopy(world_snapshot),
        "scene_prompt": scene_prompt,
        "scene_spec": copy.deepcopy(frozen_scene_spec),
    }

    return {
        "study_id": study_id,
        "event_type": "COUNTERFACTUAL_REPLAY",
        "character_id": char_id,
        "trait_axis": canonical_axis,
        "requested_delta": requested_delta,
        "actual_delta": actual_delta,
        "delta": actual_delta,
        "baseline_mean": baseline_mean,
        "variant_mean": variant_mean,
        "bounds": [TRAIT_MIN_BOUND, TRAIT_MAX_BOUND],
        "rng_seed": rng_seed,
        "world_snapshot": copy.deepcopy(world_snapshot),
        "scene_prompt": scene_prompt,
        "constants_locked": {
            "rng_seed": True,
            "world_snapshot": True,
            "scene_prompt": True,
            "other_big_five_axes": True,
        },
        "baseline_core": baseline_core,
        "variant_core": variant_core,
        "counterfactual_core": variant_core,
        "baseline": baseline_arm,
        "variant": variant_arm,
        "variants": [baseline_arm, variant_arm],
    }


def _extract_run_text(run_obj: dict[str, Any]) -> str:
    parts: list[str] = []
    for k in (
        "text",
        "segment_text",
        "output_text",
        "summary",
        "dialogue",
        "action",
        "prompt_text",
    ):
        val = run_obj.get(k)
        if isinstance(val, str) and val.strip():
            parts.append(val.strip())
    return " ".join(parts)


def _trigram_cosine_distance(text_a: str, text_b: str) -> float:
    if not text_a and not text_b:
        return 0.0
    if not text_a or not text_b:
        return 1.0
    if text_a == text_b:
        return 0.0

    def _grams(s: str) -> Counter[str]:
        norm = " ".join(_WORD_RE.findall(s.lower()))
        if len(norm) < 3:
            return Counter([norm]) if norm else Counter()
        return Counter(norm[i : i + 3] for i in range(len(norm) - 2))

    ca = _grams(text_a)
    cb = _grams(text_b)
    if not ca or not cb:
        return 1.0
    dot = sum(float(ca[k] * cb[k]) for k in (ca.keys() & cb.keys()))
    na = math.sqrt(sum(float(v * v) for v in ca.values()))
    nb = math.sqrt(sum(float(v * v) for v in cb.values()))
    if na <= 1e-12 or nb <= 1e-12:
        return 1.0
    sim = max(0.0, min(1.0, dot / (na * nb)))
    return round(1.0 - sim, 6)


def _dict_l2_distance(dict_a: dict[str, Any], dict_b: dict[str, Any]) -> float:
    if not isinstance(dict_a, dict):
        dict_a = {}
    if not isinstance(dict_b, dict):
        dict_b = {}
    keys = set(dict_a.keys()) | set(dict_b.keys())
    sq_sum = 0.0
    for k in keys:
        va = dict_a.get(k, 0.0)
        vb = dict_b.get(k, 0.0)
        if isinstance(va, (int, float)) and isinstance(vb, (int, float)):
            diff = float(va) - float(vb)
            sq_sum += diff * diff
    return round(math.sqrt(sq_sum), 6)


def evaluate_counterfactual_divergence(
    baseline_run: dict,
    variant_run: dict,
) -> dict:
    """Measure behavioral, state, and lexical divergence between counterfactual arms."""
    if not isinstance(baseline_run, dict):
        baseline_run = {}
    if not isinstance(variant_run, dict):
        variant_run = {}

    seed_a = baseline_run.get("rng_seed")
    seed_b = variant_run.get("rng_seed")
    controls_valid = (seed_a == seed_b) if (seed_a is not None and seed_b is not None) else True

    text_a = _extract_run_text(baseline_run)
    text_b = _extract_run_text(variant_run)
    words_a = set(_WORD_RE.findall(text_a.lower()))
    words_b = set(_WORD_RE.findall(text_b.lower()))
    if not words_a and not words_b:
        lexical_jaccard_distance = 0.0
    elif not words_a or not words_b:
        lexical_jaccard_distance = 1.0
    else:
        union_len = len(words_a | words_b)
        inter_len = len(words_a & words_b)
        lexical_jaccard_distance = round(
            1.0 - (float(inter_len) / float(max(1, union_len))), 6
        )

    trigram_dist = _trigram_cosine_distance(text_a, text_b)

    state_a = baseline_run.get(
        "state_deltas", baseline_run.get("momentary_state", {})
    )
    state_b = variant_run.get(
        "state_deltas", variant_run.get("momentary_state", {})
    )
    state_l2 = _dict_l2_distance(state_a, state_b)

    rel_a = baseline_run.get("relationship_deltas", {})
    rel_b = variant_run.get("relationship_deltas", {})
    rel_l2 = _dict_l2_distance(rel_a, rel_b)

    dec_a = (
        baseline_run.get("decision")
        or baseline_run.get("chosen_action")
        or baseline_run.get("outcome")
    )
    dec_b = (
        variant_run.get("decision")
        or variant_run.get("chosen_action")
        or variant_run.get("outcome")
    )
    decision_changed = bool(dec_a != dec_b) if (dec_a is not None or dec_b is not None) else (lexical_jaccard_distance > 0.25)

    # Composite normalized divergence in [0.0, 1.0]
    norm_state = min(1.0, state_l2)
    norm_rel = min(1.0, rel_l2)
    text_div = 0.5 * lexical_jaccard_distance + 0.5 * trigram_dist
    decision_bonus = 0.20 if decision_changed else 0.0

    divergence_score = round(
        min(
            1.0,
            max(
                0.0,
                0.45 * text_div + 0.25 * norm_state + 0.10 * norm_rel + decision_bonus,
            ),
        ),
        6,
    )

    delta_val = abs(
        float(
            variant_run.get(
                "delta", variant_run.get("actual_delta", variant_run.get("requested_delta", 0.25))
            )
            or 0.25
        )
    )
    causal_sensitivity = round(divergence_score / max(0.05, delta_val), 6)

    return {
        "controls_valid": controls_valid,
        "divergence_score": divergence_score,
        "lexical_jaccard_distance": lexical_jaccard_distance,
        "trigram_cosine_distance": trigram_dist,
        "state_l2_divergence": state_l2,
        "relationship_l2_divergence": rel_l2,
        "decision_changed": decision_changed,
        "causal_sensitivity": causal_sensitivity,
        "trait_axis": variant_run.get("trait_axis", baseline_run.get("trait_axis", "openness")),
        "delta": variant_run.get("delta", variant_run.get("actual_delta", 0.0)),
    }
