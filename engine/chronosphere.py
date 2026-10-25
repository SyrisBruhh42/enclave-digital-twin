"""Deterministic Exoplanet Chronosphere Engine (WP-2).

Advances the 4-tick diurnal cycle (DAWN_SHIFT, MIDDAY_EXPEDITION, DUSK_CRAFT, THE_FEAST),
twin-sun orbital geometry (Blue Dwarf & Red Giant azimuths + magnetic polarity shear kp_exo),
and triple-moon ferrofluid tidal vectors using pure seeded HMAC-SHA256 math.
Zero LLM calls; 100% reproducible from (epoch_seed, tick_id).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hashlib
import hmac
import math
from typing import Any

DAY_PHASES: tuple[str, str, str, str] = (
    "DAWN_SHIFT",
    "MIDDAY_EXPEDITION",
    "DUSK_CRAFT",
    "THE_FEAST",
)

EPOCH_START_ISO = "2026-10-25T00:00:00Z"
HOURS_PER_TICK = 6


def _seeded_unit_float(epoch_seed: str, tick_id: int, channel: str) -> float:
    """Return a deterministic float in [0.0, 1.0) from HMAC-SHA256(epoch_seed, tick_id:channel)."""
    key = str(epoch_seed or "enclave_default_seed").encode("utf-8")
    msg = f"chronosphere:{int(tick_id)}:{channel}".encode("utf-8")
    digest = hmac.new(key, msg, hashlib.sha256).digest()
    uint64_val = int.from_bytes(digest[:8], byteorder="big", signed=False)
    return uint64_val / float(1 << 64)


def _compute_orbital_and_tidal_state(epoch_seed: str, tick_id: int) -> tuple[dict[str, float], dict[str, float]]:
    """Compute twin_suns_orbital_state and triple_moon_tidal_vector for (epoch_seed, tick_id)."""
    # Seeded epoch phase offsets (constant per epoch_seed)
    blue_offset = _seeded_unit_float(epoch_seed, 0, "blue_offset") * 360.0
    red_offset = _seeded_unit_float(epoch_seed, 0, "red_offset") * 360.0
    alpha_offset = _seeded_unit_float(epoch_seed, 0, "luna_alpha_offset")
    beta_offset = _seeded_unit_float(epoch_seed, 0, "luna_beta_offset")
    gamma_offset = _seeded_unit_float(epoch_seed, 0, "luna_gamma_offset")

    # Per-tick micro-nutation from SHA-256
    blue_jitter = (_seeded_unit_float(epoch_seed, tick_id, "blue_nutation") - 0.5) * 6.0
    red_jitter = (_seeded_unit_float(epoch_seed, tick_id, "red_nutation") - 0.5) * 4.5
    flux_harmonic = _seeded_unit_float(epoch_seed, tick_id, "kp_harmonic")

    # Primary Blue Dwarf advances ~90 deg per 6h tick; Secondary Red Giant counter-drifts ~33.75 deg per tick
    blue_azimuth = (blue_offset + (tick_id - 1) * 90.0 + blue_jitter) % 360.0
    red_azimuth = (red_offset - (tick_id - 1) * 33.75 + red_jitter) % 360.0

    # Angular shear between opposing solar magnetospheres drives kp_exo in [1.0, 9.0]
    angular_diff_rad = math.radians((blue_azimuth - red_azimuth) % 360.0)
    shear_alignment = 0.5 * (1.0 - math.cos(angular_diff_rad))  # Peak when suns are in 180-deg opposition
    raw_kp = 1.0 + 8.0 * (0.60 * shear_alignment + 0.40 * flux_harmonic)
    kp_exo = round(min(9.0, max(1.0, raw_kp)), 2)

    # Triple moon synodic phases in [0.0, 1.0]
    luna_alpha = round((alpha_offset + tick_id * 0.142857 + 0.02 * _seeded_unit_float(epoch_seed, tick_id, "a")) % 1.0, 4)
    luna_beta = round((beta_offset + tick_id * 0.083333 + 0.02 * _seeded_unit_float(epoch_seed, tick_id, "b")) % 1.0, 4)
    luna_gamma = round((gamma_offset + tick_id * 0.045455 + 0.02 * _seeded_unit_float(epoch_seed, tick_id, "g")) % 1.0, 4)

    # Ferrofluid sea surge combines lunar syzygy and magnetospheric kp_exo pull
    tidal_pull = (
        0.40 * (0.5 * (1.0 + math.cos(2.0 * math.pi * luna_alpha)))
        + 0.35 * (0.5 * (1.0 + math.cos(2.0 * math.pi * luna_beta)))
        + 0.25 * (0.5 * (1.0 + math.cos(2.0 * math.pi * luna_gamma)))
    )
    kp_norm = (kp_exo - 1.0) / 8.0
    ferrofluid_surge = round(min(1.0, max(0.0, 0.65 * tidal_pull + 0.35 * kp_norm)), 4)

    twin_suns = {
        "primary_blue_dwarf_azimuth_deg": round(blue_azimuth, 2),
        "secondary_red_giant_azimuth_deg": round(red_azimuth, 2),
        "magnetic_polarity_shear_kp_exo": kp_exo,
    }
    triple_moons = {
        "luna_alpha_phase": luna_alpha,
        "luna_beta_phase": luna_beta,
        "luna_gamma_phase": luna_gamma,
        "ferrofluid_sea_surge_index": ferrofluid_surge,
    }
    return twin_suns, triple_moons


def _parse_iso_utc(iso_str: str) -> datetime:
    """Parse an ISO-8601 UTC timestamp string into a timezone-aware UTC datetime."""
    cleaned = iso_str.strip()
    if cleaned.endswith("Z"):
        cleaned = cleaned[:-1] + "+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _format_iso_utc(dt: datetime) -> str:
    """Format a UTC datetime as YYYY-MM-DDTHH:MM:SSZ."""
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_chronosphere_for_tick(
    tick_id: int,
    epoch_seed: str = "enclave_epoch_2026",
    base_timestamp_iso: str | None = None,
) -> dict[str, Any]:
    """Construct the deterministic chronosphere state for an arbitrary tick_id >= 1."""
    if tick_id < 1:
        raise ValueError(f"tick_id must be >= 1, got {tick_id}")

    colony_sol = (tick_id - 1) // 4 + 1
    day_phase = DAY_PHASES[(tick_id - 1) % 4]

    if base_timestamp_iso is not None:
        world_timestamp_iso = base_timestamp_iso
    else:
        epoch_dt = _parse_iso_utc(EPOCH_START_ISO)
        current_dt = epoch_dt + timedelta(hours=HOURS_PER_TICK * (tick_id - 1))
        world_timestamp_iso = _format_iso_utc(current_dt)

    twin_suns, triple_moons = _compute_orbital_and_tidal_state(epoch_seed, tick_id)
    kp_exo = twin_suns["magnetic_polarity_shear_kp_exo"]

    return {
        "world_timestamp_iso": world_timestamp_iso,
        "tick_id": tick_id,
        "colony_sol": colony_sol,
        "day_phase": day_phase,
        "kp_exo": kp_exo,
        "twin_suns_orbital_state": twin_suns,
        "triple_moon_tidal_vector": triple_moons,
    }


def initial_chronosphere(epoch_seed: str = "enclave_epoch_2026") -> dict[str, Any]:
    """Return the initial tick 1 (Sol 1, DAWN_SHIFT) chronosphere snapshot."""
    return build_chronosphere_for_tick(tick_id=1, epoch_seed=epoch_seed)


def advance_tick(prev_snapshot: dict, epoch_seed: str) -> dict:
    """Deterministically advance the chronosphere by 1 tick (+6 hours).

    Supports both a flat chronosphere dictionary and a full world_state dictionary
    containing a nested 'chronosphere' key. Never mutates prev_snapshot.
    """
    if not prev_snapshot:
        return initial_chronosphere(epoch_seed=epoch_seed)

    nested_chrono = prev_snapshot.get("chronosphere")
    source = nested_chrono if isinstance(nested_chrono, dict) else prev_snapshot

    prev_tick_raw = source.get("tick_id", 0)
    prev_tick = int(prev_tick_raw) if prev_tick_raw is not None else 0

    if prev_tick < 1:
        return initial_chronosphere(epoch_seed=epoch_seed)

    next_tick = prev_tick + 1

    prev_ts = source.get("world_timestamp_iso")
    if isinstance(prev_ts, str) and prev_ts.strip():
        next_dt = _parse_iso_utc(prev_ts) + timedelta(hours=HOURS_PER_TICK)
        next_ts_iso = _format_iso_utc(next_dt)
    else:
        next_ts_iso = None

    return build_chronosphere_for_tick(
        tick_id=next_tick,
        epoch_seed=epoch_seed,
        base_timestamp_iso=next_ts_iso,
    )
