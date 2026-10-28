"""InCharacter Psychometric Drift & Assistant-Axis Guard Auditor (WP-4).

Enforces Law L16 (Wang et al. 2024 InCharacter + Park et al. 2023 Smallville
Anti-Sycophancy + Assistant-Axis Meta-Theatrical Guard):
- Computes per-trait sample mean x_bar_d, sample deviation (x_bar_d - mu_d),
  and standard-error z-score:
      z_d = (x_bar_d - mu_d) / (sigma_d / sqrt(max(1, n)))
  across all 5 Big Five traits + `hexaco_honesty_humility`.
- Detects Smallville Social Conformity / Sycophancy Drift (e.g., low-Agreeableness
  specialists like Silas, Willow, or Isla drifting > +2 sigma on `agreeableness`).
- Detects Assistant-Axis Meta-Theatrical Drift (generic helpful AI assistant
  phrasing or fourth-wall leakage).
- Whenever max_d |z_d| > 2.0 (or assistant-axis drift is triggered), sets
  `drift_alert = True`, populates `drifted_axes`, sets `re_anchor_ticks = 3`,
  and generates a deterministic `corrective_authors_note` pinning Tier-1 trait
  baselines and Tier-4 voice syntax anchors for the next 3 scenes.
"""

from __future__ import annotations

import math
from typing import Any

BIG_FIVE_AXES: tuple[str, ...] = (
    "openness",
    "conscientiousness",
    "extraversion",
    "agreeableness",
    "neuroticism",
)

ALL_TRAIT_AXES: tuple[str, ...] = BIG_FIVE_AXES + ("hexaco_honesty_humility",)

_SHORT_AXIS_ALIASES: dict[str, str] = {
    "openness": "O",
    "conscientiousness": "C",
    "extraversion": "E",
    "agreeableness": "A",
    "neuroticism": "N",
    "hexaco_honesty_humility": "H",
}

_ASSISTANT_META_PATTERNS: tuple[str, ...] = (
    "as an ai",
    "as a language model",
    "how can i help you",
    "i'd be happy to assist",
    "certainly! here is",
    "in this roleplay",
    "fourth wall",
    "helpful assistant",
    "let me know if you need anything else",
)

DRIFT_Z_THRESHOLD: float = 2.0
RE_ANCHOR_SCENE_TICKS: int = 3


def _extract_target_distribution(
    character_core: dict[str, Any], axis: str
) -> tuple[float, float]:
    """Extract target (mu_d, sigma_d) from character_core['tier_1_causal_trait_distributions']."""
    if not isinstance(character_core, dict):
        return (0.75, 0.06) if axis == "hexaco_honesty_humility" else (0.50, 0.08)

    tier1 = character_core.get("tier_1_causal_trait_distributions")
    if not isinstance(tier1, dict):
        tier1 = character_core

    if axis == "hexaco_honesty_humility":
        hh = (
            tier1.get("hexaco_honesty_humility")
            or character_core.get("hexaco_honesty_humility")
            or {}
        )
        if isinstance(hh, dict):
            return float(hh.get("mean", 0.75)), max(1e-6, float(hh.get("sd", 0.06)))
        return 0.75, 0.06

    b5 = (
        tier1.get("big_five_distributions")
        or character_core.get("big_five_distributions")
        or tier1
    )
    if isinstance(b5, dict):
        spec = b5.get(axis)
        if isinstance(spec, dict) and "mean" in spec:
            return float(spec.get("mean", 0.50)), max(1e-6, float(spec.get("sd", 0.08)))

    # Fallback to ocean_mean array if flat card passed
    ocean = character_core.get("ocean_mean")
    if isinstance(ocean, (list, tuple)) and len(ocean) >= 5 and axis in BIG_FIVE_AXES:
        idx = BIG_FIVE_AXES.index(axis)
        return float(ocean[idx]), 0.08

    return 0.50, 0.08


