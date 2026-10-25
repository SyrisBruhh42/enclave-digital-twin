"""Deterministic Exoplanet Magneto-Meteorology Engine (WP-2).

Models the Enclave's 'Engine of Chaos': bifurcated valley/ridge thermal gradients,
magnetospheric flux index (kp_exo in [1.0, 9.0]), ferrofluid squalls, captured lightning
geode charge capacity, mycorrhizal spore luminescence, and PvE environmental hazards.
Zero LLM calls; 100% reproducible from (tick_id, colony_sol, day_phase, epoch_seed).
"""

from __future__ import annotations

import hashlib
import hmac
from typing import Any

from engine.chronosphere import build_chronosphere_for_tick

BIOME_CELLS: tuple[str, ...] = (
    "Enclave_Crater_Valley",
    "Basalt_Spire_Ridge",
    "Ferrofluid_Tidal_Basin",
    "Mycelial_Geode_Caverns",
    "Shattered_Magnetite_Steppe",
)

MICRO_CLIMATE_REGIMES: tuple[str, ...] = (
    "Bifurcated_Thermal_Shear",
    "Ferrofluid_Tidal_Squall",
    "Lightning_Geode_Supercharge",
    "Bioluminescent_Spore_Calm",
    "Magnetic_Null_Aurora",
)

HAZARD_BY_REGIME: dict[str, str] = {
    "Bifurcated_Thermal_Shear": "Resonant_Spore_Fog_Drift",
    "Ferrofluid_Tidal_Squall": "Ferrofluid_Riptide_Surge",
    "Lightning_Geode_Supercharge": "High_Altitude_Flux_Arc",
    "Bioluminescent_Spore_Calm": "Passive_Mycelial_Pollen_Haze",
    "Magnetic_Null_Aurora": "Compass_Inversion_Static_Shear",
}

PHASE_TEMP_OFFSET_C: dict[str, tuple[float, float]] = {
    "DAWN_SHIFT": (-2.4, -4.5),
    "MIDDAY_EXPEDITION": (4.8, 2.2),
    "DUSK_CRAFT": (1.1, -2.8),
    "THE_FEAST": (-1.5, -5.6),
}


def _weather_rng_float(
    epoch_seed: str,
    tick_id: int,
    colony_sol: int,
    day_phase: str,
    channel: str,
) -> float:
    """Return a deterministic float in [0.0, 1.0) using HMAC-SHA256."""
    key = str(epoch_seed or "enclave_default_seed").encode("utf-8")
    msg = f"weather:{int(tick_id)}:{int(colony_sol)}:{day_phase}:{channel}".encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    uint64_val = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return uint64_val / float(1 << 64)


