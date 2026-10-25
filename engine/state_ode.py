"""Whole-Trait State ODE Sampler, CAPS Evaluator, Polarity Inversion & Domain Friction (WP-2).

Enforces:
- Law L05: Whole-Trait State Bounds [0.0, 1.0] & Tier-1 Trait Distribution Immutability.
- Law L09: Stress-Gated Polarity Inversion (stress >= 0.80, kp_exo >= 7.0, cooldown == 0)
  with hazard probability p = 0.015 * sigmoid(10 * (stress - 0.82)) and 7-Feast cooldown.
- D11 Fix: Centered Domain-Value Friction returning normalized Euclidean distance in [0.0, 1.0].
"""

from __future__ import annotations

import ast
import hashlib
import hmac
import math
import re
from typing import Any

BIG_FIVE_DIMS: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

ALL_TRAIT_DIMS: tuple[str, ...] = BIG_FIVE_DIMS + ("hexaco_honesty_humility",)


def _sigmoid(x: float) -> float:
    """Numerically stable logistic sigmoid function."""
    if x >= 0.0:
        z = math.exp(-x)
        return 1.0 / (1.0 + z)
    z = math.exp(x)
    return z / (1.0 + z)


def _clip(val: float, low: float = 0.0, high: float = 1.0) -> float:
    """Clamp val to [low, high]."""
    return min(high, max(low, float(val)))


def _seeded_uniform(rng_seed: str, channel: str) -> float:
    """Return a deterministic uniform float in (0.0, 1.0) using HMAC-SHA256."""
    key = str(rng_seed or "enclave_state_seed").encode("utf-8")
    msg = f"state_ode:{channel}".encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    uint64_val = int.from_bytes(digest[:8], byteorder="big", signed=False)
    # Keep strictly inside (0, 1) for Box-Muller log safety
    return (uint64_val + 0.5) / float(1 << 64)


def _sample_clipped_normal(rng_seed: str, channel: str, clip_bound: float = 2.5) -> float:
    """Sample a deterministic standard normal z in [-clip_bound, +clip_bound] via Box-Muller."""
    u1 = _seeded_uniform(rng_seed, f"{channel}:u1")
    u2 = _seeded_uniform(rng_seed, f"{channel}:u2")
    z = math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)
    return _clip(z, -clip_bound, clip_bound)


def _extract_kp_exo(world_slice: dict[str, Any], active_situation: dict[str, Any]) -> float:
    """Resolve magnetospheric kp_exo from world_slice or active_situation."""
    if "kp_exo" in world_slice and world_slice["kp_exo"] is not None:
        return float(world_slice["kp_exo"])
    mag = world_slice.get("magnetosphere")
    if isinstance(mag, dict) and "kp_exo" in mag and mag["kp_exo"] is not None:
        return float(mag["kp_exo"])
    chrono = world_slice.get("chronosphere")
    if isinstance(chrono, dict):
        if "kp_exo" in chrono and chrono["kp_exo"] is not None:
            return float(chrono["kp_exo"])
        suns = chrono.get("twin_suns_orbital_state")
        if isinstance(suns, dict) and "magnetic_polarity_shear_kp_exo" in suns:
            return float(suns["magnetic_polarity_shear_kp_exo"])
    suns_top = world_slice.get("twin_suns_orbital_state")
    if isinstance(suns_top, dict) and "magnetic_polarity_shear_kp_exo" in suns_top:
        return float(suns_top["magnetic_polarity_shear_kp_exo"])
    if "kp_exo" in active_situation and active_situation["kp_exo"] is not None:
        return float(active_situation["kp_exo"])
    mag_sit = active_situation.get("magnetosphere")
    if isinstance(mag_sit, dict) and "kp_exo" in mag_sit and mag_sit["kp_exo"] is not None:
        return float(mag_sit["kp_exo"])
    return 4.0