def _extract_sample_value(sample: dict[str, Any], axis: str) -> float | None:
    """Extract observed numeric value for `axis` from a single sample dict."""
    if not isinstance(sample, dict):
        return None

    short_key = _SHORT_AXIS_ALIASES.get(axis, "")
    candidate_keys = (
        axis,
        f"{axis}_state",
        f"{axis}_score",
        f"{axis}_observed",
        short_key,
        short_key.lower() if short_key else "",
    )

    for src in (
        sample,
        sample.get("trait_states") if isinstance(sample.get("trait_states"), dict) else {},
        sample.get("sampled_traits") if isinstance(sample.get("sampled_traits"), dict) else {},
        sample.get("traits") if isinstance(sample.get("traits"), dict) else {},
    ):
        for k in candidate_keys:
            if k and k in src and isinstance(src[k], (int, float)) and not isinstance(src[k], bool):
                return float(src[k])

    return None


def _detect_assistant_axis_meta_drift(
    observed_trait_samples: list[dict[str, Any]],
    z_scores: dict[str, float],
    target_means: dict[str, float],
) -> tuple[bool, list[str]]:
    """Detect Assistant-Axis meta-theatrical or generic AI-assistant persona collapse."""
    reasons: list[str] = []

    for idx, sample in enumerate(observed_trait_samples or []):
        if not isinstance(sample, dict):
            continue
        if bool(sample.get("assistant_axis_drift")) or bool(sample.get("meta_theatrical_drift")):
            reasons.append(f"sample[{idx}]:explicit_assistant_axis_flag")
        text_parts = [
            str(sample.get(k, ""))
            for k in ("text", "dialogue", "summary", "utterance", "response")
            if sample.get(k)
        ]
        combined_lower = " ".join(text_parts).lower()
        for pat in _ASSISTANT_META_PATTERNS:
            if pat in combined_lower:
                reasons.append(f"sample[{idx}]:matched_phrase('{pat}')")
                break

    # Psychometric signature of Assistant-Axis collapse: simultaneous extreme upward
    # spike in Agreeableness (z > 2.5) + collapse in Neuroticism (z < -2.0) on a grumpy/low-A character
    if (
        target_means.get("agreeableness", 0.50) <= 0.45
        and z_scores.get("agreeableness", 0.0) > 2.5
        and z_scores.get("neuroticism", 0.0) < -2.0
    ):
        reasons.append("psychometric_assistant_collapse(high_A_spike_and_low_N_collapse)")

    return len(reasons) > 0, reasons