def compute_exoplanet_weather(
    tick_id: int,
    colony_sol: int,
    day_phase: str,
    epoch_seed: str,
) -> dict:
    """Deterministically compute the exoplanet weather snapshot for a given tick and sol."""
    safe_tick = max(1, int(tick_id))
    safe_sol = max(1, int(colony_sol))
    normalized_phase = str(day_phase or "DAWN_SHIFT").strip().upper()

    # Align kp_exo with chronosphere orbital shear while incorporating sol/phase harmonics
    chrono = build_chronosphere_for_tick(tick_id=safe_tick, epoch_seed=epoch_seed)
    base_kp = float(chrono["kp_exo"])
    kp_perturbation = (_weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "kp_mod") - 0.5) * 0.8
    kp_exo = round(min(9.0, max(1.0, base_kp + kp_perturbation)), 2)

    # Select biome cell and micro-climate regime deterministically
    biome_u = _weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "biome")
    active_biome_cell = BIOME_CELLS[int(biome_u * len(BIOME_CELLS)) % len(BIOME_CELLS)]

    regime_u = _weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "regime")
    if kp_exo >= 7.2:
        micro_climate_regime = "Lightning_Geode_Supercharge"
    elif kp_exo <= 2.4:
        micro_climate_regime = "Bioluminescent_Spore_Calm"
    else:
        micro_climate_regime = MICRO_CLIMATE_REGIMES[int(regime_u * len(MICRO_CLIMATE_REGIMES)) % len(MICRO_CLIMATE_REGIMES)]

    # Valley floor vs. ridge crest temperatures (thermal bifurcation)
    valley_phase_delta, ridge_phase_delta = PHASE_TEMP_OFFSET_C.get(normalized_phase, (0.0, -3.0))
    valley_noise = (_weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "valley_temp") - 0.5) * 6.0
    ridge_noise = (_weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "ridge_temp") - 0.5) * 8.0

    valley_floor_temp_c = round(14.5 + valley_phase_delta + valley_noise, 1)
    ridge_crest_temp_c = round(min(valley_floor_temp_c - 8.5, -5.0 + ridge_phase_delta + ridge_noise), 1)

    # Barometric pressure (inverse relation with storm intensity)
    pressure_noise = (_weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "pressure") - 0.5) * 28.0
    kp_norm = (kp_exo - 1.0) / 8.0
    barometric_pressure_hpa = round(1018.0 - 24.0 * kp_norm + pressure_noise, 1)

    # Spore luminescence density in [0.0, 1.0] (peaks at Dusk & The Feast)
    nocturnal_boost = 0.22 if normalized_phase in ("DUSK_CRAFT", "THE_FEAST") else 0.0
    spore_raw = (
        0.35
        + nocturnal_boost
        + 0.40 * _weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "spore")
    )
    spore_luminescence_density = round(min(1.0, max(0.0, spore_raw)), 3)

    # Geode charge capacity percentage in [0.0, 100.0] driven by magnetospheric shear
    geode_noise = (_weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "geode") - 0.5) * 18.0
    geode_raw = 32.0 + 62.0 * kp_norm + geode_noise
    geode_charge_capacity_pct = round(min(100.0, max(0.0, geode_raw)), 1)

    # Weather severity in [0.0, 1.0]
    thermal_gradient_norm = min(1.0, max(0.0, (valley_floor_temp_c - ridge_crest_temp_c) / 35.0))
    severity_noise = _weather_rng_float(epoch_seed, safe_tick, safe_sol, normalized_phase, "severity")
    regime_severity_bias = {
        "Bioluminescent_Spore_Calm": -0.18,
        "Magnetic_Null_Aurora": -0.05,
        "Bifurcated_Thermal_Shear": 0.05,
        "Ferrofluid_Tidal_Squall": 0.16,
        "Lightning_Geode_Supercharge": 0.24,
    }.get(micro_climate_regime, 0.0)

    raw_severity = 0.45 * kp_norm + 0.25 * thermal_gradient_norm + 0.30 * severity_noise + regime_severity_bias
    if normalized_phase == "THE_FEAST":
        # Sanctuary hearth shelter dampens effective outdoor exposure during The Feast
        raw_severity *= 0.85
    weather_severity = round(min(1.0, max(0.0, raw_severity)), 3)

    active_environmental_hazard = HAZARD_BY_REGIME.get(
        micro_climate_regime,
        "Resonant_Spore_Fog_Drift",
    )

    return {
        "tick_id": safe_tick,
        "colony_sol": safe_sol,
        "day_phase": normalized_phase,
        "active_biome_cell": active_biome_cell,
        "micro_climate_regime": micro_climate_regime,
        "valley_floor_temp_c": valley_floor_temp_c,
        "ridge_crest_temp_c": ridge_crest_temp_c,
        "barometric_pressure_hpa": barometric_pressure_hpa,
        "spore_luminescence_density": spore_luminescence_density,
        "geode_charge_capacity_pct": geode_charge_capacity_pct,
        "weather_severity": weather_severity,
        "kp_exo": kp_exo,
        "magnetosphere": {"kp_exo": kp_exo},
        "active_environmental_hazard": active_environmental_hazard,
    }
