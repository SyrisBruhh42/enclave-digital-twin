"""
Sovereign March x Enclave Digital Twin Unified Bridge Engine (U3 Capsule).

Merges the 2D Tactical Hero Tower Defense & Infinite Class Progression mechanics
of `SyrisBruhh42/LFS-Tower-Defense-Experiment` (Sovereign March) with the 16+1
Psychometric Colony, 3D Infinite Corridor, and 6-Pillar Calibrated Living Atlas
of `SyrisBruhh42/LFS-Enclave-experiment` and `enclave-digital-twin`.

Key Unified Systems:
1. 4-Stage Epoch Progression Gate ("Beat the Level to Progress to the Next Style System"):
   - STAGE_1_LIVING_ATLAS -> STAGE_2_CORRIDOR_GATE -> STAGE_3_TACTICAL_DEFENSE -> STAGE_4_COLONY_FEAST
2. Event-Seeded Deterministic 16x10 Procedural Map Generator (`generate_event_seeded_battlefield`).
3. Hybrid 16+1 Enclave Specialist Hero Towers with infinite Class Stat Growth across 20 Classes,
   9 Civilization Veterancy Promotions, Movement Speed Decay, and Dyadic Partner Resonance.
4. 10x6 D&D/Wesnoth Attack vs. Armor Matrix & 8 Dual-Element Catalyst Reactions with
   1-click Terminology Mode toggle (`kepler_exoplanet` vs. `classic_fantasy`).
5. Battle Telemetry -> Calibrated Living Atlas Chapter & Nightly Grand Feast Compiler
   verified by `NarrativeCalibrationEngine` (Stop-Slop >= 35/50).
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from engine.narrative_calibration_engine import (
    CHARACTER_SPINES,
    run_three_pass_de_ai_calibration,
    score_stop_slop_5d,
)

# ============================================================================
# 1. 20 HERO CLASSES, INFINITE STAT GROWTH & TERMINOLOGY TOGGLE
# ============================================================================

HERO_CLASS_REGISTRY: Dict[str, Dict[str, Any]] = {
    # Tier 1 Base Disciplines
    "swordplay": {
        "tier": 1,
        "classic_name": "Swordplay",
        "kepler_name": "Vibro-Halberd Vanguard",
        "damage_type": "slashing",
        "cost": 100,
        "base_power": 24.0,
        "base_speed": 62.0,
        "base_range": 2.1,
        "growth": {"power": 4.2, "speed": 1.8, "range": 0.04, "mastery": 1.5},
        "prereqs": {},
    },
    "archery": {
        "tier": 1,
        "classic_name": "Archery",
        "kepler_name": "Rail-Bow Marksman",
        "damage_type": "piercing",
        "cost": 110,
        "base_power": 19.0,
        "base_speed": 76.0,
        "base_range": 3.8,
        "growth": {"power": 2.6, "speed": 3.6, "range": 0.08, "mastery": 1.4},
        "prereqs": {},
    },
    "pyromancy": {
        "tier": 1,
        "classic_name": "Pyromancy",
        "kepler_name": "Plasma Thermicist",
        "damage_type": "fire",
        "cost": 125,
        "base_power": 28.0,
        "base_speed": 54.0,
        "base_range": 3.1,
        "growth": {"power": 4.8, "speed": 1.4, "range": 0.05, "mastery": 2.4},
        "prereqs": {},
    },
    "cryomancy": {
        "tier": 1,
        "classic_name": "Cryomancy",
        "kepler_name": "Cryo-Stasis Splicer",
        "damage_type": "cold",
        "cost": 120,
        "base_power": 20.0,
        "base_speed": 58.0,
        "base_range": 3.2,
        "growth": {"power": 3.0, "speed": 1.9, "range": 0.06, "mastery": 2.6},
        "prereqs": {},
    },
    "alchemy": {
        "tier": 1,
        "classic_name": "Alchemy",
        "kepler_name": "Xenobiotic Alkahest",
        "damage_type": "acid",
        "cost": 120,
        "base_power": 18.0,
        "base_speed": 64.0,
        "base_range": 3.0,
        "growth": {"power": 2.8, "speed": 2.2, "range": 0.05, "mastery": 3.0},
        "prereqs": {},
    },
    # Tier 2 Specialist & Synergistic Hybrid Disciplines
    "warhammer": {
        "tier": 2,
        "classic_name": "Warhammer",
        "kepler_name": "Seismic Pile-Driver",
        "damage_type": "bludgeoning",
        "cost": 165,
        "base_power": 42.0,
        "base_speed": 48.0,
        "base_range": 2.2,
        "growth": {"power": 6.4, "speed": 1.1, "range": 0.03, "mastery": 2.0},
        "prereqs": {"swordplay": 2},
    },
    "crossbow": {
        "tier": 2,
        "classic_name": "Crossbow",
        "kepler_name": "Gauss Arbalest",
        "damage_type": "piercing",
        "cost": 160,
        "base_power": 36.0,
        "base_speed": 64.0,
        "base_range": 4.2,
        "growth": {"power": 4.9, "speed": 2.4, "range": 0.09, "mastery": 1.8},
        "prereqs": {"archery": 2},
    },
    "electromancy": {
        "tier": 2,
        "classic_name": "Electromancy",
        "kepler_name": "Magneto-Arc Conduit",
        "damage_type": "lightning",
        "cost": 175,
        "base_power": 32.0,
        "base_speed": 72.0,
        "base_range": 3.4,
        "growth": {"power": 4.4, "speed": 3.2, "range": 0.06, "mastery": 2.8},
        "prereqs": {"pyromancy": 2},
    },
    "chronomancy": {
        "tier": 2,
        "classic_name": "Chronomancy",
        "kepler_name": "Schumann Phase-Shifter",
        "damage_type": "force",
        "cost": 180,
        "base_power": 29.0,
        "base_speed": 78.0,
        "base_range": 3.6,
        "growth": {"power": 3.8, "speed": 3.8, "range": 0.07, "mastery": 3.2},
        "prereqs": {"cryomancy": 2},
    },
    "spellblade": {
        "tier": 2,
        "classic_name": "Spellblade",
        "kepler_name": "Thermite Saboteur",
        "damage_type": "fire",
        "cost": 185,
        "base_power": 38.0,
        "base_speed": 68.0,
        "base_range": 2.6,
        "growth": {"power": 5.2, "speed": 2.5, "range": 0.05, "mastery": 2.7},
        "prereqs": {"swordplay": 2, "pyromancy": 2},
    },
    "frostbow": {
        "tier": 2,
        "classic_name": "Frostbow",
        "kepler_name": "Permafrost Ballista",
        "damage_type": "cold",
        "cost": 180,
        "base_power": 31.0,
        "base_speed": 74.0,
        "base_range": 4.0,
        "growth": {"power": 3.9, "speed": 3.1, "range": 0.08, "mastery": 2.6},
        "prereqs": {"archery": 2, "cryomancy": 2},
    },
    "venomcraft": {
        "tier": 2,
        "classic_name": "Venomcraft",
        "kepler_name": "Mycelial Toxin-Weaver",
        "damage_type": "poison",
        "cost": 175,
        "base_power": 27.0,
        "base_speed": 75.0,
        "base_range": 3.7,
        "growth": {"power": 3.5, "speed": 3.0, "range": 0.07, "mastery": 3.4},
        "prereqs": {"archery": 2, "alchemy": 2},
    },
    "geomancy": {
        "tier": 2,
        "classic_name": "Geomancy",
        "kepler_name": "Basalt Tectonist",
        "damage_type": "bludgeoning",
        "cost": 185,
        "base_power": 40.0,
        "base_speed": 56.0,
        "base_range": 3.2,
        "growth": {"power": 5.8, "speed": 1.6, "range": 0.05, "mastery": 2.8},
        "prereqs": {"swordplay": 2, "cryomancy": 2},
    },
    "gunpowder": {
        "tier": 2,
        "classic_name": "Gunpowder",
        "kepler_name": "Ferro-Mortar Siegeworks",
        "damage_type": "bludgeoning",
        "cost": 190,
        "base_power": 44.0,
        "base_speed": 52.0,
        "base_range": 4.1,
        "growth": {"power": 6.1, "speed": 1.5, "range": 0.08, "mastery": 2.9},
        "prereqs": {"pyromancy": 2, "alchemy": 2},
    },
    "runesmith": {
        "tier": 2,
        "classic_name": "Runesmith",
        "kepler_name": "High-Entropy Anvil",
        "damage_type": "lightning",
        "cost": 185,
        "base_power": 37.0,
        "base_speed": 62.0,
        "base_range": 2.9,
        "growth": {"power": 5.0, "speed": 2.1, "range": 0.05, "mastery": 3.1},
        "prereqs": {"swordplay": 2, "alchemy": 2},
    },
    # Tier 3 Master Classes
    "arcane_archer": {
        "tier": 3,
        "classic_name": "Arcane Archer",
        "kepler_name": "Phase-Horizon Sharpshooter",
        "damage_type": "force",
        "cost": 260,
        "base_power": 52.0,
        "base_speed": 86.0,
        "base_range": 4.8,
        "growth": {"power": 6.8, "speed": 4.2, "range": 0.11, "mastery": 3.6},
        "prereqs": {"crossbow": 3, "frostbow": 2},
    },
    "grand_inquisitor": {
        "tier": 3,
        "classic_name": "Grand Inquisitor",
        "kepler_name": "Solar-Flare Aegis Marshal",
        "damage_type": "radiant",
        "cost": 270,
        "base_power": 58.0,
        "base_speed": 70.0,
        "base_range": 3.3,
        "growth": {"power": 7.5, "speed": 2.8, "range": 0.06, "mastery": 3.8},
        "prereqs": {"warhammer": 3, "spellblade": 2},
    },
    "archmage": {
        "tier": 3,
        "classic_name": "Archmage",
        "kepler_name": "Twin-Sun Cataclysm Savant",
        "damage_type": "lightning",
        "cost": 280,
        "base_power": 62.0,
        "base_speed": 74.0,
        "base_range": 4.0,
        "growth": {"power": 8.0, "speed": 3.0, "range": 0.08, "mastery": 4.4},
        "prereqs": {"electromancy": 3, "pyromancy": 3},
    },
    "master_alchemist": {
        "tier": 3,
        "classic_name": "Master Alchemist",
        "kepler_name": "Bioluminescent Apex Chemist",
        "damage_type": "acid",
        "cost": 265,
        "base_power": 49.0,
        "base_speed": 78.0,
        "base_range": 3.9,
        "growth": {"power": 6.2, "speed": 3.4, "range": 0.07, "mastery": 4.6},
        "prereqs": {"venomcraft": 3, "gunpowder": 2},
    },
    "chronosavant": {
        "tier": 3,
        "classic_name": "Chronosavant",
        "kepler_name": "Singularity Chronometer",
        "damage_type": "force",
        "cost": 275,
        "base_power": 54.0,
        "base_speed": 88.0,
        "base_range": 4.2,
        "growth": {"power": 6.6, "speed": 4.5, "range": 0.09, "mastery": 4.5},
        "prereqs": {"chronomancy": 3, "geomancy": 2},
    },
}

# ============================================================================
# 2. 10x6 ATTACK VS. ARMOR MATRIX & 8 DUAL-ELEMENT CATALYST REACTIONS
# ============================================================================

ATTACK_VS_ARMOR_MATRIX: Dict[str, Dict[str, float]] = {
    "slashing": {
        "unarmored": 1.45,
        "leather": 1.25,
        "chainmail": 0.80,
        "heavy_plate": 0.50,
        "natural_carapace": 0.85,
        "arcane_ward": 0.90,
    },
    "piercing": {
        "unarmored": 1.20,
        "leather": 1.45,
        "chainmail": 1.15,
        "heavy_plate": 0.65,
        "natural_carapace": 1.25,
        "arcane_ward": 0.85,
    },
    "bludgeoning": {
        "unarmored": 0.95,
        "leather": 1.00,
        "chainmail": 1.30,
        "heavy_plate": 1.55,
        "natural_carapace": 1.45,
        "arcane_ward": 0.90,
    },
    "fire": {
        "unarmored": 1.35,
        "leather": 1.25,
        "chainmail": 1.05,
        "heavy_plate": 0.90,
        "natural_carapace": 1.30,
        "arcane_ward": 0.80,
    },
    "cold": {
        "unarmored": 1.15,
        "leather": 1.10,
        "chainmail": 1.10,
        "heavy_plate": 1.25,
        "natural_carapace": 1.35,
        "arcane_ward": 0.85,
    },
    "lightning": {
        "unarmored": 1.10,
        "leather": 0.90,
        "chainmail": 1.50,
        "heavy_plate": 1.45,
        "natural_carapace": 0.95,
        "arcane_ward": 1.15,
    },
    "acid": {
        "unarmored": 1.05,
        "leather": 1.15,
        "chainmail": 1.35,
        "heavy_plate": 1.50,
        "natural_carapace": 1.40,
        "arcane_ward": 0.75,
    },
    "poison": {
        "unarmored": 1.50,
        "leather": 1.35,
        "chainmail": 0.95,
        "heavy_plate": 0.55,
        "natural_carapace": 1.15,
        "arcane_ward": 0.70,
    },
    "force": {
        "unarmored": 1.05,
        "leather": 1.05,
        "chainmail": 1.10,
        "heavy_plate": 1.15,
        "natural_carapace": 1.10,
        "arcane_ward": 1.60,
    },
    "radiant": {
        "unarmored": 1.25,
        "leather": 1.15,
        "chainmail": 1.15,
        "heavy_plate": 1.20,
        "natural_carapace": 1.15,
        "arcane_ward": 1.50,
    },
}

CATALYST_REACTIONS: Dict[str, Dict[str, Any]] = {
    "slag_detonation": {
        "primer_status": "corroded",
        "detonator_element": "fire",
        "name": "Alchemical Ignition",
        "damage_multiplier": 2.25,
    },
    "brittle_fracture": {
        "primer_status": "frozen",
        "detonator_element": "bludgeoning",
        "name": "Cryo-Shatter Crush",
        "damage_multiplier": 2.60,
    },
    "superconductor_surge": {
        "primer_status": "chilled",
        "detonator_element": "lightning",
        "name": "Superconductor Arc",
        "damage_multiplier": 1.95,
    },
    "thermal_shockwave": {
        "primer_status": "burning",
        "detonator_element": "cold",
        "name": "Thermal Shock",
        "damage_multiplier": 2.05,
    },
    "blight_miasma": {
        "primer_status": "poisoned",
        "detonator_element": "acid",
        "name": "Neuro-Blight Cloud",
        "damage_multiplier": 2.10,
    },
    "sanctified_purge": {
        "primer_status": "sundered",
        "detonator_element": "radiant",
        "name": "Solar Judgment",
        "damage_multiplier": 2.30,
    },
    "temporal_singularity": {
        "primer_status": "time_sheared",
        "detonator_element": "force",
        "name": "Schumann Singularity",
        "damage_multiplier": 2.40,
    },
    "molten_shrapnel": {
        "primer_status": "burning",
        "detonator_element": "piercing",
        "name": "Thermite Shrapnel",
        "damage_multiplier": 1.85,
    },
}


# ============================================================================
# 3. HYBRID 16+1 ENCLAVE SPECIALIST TOWER INSTANCE & STAT GROWTH
# ============================================================================

@dataclass
class EnclaveTowerUnit:
    unit_id: str
    specialist_id: str
    job_id: str
    col: int
    row: int
    level: int = 1
    ap: int = 0
    perm_power: float = 0.0
    perm_speed: float = 0.0
    perm_range: float = 0.0
    perm_mastery: float = 0.0
    job_levels: Dict[str, int] = field(default_factory=dict)
    promotions: List[str] = field(default_factory=list)
    move_speed_penalty_pct: float = 0.0
    move_penalty_remaining_sec: float = 0.0
    total_damage: float = 0.0


def create_enclave_specialist_tower(
    unit_id: str,
    specialist_id: str,
    job_id: str = "swordplay",
    col: int = 4,
    row: int = 4,
) -> EnclaveTowerUnit:
    if job_id not in HERO_CLASS_REGISTRY:
        raise ValueError(f"Unknown job_id: {job_id}")
    cls = HERO_CLASS_REGISTRY[job_id]
    return EnclaveTowerUnit(
        unit_id=unit_id,
        specialist_id=specialist_id,
        job_id=job_id,
        col=col,
        row=row,
        level=1,
        ap=0,
        perm_power=float(cls["base_power"]),
        perm_speed=float(cls["base_speed"]),
        perm_range=float(cls["base_range"]),
        perm_mastery=10.0,
        job_levels={job_id: 1},
    )


def grant_specialist_ap(unit: EnclaveTowerUnit, ap_amount: int) -> EnclaveTowerUnit:
    """Grants AP with infinite level scaling and permanent class-specific stat growth."""
    cls = HERO_CLASS_REGISTRY[unit.job_id]
    growth = cls["growth"]
    unit.ap += ap_amount
    while unit.ap >= 60:
        unit.ap -= 60
        unit.level += 1
        unit.job_levels[unit.job_id] = unit.job_levels.get(unit.job_id, 1) + 1
        unit.perm_power = round(unit.perm_power + growth["power"], 2)
        unit.perm_speed = round(unit.perm_speed + growth["speed"], 2)
        unit.perm_range = round(unit.perm_range + growth["range"], 3)
        unit.perm_mastery = round(unit.perm_mastery + growth["mastery"], 2)
    return unit


def can_promote_specialist_to_job(unit: EnclaveTowerUnit, target_job_id: str) -> bool:
    cls = HERO_CLASS_REGISTRY.get(target_job_id)
    if not cls:
        return False
    for req_job, req_lvl in cls["prereqs"].items():
        if unit.job_levels.get(req_job, 0) < req_lvl:
            return False
    return True


def promote_specialist_job(unit: EnclaveTowerUnit, target_job_id: str) -> EnclaveTowerUnit:
    if not can_promote_specialist_to_job(unit, target_job_id):
        raise ValueError(f"Prerequisites not met for {target_job_id}")
    unit.job_id = target_job_id
    if target_job_id not in unit.job_levels:
        unit.job_levels[target_job_id] = 1
    return unit


def order_specialist_move(
    unit: EnclaveTowerUnit, target_col: int, target_row: int, between_waves: bool = False
) -> EnclaveTowerUnit:
    """Applies Movement Speed Decay curve (zero stationary buffs; speed dampens decay)."""
    dist = math.hypot(target_col - unit.col, target_row - unit.row)
    unit.col = target_col
    unit.row = target_row
    if between_waves or dist <= 0.01:
        unit.move_speed_penalty_pct = 0.0
        unit.move_penalty_remaining_sec = 0.0
        return unit

    tempo_ranks = sum(1 for p in unit.promotions if p.startswith("tempo_"))
    speed_factor = max(0.45, 70.0 / max(35.0, unit.perm_speed))
    promo_mult = max(0.40, 1.0 - 0.18 * tempo_ranks)

    unit.move_speed_penalty_pct = round(min(45.0, (14.0 + dist * 4.5) * promo_mult), 2)
    unit.move_penalty_remaining_sec = round(max(0.8, dist * 1.15 * speed_factor * promo_mult), 2)
    return unit


def evaluate_dyadic_resonance_on_grid(units: List[EnclaveTowerUnit]) -> Dict[str, Any]:
    """Detects Enclave dyadic partner pairs deployed within 2.35 tiles on the 16x10 grid."""
    active_pairs: List[Dict[str, Any]] = []
    for i in range(len(units)):
        for j in range(i + 1, len(units)):
            u_a = units[i]
            u_b = units[j]
            dist = math.hypot(u_a.col - u_b.col, u_a.row - u_b.row)
            if dist <= 2.35:
                active_pairs.append(
                    {
                        "unit_a": u_a.specialist_id,
                        "unit_b": u_b.specialist_id,
                        "distance_tiles": round(dist, 2),
                        "catalyst_bonus_pct": 18,
                    }
                )
    return {
        "active_pairs": active_pairs,
        "catalyst_damage_bonus_pct": min(54, len(active_pairs) * 18),
        "move_decay_reduction_pct": 20 if active_pairs else 0,
    }


# ============================================================================
# 4. EVENT-SEEDED DETERMINISTIC 16x10 PROCEDURAL MAP GENERATOR
# ============================================================================

def generate_event_seeded_battlefield(
    event_id: str,
    sol_number: int,
    active_pov_id: str,
    door_archetype: str = "TICKING_CRISIS",
    margin_hypothesis_submitted: bool = True,
    black_market_prank_active: bool = True,
) -> Dict[str, Any]:
    """
    Deterministically generates a 16x10 multi-lane Tower Defense battlefield
    seeded directly by the active Enclave Narrative Event.
    """
    cols, rows = 16, 10
    seed_str = f"{event_id}-SOL{sol_number}-{active_pov_id.upper()}-{door_archetype}"
    digest = hashlib.sha256(seed_str.encode("utf-8")).digest()

    core_col = 14
    core_row = 3 + (digest[0] % 4)
    spawn_top_row = 1 + (digest[1] % 2)
    spawn_bot_row = 7 + (digest[2] % 2)
    mid_col = 5 + (digest[3] % 4)

    grid: List[List[str]] = [["grass" for _ in range(cols)] for _ in range(rows)]

    def carve_manhattan_route(start_r: int, start_c: int) -> List[Tuple[int, int]]:
        pts: List[Tuple[int, int]] = []
        r, c = start_r, start_c
        pts.append((r, c))
        grid[r][c] = "path"
        while c < mid_col:
            c += 1
            pts.append((r, c))
            grid[r][c] = "path"
        while r != core_row:
            r += 1 if core_row > r else -1
            pts.append((r, c))
            grid[r][c] = "path"
        while c < core_col:
            c += 1
            pts.append((r, c))
            grid[r][c] = "path"
        return pts

    route_alpha = carve_manhattan_route(spawn_top_row, 0)
    route_beta = carve_manhattan_route(spawn_bot_row, 0)
    grid[core_row][core_col] = "core"

    # Place deterministic Highground and Leyline tiles on non-path cells
    for idx in range(6):
        hc = 2 + (digest[4 + idx] % (cols - 4))
        hr = 1 + (digest[10 + idx] % (rows - 2))
        if grid[hr][hc] == "grass":
            grid[hr][hc] = "highground"

    scouting_gold_bonus = 0
    modifiers: List[str] = []

    if margin_hypothesis_submitted:
        scouting_gold_bonus += 75
        modifiers.append("17th-Node Margin Hypothesis (+75g Scouting Supply & Astral Pylon)")
        astral_r = max(1, min(rows - 2, core_row - 1))
        astral_c = max(1, min(cols - 3, core_col - 2))
        if grid[astral_r][astral_c] in ("grass", "highground"):
            grid[astral_r][astral_c] = "leyline_astral"

    if black_market_prank_active:
        modifiers.append("Vex's 3-Turn Black Market Contraption (Alkahest Leyline Node)")
        alk_r = max(1, min(rows - 2, core_row + (1 if core_row < rows - 2 else -1)))
        alk_c = max(1, min(cols - 3, mid_col + 1))
        if grid[alk_r][alk_c] in ("grass", "highground"):
            grid[alk_r][alk_c] = "leyline_alkahest"

    buildable_tiles = sum(
        1
        for r in range(rows)
        for c in range(cols)
        if grid[r][c] in ("grass", "highground", "leyline_astral", "leyline_alkahest")
    )

    return {
        "seed": seed_str,
        "cols": cols,
        "rows": rows,
        "door_archetype": door_archetype,
        "core_point": (core_row, core_col),
        "routes": [
            {"name": "Northern Basalt Causeway", "points": route_alpha},
            {"name": "Southern Geothermal Trench", "points": route_beta},
        ],
        "grid": grid,
        "buildable_tiles": buildable_tiles,
        "scouting_gold_bonus": scouting_gold_bonus,
        "modifiers": modifiers,
    }


# ============================================================================
# 5. 4-STAGE EPOCH LOOP & LIVING ATLAS BATTLE OUTCOME COMPILER
# ============================================================================

class SovereignMarchEpochBridge:
    """
    Coordinates the 4-stage unified game loop:
    STAGE_1_LIVING_ATLAS -> STAGE_2_CORRIDOR_GATE -> STAGE_3_TACTICAL_DEFENSE -> STAGE_4_COLONY_FEAST
    and compiles Stage 3 battle telemetry into a calibrated Living Atlas Chapter
    audited by NarrativeCalibrationEngine (Stop-Slop >= 35/50).
    """

    STAGES = (
        "STAGE_1_LIVING_ATLAS",
        "STAGE_2_CORRIDOR_GATE",
        "STAGE_3_TACTICAL_DEFENSE",
        "STAGE_4_COLONY_FEAST",
    )

    def __init__(self, sol_number: int = 28, active_pov_id: str = "enclave_15_dorian") -> None:
        self.sol_number = sol_number
        self.active_pov_id = (
            active_pov_id if active_pov_id in CHARACTER_SPINES else "enclave_15_dorian"
        )
        self.current_stage = "STAGE_1_LIVING_ATLAS"
        self.waves_required_for_stage4 = 3
        self.waves_cleared = 0
        self.stage3_cleared = False
        self.swain_sequel_state = "NONE"

    def advance_to_corridor_gate(self, margin_hypothesis: str) -> Dict[str, Any]:
        self.current_stage = "STAGE_2_CORRIDOR_GATE"
        return {
            "stage": self.current_stage,
            "margin_hypothesis_recorded": bool(margin_hypothesis.strip()),
            "scouting_gold_bonus": 75 if margin_hypothesis.strip() else 0,
        }

    def enter_tactical_defense(self, event_id: str = "EVT-SOL028-VAULT-SHEAR") -> Dict[str, Any]:
        self.current_stage = "STAGE_3_TACTICAL_DEFENSE"
        return generate_event_seeded_battlefield(
            event_id=event_id,
            sol_number=self.sol_number,
            active_pov_id=self.active_pov_id,
        )

    def resolve_tactical_battle(
        self,
        waves_cleared: int,
        victory: bool,
        mvp_unit: EnclaveTowerUnit,
        total_synergies: int,
        reposition_count: int,
        terminology_mode: str = "kepler_exoplanet",
    ) -> Dict[str, Any]:
        """
        Enforces 'Beat the Level to Progress to the Next Style System' and compiles
        the battle telemetry into a Stop-Slop calibrated Living Atlas prose segment.
        """
        self.waves_cleared = waves_cleared
        if victory and waves_cleared >= self.waves_required_for_stage4:
            self.stage3_cleared = True
            self.current_stage = "STAGE_4_COLONY_FEAST"
            self.swain_sequel_state = "NONE"
        else:
            self.stage3_cleared = False
            self.current_stage = "STAGE_3_TACTICAL_DEFENSE"
            self.swain_sequel_state = "YES_BUT_RECOVERY"

        pov_name = self.active_pov_id.split("_")[-1].capitalize()
        cls_info = HERO_CLASS_REGISTRY[mvp_unit.job_id]
        job_title = (
            cls_info["kepler_name"] if terminology_mode == "kepler_exoplanet" else cls_info["classic_name"]
        )

        raw_prose = (
            f"The Bourdon pressure gauge on Sector 4 climbed past forty-two megapascals as the armored column breached the basalt causeway. "
            f"{pov_name} locked the {job_title} housing into the highground detent. "
            f"The gasket held.\n\n"
            f"Across {waves_cleared} assault waves, the squad repositioned {reposition_count} times along the catwalk and triggered {total_synergies} dual-element catalyst detonations before the carapace vanguard reached the inner sluice. "
            f"At Ryn's galley table that night, {pov_name} set the calibration wrench beside the fermented root-stew while the manifold settled into a clean 432-hertz lock."
        )

        cal_res = run_three_pass_de_ai_calibration(raw_prose)
        calibrated_prose = cal_res["calibrated_text"]
        audit = score_stop_slop_5d(calibrated_prose)

        return {
            "stage": self.current_stage,
            "stage3_cleared": self.stage3_cleared,
            "swain_sequel_state": self.swain_sequel_state,
            "job_title": job_title,
            "calibrated_prose": calibrated_prose,
            "stop_slop_score": audit["total_score"],
            "passed_stop_slop_gate": audit["passed"],
        }