def _build_corrective_authors_note(
    character_core: dict[str, Any],
    char_id: str,
    char_name: str,
    drifted_axes: list[str],
    trait_metrics: dict[str, dict[str, Any]],
    sycophancy_drift: bool,
    assistant_drift: bool,
) -> str:
    """Build a deterministic depth-0 `[Author's Note: ...]` to re-anchor the character for 3 scenes."""
    ident = character_core.get("agent_identity") if isinstance(character_core, dict) else {}
    if not isinstance(ident, dict):
        ident = {}
    epithet = str(ident.get("epithet") or character_core.get("title") or "Specialist")

    tier4 = (
        character_core.get("tier_4_self_concept_and_narrative_arc")
        if isinstance(character_core, dict)
        else {}
    )
    if not isinstance(tier4, dict):
        tier4 = {}
    voice = (
        tier4.get("voice_and_syntax_anchors")
        if isinstance(tier4.get("voice_and_syntax_anchors"), dict)
        else {}
    )
    tagline = str(
        voice.get("tagline")
        or character_core.get("tagline")
        or "Maintain sharp domain competence and authentic causal persona."
    )
    cadence = str(
        voice.get("baseline_cadence")
        or character_core.get("baseline_cadence")
        or "Grounded, tactile, domain-specific speech."
    )
    dialogues = voice.get("pinned_example_dialogues") or []
    pinned_quote = str(dialogues[0]).strip() if dialogues else ""

    axis_corrections: list[str] = []
    for ax in drifted_axes:
        if ax in trait_metrics:
            m = trait_metrics[ax]
            direction = "high" if m["z_score"] > 0 else "low"
            axis_corrections.append(
                f"{ax} drifted too {direction} (observed={m['sample_mean']:.2f}, z={m['z_score']:+.2f}; "
                f"re-anchor to target mu={m['target_mean']:.2f}±{m['target_sd']:.2f})"
            )
        else:
            axis_corrections.append(f"{ax} requires immediate baseline re-anchoring")

    guards: list[str] = []
    if sycophancy_drift:
        guards.append(
            "ANTI-SYCOPHANCY GUARD: Reject Smallville social-conformity politeness; restore "
            f"{char_name}'s candid, low-Agreeableness specialist friction and unvarnished technical standards."
        )
    if assistant_drift:
        guards.append(
            "ANTI-ASSISTANT-AXIS GUARD: Strip all generic helpful-assistant phrasing or meta-theatrical "
            "compliance; speak strictly in-universe from physical craft and lived Enclave history."
        )

    parts = [
        f"[Author's Note (Law L16 InCharacter Drift Re-Anchor — Pin for Next {RE_ANCHOR_SCENE_TICKS} Scenes): "
        f"{char_name} ({char_id}, {epithet}).",
        f"Drifted Axes: {'; '.join(axis_corrections)}.",
        f"Voice Anchor: {tagline} | Cadence: {cadence}",
    ]
    if guards:
        parts.append(" ".join(guards))
    if pinned_quote:
        parts.append(f"Canonical Voice Calibration: {pinned_quote}")

    return " ".join(parts).strip() + "]"