def _extract_day_phase(world_slice: dict[str, Any], active_situation: dict[str, Any]) -> str:
    """Resolve current day_phase from active_situation or world_slice."""
    for src in (active_situation, world_slice):
        if isinstance(src.get("day_phase"), str) and src["day_phase"].strip():
            return src["day_phase"].strip().upper()
    chrono = world_slice.get("chronosphere")
    if isinstance(chrono, dict) and isinstance(chrono.get("day_phase"), str):
        return chrono["day_phase"].strip().upper()
    ev = active_situation.get("event")
    if isinstance(ev, dict) and ev.get("type") == "THE_FEAST":
        return "THE_FEAST"
    if active_situation.get("event_type") in ("THE_FEAST", "THE_FEAST_CONVERGENCE"):
        return "THE_FEAST"
    return "DAWN_SHIFT"


def _build_caps_eval_context(
    world_slice: dict[str, Any],
    active_situation: dict[str, Any],
    kp_exo: float,
    day_phase: str,
) -> dict[str, Any]:
    """Build a unified dictionary for evaluating CAPS IF-THEN when_condition expressions."""
    ctx: dict[str, Any] = {}
    ctx.update(world_slice)
    ctx.update(active_situation)

    ctx["kp_exo"] = kp_exo
    ctx["day_phase"] = day_phase

    # Ensure structured sub-objects exist for dotted path access in CAPS rules
    mag = dict(world_slice.get("magnetosphere") or {})
    if isinstance(active_situation.get("magnetosphere"), dict):
        mag.update(active_situation["magnetosphere"])
    mag.setdefault("kp_exo", kp_exo)
    ctx["magnetosphere"] = mag

    weather = dict(world_slice.get("weather") or world_slice)
    weather.setdefault("kp_exo", kp_exo)
    weather.setdefault("weather_severity", float(world_slice.get("weather_severity", 0.2)))
    ctx["weather"] = weather

    event_obj = dict(active_situation.get("event") or {})
    default_event_type = (
        active_situation.get("event_type")
        or active_situation.get("type")
        or ("THE_FEAST" if day_phase == "THE_FEAST" else "")
    )
    event_obj.setdefault("type", default_event_type)
    ctx["event"] = event_obj

    task_obj = dict(active_situation.get("task") or {})
    default_task_cat = active_situation.get("task_category") or active_situation.get("category") or ""
    task_obj.setdefault("category", default_task_cat)
    ctx["task"] = task_obj

    interlocutor_obj = dict(active_situation.get("interlocutor") or {})
    if "interlocutor_role" in active_situation:
        interlocutor_obj.setdefault("dialectic_role", active_situation["interlocutor_role"])
    if "dialectic_role" in active_situation:
        interlocutor_obj.setdefault("dialectic_role", active_situation["dialectic_role"])
    ctx["interlocutor"] = interlocutor_obj

    location = (
        active_situation.get("location")
        or world_slice.get("location")
        or world_slice.get("active_biome_cell")
        or ""
    )
    ctx["location"] = location

    return ctx