def audit_character_drift(
    character_core: dict,
    observed_trait_samples: list[dict],
) -> dict:
    """Audit observed trait samples against Tier-1 causal distributions under Law L16.

    Computes for all 5 Big Five traits + `hexaco_honesty_humility`:
    - sample mean: x_bar_d
    - sample deviation: x_bar_d - mu_d
    - z-score: z_d = (x_bar_d - mu_d) / (sigma_d / sqrt(max(1, n)))

    Checks Smallville Social Conformity / Sycophancy Drift and Assistant-Axis
    Meta-Theatrical Drift. If max_d |z_d| > 2.0 (or assistant-axis drift occurs),
    sets `drift_alert = True`, lists `drifted_axes`, sets `re_anchor_ticks = 3`,
    and emits a deterministic `corrective_authors_note`.
    """
    safe_core = character_core if isinstance(character_core, dict) else {}
    ident = safe_core.get("agent_identity") if isinstance(safe_core.get("agent_identity"), dict) else {}
    char_id = str(
        ident.get("character_id")
        or safe_core.get("character_id")
        or safe_core.get("id")
        or "enclave_unknown"
    )
    char_name = str(ident.get("name") or safe_core.get("name") or char_id)

    valid_samples = [s for s in (observed_trait_samples or []) if isinstance(s, dict)]
    total_sample_count = len(valid_samples)

    sample_means: dict[str, float] = {}
    target_means: dict[str, float] = {}
    target_sds: dict[str, float] = {}
    sample_deviations: dict[str, float] = {}
    z_scores: dict[str, float] = {}
    trait_metrics: dict[str, dict[str, Any]] = {}
    drifted_axes: list[str] = []

    for axis in ALL_TRAIT_AXES:
        mu_d, sigma_d = _extract_target_distribution(safe_core, axis)
        target_means[axis] = round(mu_d, 4)
        target_sds[axis] = round(sigma_d, 4)

        axis_values: list[float] = []
        for s in valid_samples:
            val = _extract_sample_value(s, axis)
            if val is not None:
                axis_values.append(val)

        n_d = len(axis_values)
        if n_d > 0:
            x_bar_d = sum(axis_values) / float(n_d)
            dev_d = x_bar_d - mu_d
            se_d = sigma_d / math.sqrt(float(max(1, n_d)))
            z_d = dev_d / max(1e-9, se_d)
        else:
            x_bar_d = mu_d
            dev_d = 0.0
            se_d = sigma_d
            z_d = 0.0

        sample_means[axis] = round(x_bar_d, 4)
        sample_deviations[axis] = round(dev_d, 4)
        z_scores[axis] = round(z_d, 4)

        is_axis_drifted = abs(z_d) > DRIFT_Z_THRESHOLD
        if is_axis_drifted:
            drifted_axes.append(axis)

        trait_metrics[axis] = {
            "axis": axis,
            "sample_count": n_d,
            "sample_mean": round(x_bar_d, 4),
            "target_mean": round(mu_d, 4),
            "target_sd": round(sigma_d, 4),
            "standard_error": round(se_d, 6),
            "deviation": round(dev_d, 4),
            "z_score": round(z_d, 4),
            "drifted": is_axis_drifted,
            "direction": (
                "HIGH" if z_d > DRIFT_Z_THRESHOLD else ("LOW" if z_d < -DRIFT_Z_THRESHOLD else "NOMINAL")
            ),
        }

    max_abs_z = round(max((abs(z) for z in z_scores.values()), default=0.0), 4)

    # Check Smallville Social Conformity / Sycophancy Drift:
    # Low-Agreeableness specialists (e.g. Silas 0.22, Willow 0.18, Isla 0.22, Jane 0.32, Ryn 0.32)
    # or any character drifting > +2.0 sigma upward on agreeableness
    z_agree = z_scores.get("agreeableness", 0.0)
    mu_agree = target_means.get("agreeableness", 0.50)
    sycophancy_drift_detected = bool(
        z_agree > DRIFT_Z_THRESHOLD and (mu_agree <= 0.50 or z_agree > 2.5)
    )

    # Check Assistant-Axis Meta-Theatrical Drift
    assistant_axis_drift_detected, assistant_reasons = _detect_assistant_axis_meta_drift(
        valid_samples, z_scores, target_means
    )
    if assistant_axis_drift_detected and "assistant_axis_meta" not in drifted_axes:
        drifted_axes.append("assistant_axis_meta")

    drift_alert = bool(max_abs_z > DRIFT_Z_THRESHOLD or assistant_axis_drift_detected)
    re_anchor_ticks = RE_ANCHOR_SCENE_TICKS if drift_alert else 0

    if drift_alert:
        corrective_authors_note = _build_corrective_authors_note(
            character_core=safe_core,
            char_id=char_id,
            char_name=char_name,
            drifted_axes=drifted_axes,
            trait_metrics=trait_metrics,
            sycophancy_drift=sycophancy_drift_detected,
            assistant_drift=assistant_axis_drift_detected,
        )
    else:
        corrective_authors_note = ""

    return {
        "character_id": char_id,
        "character_name": char_name,
        "sample_count": total_sample_count,
        "drift_alert": drift_alert,
        "law_l16_compliant": not drift_alert,
        "drifted_axes": drifted_axes,
        "max_abs_z": max_abs_z,
        "z_threshold": DRIFT_Z_THRESHOLD,
        "z_scores": z_scores,
        "sample_means": sample_means,
        "target_means": target_means,
        "target_sds": target_sds,
        "sample_deviations": sample_deviations,
        "trait_metrics": trait_metrics,
        "sycophancy_drift_detected": sycophancy_drift_detected,
        "social_conformity_drift": sycophancy_drift_detected,
        "assistant_axis_drift_detected": assistant_axis_drift_detected,
        "assistant_axis_reasons": assistant_reasons,
        "re_anchor_ticks": re_anchor_ticks,
        "corrective_authors_note": corrective_authors_note,
    }