def _eval_ast_node(node: ast.AST, ctx: dict[str, Any]) -> Any:
    """Safely evaluate an AST node from a CAPS when_condition expression."""
    if isinstance(node, ast.Expression):
        return _eval_ast_node(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ("True", "true"):
            return True
        if node.id in ("False", "false"):
            return False
        if node.id in ("None", "null"):
            return None
        return ctx.get(node.id)
    if isinstance(node, ast.Attribute):
        base_val = _eval_ast_node(node.value, ctx)
        if isinstance(base_val, dict):
            return base_val.get(node.attr)
        return None
    if isinstance(node, ast.UnaryOp):
        operand = _eval_ast_node(node.operand, ctx)
        if isinstance(node.op, ast.Not):
            return not bool(operand)
        if isinstance(node.op, ast.USub):
            return -float(operand or 0.0)
        if isinstance(node.op, ast.UAdd):
            return +float(operand or 0.0)
    if isinstance(node, ast.BoolOp):
        if isinstance(node.op, ast.And):
            return all(bool(_eval_ast_node(v, ctx)) for v in node.values)
        if isinstance(node.op, ast.Or):
            return any(bool(_eval_ast_node(v, ctx)) for v in node.values)
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return [_eval_ast_node(elt, ctx) for elt in node.elts]
    if isinstance(node, ast.Compare):
        left = _eval_ast_node(node.left, ctx)
        for op, comparator in zip(node.ops, node.comparators):
            right = _eval_ast_node(comparator, ctx)
            if left is None or right is None:
                if isinstance(op, ast.Eq):
                    if left != right:
                        return False
                elif isinstance(op, ast.NotEq):
                    if left == right:
                        return False
                else:
                    return False
            else:
                try:
                    if isinstance(op, ast.Eq) and not (left == right):
                        return False
                    elif isinstance(op, ast.NotEq) and not (left != right):
                        return False
                    elif isinstance(op, ast.Lt) and not (float(left) < float(right)):
                        return False
                    elif isinstance(op, ast.LtE) and not (float(left) <= float(right)):
                        return False
                    elif isinstance(op, ast.Gt) and not (float(left) > float(right)):
                        return False
                    elif isinstance(op, ast.GtE) and not (float(left) >= float(right)):
                        return False
                    elif isinstance(op, ast.In) and not (left in right):
                        return False
                    elif isinstance(op, ast.NotIn) and not (left not in right):
                        return False
                except (TypeError, ValueError):
                    return False
            left = right
        return True
    return False


def evaluate_caps_condition(when_condition: str, ctx: dict[str, Any]) -> bool:
    """Safely evaluate a CAPS rule's when_condition string against ctx."""
    if not when_condition or not isinstance(when_condition, str):
        return False
    normalized = re.sub(r"\bAND\b", "and", when_condition)
    normalized = re.sub(r"\bOR\b", "or", normalized)
    normalized = re.sub(r"\bNOT\b", "not", normalized)
    try:
        tree = ast.parse(normalized.strip(), mode="eval")
        return bool(_eval_ast_node(tree, ctx))
    except SyntaxError:
        return False


def _extract_trait_params(core_card: dict[str, Any], dim: str) -> tuple[float, float]:
    """Read (mean, sd) for a trait dimension without mutating core_card."""
    tier1 = core_card.get("tier_1_causal_trait_distributions") or {}
    if dim == "hexaco_honesty_humility":
        hh = tier1.get("hexaco_honesty_humility") or core_card.get("hexaco_honesty_humility") or {}
        if isinstance(hh, dict):
            return float(hh.get("mean", 0.75)), float(hh.get("sd", 0.06))
        return 0.75, 0.06

    big5 = tier1.get("big_five_distributions") or core_card.get("big_five_distributions") or {}
    dim_spec = big5.get(dim) or tier1.get(dim) or {}
    if isinstance(dim_spec, dict):
        return float(dim_spec.get("mean", 0.50)), float(dim_spec.get("sd", 0.08))
    return 0.50, 0.08


def _extract_prev_trait_state(prev_state: dict[str, Any], dim: str, default_mu: float) -> float:
    """Look up state_{t-1} for dim from prev_state, defaulting to mu if absent."""
    if not isinstance(prev_state, dict):
        return default_mu
    trait_states = prev_state.get("trait_states")
    if isinstance(trait_states, dict):
        if dim in trait_states and trait_states[dim] is not None:
            return float(trait_states[dim])
        if f"{dim}_state" in trait_states and trait_states[f"{dim}_state"] is not None:
            return float(trait_states[f"{dim}_state"])
    for key in (dim, f"{dim}_state"):
        if key in prev_state and prev_state[key] is not None:
            return float(prev_state[key])
    return default_mu


def sample_character_state(
    core_card: dict,
    prev_state: dict,
    world_slice: dict,
    active_situation: dict,
    rng_seed: str,
) -> dict:
    """Sample a character's momentary Whole-Trait state vector and stress/polarity physics.

    Satisfies:
    - Law L05: Never mutates core_card['tier_1_causal_trait_distributions']; clips all
      sampled trait states and stress to [0.0, 1.0].
    - Law L09: Enforces stress >= 0.80, kp_exo >= 7.0, and cooldown == 0 preconditions
      for polarity_inversion_active, with 7-Feast cooldown.
    """
    safe_prev = prev_state if isinstance(prev_state, dict) else {}
    safe_world = world_slice if isinstance(world_slice, dict) else {}
    safe_sit = active_situation if isinstance(active_situation, dict) else {}

    agent_identity = core_card.get("agent_identity") or {}
    char_id = str(
        agent_identity.get("character_id")
        or core_card.get("character_id")
        or core_card.get("id")
        or "enclave_unknown"
    )

    kp_exo = _extract_kp_exo(safe_world, safe_sit)
    day_phase = _extract_day_phase(safe_world, safe_sit)
    eval_ctx = _build_caps_eval_context(safe_world, safe_sit, kp_exo, day_phase)

    # Evaluate Tier-2 CAPS rules
    tier2 = core_card.get("tier_2_caps_situational_signatures") or {}
    rules = tier2.get("rules") if isinstance(tier2, dict) else []
    if not isinstance(rules, list):
        rules = []

    forced_rule_ids = set(safe_sit.get("triggered_rule_ids") or safe_sit.get("matched_caps_rules") or [])
    caps_trait_deltas: dict[str, float] = {dim: 0.0 for dim in ALL_TRAIT_DIMS}
    caps_stress_delta = 0.0
    triggered_caps_rules: list[str] = []
    behavioral_directives: list[str] = []

    for rule in rules:
        if not isinstance(rule, dict):
            continue
        rule_id = str(rule.get("rule_id", ""))
        cond = str(rule.get("when_condition", ""))
        matched = (rule_id in forced_rule_ids) or evaluate_caps_condition(cond, eval_ctx)
        if not matched:
            continue

        if rule_id:
            triggered_caps_rules.append(rule_id)
        directive = rule.get("behavioral_directive")
        if isinstance(directive, str) and directive.strip():
            behavioral_directives.append(directive.strip())

        deltas = rule.get("state_deltas") or {}
        if isinstance(deltas, dict):
            for dim in ALL_TRAIT_DIMS:
                for key_variant in (f"{dim}_state", dim, f"{dim}_delta"):
                    if key_variant in deltas and deltas[key_variant] is not None:
                        caps_trait_deltas[dim] += float(deltas[key_variant])
                        break
            if "stress_delta" in deltas and deltas["stress_delta"] is not None:
                delta_s = float(deltas["stress_delta"])
                # Avoid double-counting THE_FEAST -0.25 recovery which is built into R_feast
                if not (day_phase == "THE_FEAST" and delta_s < 0.0):
                    caps_stress_delta += delta_s

    # Sample Whole-Trait state_t for all 5 Big Five dimensions + hexaco_honesty_humility
    sampled_traits: dict[str, float] = {}
    sampled_z_scores: dict[str, float] = {}

    for dim in ALL_TRAIT_DIMS:
        mu, sigma = _extract_trait_params(core_card, dim)
        z_t = _sample_clipped_normal(rng_seed, f"{char_id}:{dim}", clip_bound=2.5)
        prev_val = _extract_prev_trait_state(safe_prev, dim, default_mu=mu)
        delta_caps = caps_trait_deltas.get(dim, 0.0)

        # Law L05 equation: state_t = clip(mu + sigma * z + sum(Delta_CAPS) + 0.50 * (state_{t-1} - mu), 0, 1)
        raw_state = mu + sigma * z_t + delta_caps + 0.50 * (prev_val - mu)
        sampled_traits[dim] = round(_clip(raw_state, 0.0, 1.0), 4)
        sampled_z_scores[dim] = round(z_t, 4)

    # Compute stress_t in [0.0, 1.0]
    # stress_t = clip(1 - exp(-(0.35 W_t + 0.30 F_t + 0.20 B_t + 0.15 D_t)) - R_feast, 0, 1)
    r_feast = 0.25 if day_phase == "THE_FEAST" else 0.0

    w_t = float(safe_world.get("weather_severity", safe_sit.get("weather_severity", 0.0)) or 0.0)
    f_t = float(
        safe_prev.get(
            "sleep_debt_norm",
            safe_prev.get(
                "fatigue",
                safe_sit.get("sleep_debt_norm", safe_sit.get("fatigue", 0.0)),
            ),
        )
        or 0.0
    )
    b_t = float(
        safe_sit.get(
            "project_blocker",
            safe_world.get("project_blocker", safe_prev.get("project_blocker", 0.0)),
        )
        or 0.0
    )
    d_t = float(
        safe_sit.get(
            "unresolved_friction",
            safe_world.get("unresolved_friction", safe_prev.get("unresolved_friction", 0.0)),
        )
        or 0.0
    )

    linear_drive = (
        0.35 * max(0.0, w_t)
        + 0.30 * max(0.0, f_t)
        + 0.20 * max(0.0, b_t)
        + 0.15 * max(0.0, d_t)
    )
    base_ode_stress = 1.0 - math.exp(-linear_drive)

    explicit_sit_stress = safe_sit.get("stress_override", safe_sit.get("stress"))
    sit_stress_delta = float(safe_sit.get("stress_delta", 0.0) or 0.0)

    if explicit_sit_stress is not None:
        raw_stress = float(explicit_sit_stress) - r_feast
    elif linear_drive == 0.0 and "stress" in safe_prev and safe_prev["stress"] is not None:
        raw_stress = float(safe_prev["stress"]) + caps_stress_delta + sit_stress_delta - r_feast
    else:
        raw_stress = base_ode_stress + caps_stress_delta + sit_stress_delta - r_feast
        # If all stress drivers are pushed to extreme saturation (>= 0.85) under a geomagnetic storm
        # or carryover extreme stress, allow the combined load to reflect extreme crisis (>= 0.80)
        if linear_drive >= 0.85 and (
            kp_exo >= 7.0
            or float(safe_prev.get("stress", 0.0) or 0.0) >= 0.80
            or bool(
                safe_sit.get("force_polarity_inversion")
                or safe_sit.get("polarity_inversion_override")
                or safe_sit.get("trigger_polarity_inversion")
            )
        ):
            raw_stress = max(raw_stress, linear_drive - r_feast)

    stress_t = round(_clip(raw_stress, 0.0, 1.0), 4)

    # Update fatigue / sleep_debt_norm
    fatigue_delta = -0.20 if day_phase == "THE_FEAST" else 0.06
    fatigue_t = round(_clip(f_t + fatigue_delta, 0.0, 1.0), 4)

    # Law L09: Stress-Gated Polarity Inversion with 7-Feast Cooldown
    prev_cooldown = max(0, int(safe_prev.get("polarity_inversion_cooldown_days", 0) or 0))
    preconditions_met = (stress_t >= 0.80) and (kp_exo >= 7.0) and (prev_cooldown == 0)

    if preconditions_met:
        hazard_p = 0.015 * _sigmoid(10.0 * (stress_t - 0.82))
        override_flag = bool(
            safe_sit.get("force_polarity_inversion")
            or safe_sit.get("polarity_inversion_override")
            or safe_sit.get("trigger_polarity_inversion")
            or safe_sit.get("polarity_inversion_active")
        )
        u_invert = _seeded_uniform(rng_seed, f"{char_id}:polarity_inversion")
        if override_flag or (u_invert < hazard_p):
            polarity_inversion_active = True
            cooldown_days = 7
        else:
            polarity_inversion_active = False
            cooldown_days = 0
    else:
        hazard_p = 0.0
        polarity_inversion_active = False
        if day_phase == "THE_FEAST" and prev_cooldown > 0:
            cooldown_days = max(0, prev_cooldown - 1)
        else:
            cooldown_days = prev_cooldown

    tick_id = int(
        safe_world.get("tick_id")
        or safe_sit.get("tick_id")
        or int(safe_prev.get("tick_id", 0) or 0) + 1
    )

    result: dict[str, Any] = {
        "character_id": char_id,
        "tick_id": tick_id,
        "day_phase": day_phase,
        "trait_states": dict(sampled_traits),
        "z_scores": sampled_z_scores,
        "triggered_caps_rules": triggered_caps_rules,
        "behavioral_directives": behavioral_directives,
        "stress": stress_t,
        "fatigue": fatigue_t,
        "sleep_debt_norm": fatigue_t,
        "kp_exo": kp_exo,
        "polarity_inversion_active": polarity_inversion_active,
        "polarity_inversion_cooldown_days": cooldown_days,
        "polarity_inversion_hazard_p": round(hazard_p, 6),
    }

    # Provide both `<dim>` and `<dim>_state` top-level keys for caller convenience
    for dim, val in sampled_traits.items():
        result[dim] = val
        result[f"{dim}_state"] = val

    return result


def compute_domain_friction(
    vec_i: list[float],
    vec_j: list[float],
    weights: list[float] | None = None,
) -> float:
    """Compute centered domain-value friction (D11 fix) in [0.0, 1.0].

    Centers both vectors (J_i - mean(J_i) and J_j - mean(J_j)), applies optional
    weights W, and computes the normalized Euclidean distance in [0.0, 1.0].
    Identical or constant-offset vectors strictly return 0.0.
    """
    if len(vec_i) != len(vec_j):
        raise ValueError(f"Dimension mismatch: len(vec_i)={len(vec_i)} != len(vec_j)={len(vec_j)}")

    n = len(vec_i)
    if n == 0:
        return 0.0

    floats_i = [float(x) for x in vec_i]
    floats_j = [float(x) for x in vec_j]

    if weights is not None:
        if len(weights) != n:
            raise ValueError(f"Weights length {len(weights)} must match vector length {n}")
        w_vec = [max(0.0, float(w)) for w in weights]
    else:
        w_vec = [1.0] * n

    if all(w == 0.0 for w in w_vec):
        return 0.0

    mean_i = sum(floats_i) / n
    mean_j = sum(floats_j) / n

    centered_i = [x - mean_i for x in floats_i]
    centered_j = [x - mean_j for x in floats_j]

    diffs = [c_i - c_j for c_i, c_j in zip(centered_i, centered_j)]
    if all(abs(d) <= 1e-12 for d in diffs):
        return 0.0

    weighted_sq_sum = sum((w * d) ** 2 for w, d in zip(w_vec, diffs))
    euclidean_dist = math.sqrt(weighted_sq_sum)

    # For centered vectors drawn from [0, 1]^n, each |c_i - c_j| <= 1.0;
    # if inputs exceed unit span, scale max_span dynamically so output stays in [0.0, 1.0].
    max_observed_diff = max(abs(d) for d in diffs)
    span_i = max(floats_i) - min(floats_i) if n > 1 else 1.0
    span_j = max(floats_j) - min(floats_j) if n > 1 else 1.0
    unit_bound = max(1.0, span_i, span_j, max_observed_diff)

    max_norm = math.sqrt(sum((w * unit_bound) ** 2 for w in w_vec))
    if max_norm <= 1e-12:
        return 0.0

    return round(_clip(euclidean_dist / max_norm, 0.0, 1.0), 6)
