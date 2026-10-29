"""Deterministic 2.5D Voxel City & Animal Crossing Companion Engine for The Enclave of the 16 (`STAGE_2`).

Strictly reuses the canonical Enclave Digital Twin & LFS Suite engines (zero parallel reinvention):
- `engine.chronosphere` (`DAY_PHASES`, `initial_chronosphere`, `advance_tick`, `build_chronosphere_for_tick`)
- `engine.magneto_weather` (`BIOME_CELLS`, `MICRO_CLIMATE_REGIMES`, `compute_exoplanet_weather`)
- `engine.state_ode` (`sample_character_state`, `compute_domain_friction`)
- `engine.drama_director` (`evaluate_pacing_and_beat`)
- `engine.shadow_economy` (`seed_shadow_prank`, `process_shadow_ledger`)
- `engine.oasis_twin_bridge` (`compute_enclave_player_meta_rewards`, `extract_enclave_twin_live_state`,
  `sync_enclave_oasis_save_and_bridge`)
- Cross-Capsule Suite Synergies (`oasis-component-atlas.json` `SR-02`, `SR-04`, `SR-05`, `SR-08`):
  - `SR-02` (`lfs-tycoon`): `theme_enclave_first_forge` & `theme_enclave_living_atlas` crafting items
  - `SR-04` (`crucible-automata`): 4 elemental Hearth biomes (`Porch Hearth`, `Rain Garden`,
    `Flow Hourglass`, `Alchemist Crucible`)
  - `SR-05` (`dads-book-lore`): Living Atlas epistemic tiers (`TIER_1_VERIFIED_EVENT`,
    `TIER_2_EMPIRICAL_SPECIMEN`, `TIER_3_ORAL_BALLAD`, `TIER_4_SPECULATIVE_HYPOTHESIS`)
  - `SR-08`: `window.ArcadeAssetBridge` & `lfs-local-abac-v1` Rupee (`RUP`) synchronization.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

from engine.chronosphere import (
    DAY_PHASES,
    advance_tick,
    build_chronosphere_for_tick,
    initial_chronosphere,
)
from engine.drama_director import evaluate_pacing_and_beat
from engine.magneto_weather import (
    BIOME_CELLS,
    MICRO_CLIMATE_REGIMES,
    compute_exoplanet_weather,
)
from engine.shadow_economy import process_shadow_ledger, seed_shadow_prank
from engine.state_ode import compute_domain_friction, sample_character_state
from tools.check_enclave_constitutions import (
    CANONICAL_16_CHARACTER_IDS,
    CANONICAL_16_MBTI,
    HOSTILE_PVE_KEYWORDS,
)

SCHEMA_VERSION = "enclave-voxel-city-v2"
ENCLAVE_VOXEL_CITY_SCHEMA = SCHEMA_VERSION
GRID_SIZE = 48
OASIS_CMY_RUPEE_TIERS: tuple[int, ...] = (1, 5, 10, 25, 50, 100, 250, 500, 1000)

# ============================================================================
# CROSS-CAPSULE SUITE SYNERGIES (oasis-component-atlas.json SR-02, SR-04, SR-05, SR-08)
# ============================================================================
CRUCIBLE_ELEMENTAL_HEARTH_BIOMES: tuple[str, ...] = (
    "Porch Hearth",
    "Rain Garden",
    "Flow Hourglass",
    "Alchemist Crucible",
)

DADS_BOOK_LORE_EPISTEMIC_TIERS: tuple[str, ...] = (
    "TIER_1_VERIFIED_EVENT",
    "TIER_2_EMPIRICAL_SPECIMEN",
    "TIER_3_ORAL_BALLAD",
    "TIER_4_SPECULATIVE_HYPOTHESIS",
)

LFS_TYCOON_CRAFTING_THEMES: tuple[str, ...] = (
    "theme_enclave_first_forge",
    "theme_enclave_living_atlas",
)

SUITE_SYNERGY_ATLAS: dict[str, dict[str, Any]] = {
    "SR-02": {
        "synergy_id": "SR-02",
        "source_capsule": "lfs-tycoon",
        "shared_items": list(LFS_TYCOON_CRAFTING_THEMES),
        "description": "Shared Forge & Living Atlas workshop themes unlocked across Tycoon and Enclave City.",
    },
    "SR-04": {
        "synergy_id": "SR-04",
        "source_capsule": "crucible-automata",
        "hearth_biomes": list(CRUCIBLE_ELEMENTAL_HEARTH_BIOMES),
        "description": "Four elemental Hearth micro-biomes coupled with Enclave Crater Valley regimes.",
    },
    "SR-05": {
        "synergy_id": "SR-05",
        "source_capsule": "dads-book-lore",
        "epistemic_tiers": list(DADS_BOOK_LORE_EPISTEMIC_TIERS),
        "description": "Living Atlas epistemic provenance tiers shared with Dorian & Vex's Museum.",
    },
    "SR-08": {
        "synergy_id": "SR-08",
        "source_capsule": "lfs-trash-arcade",
        "bridge_global": "window.ArcadeAssetBridge",
        "schema": "lfs-local-abac-v1",
        "currency_code": "RUP",
        "description": "Cross-capsule Rupee (RUP) satchel & wardrobe asset bridge via engine.oasis_twin_bridge.",
    },
}

# ============================================================================
# 1. FIVE CRATER VALLEY BIOME REGIMES (Coupled to engine.magneto_weather & SR-04 Hearth Biomes)
# ============================================================================
ENCLAVE_BIOMES: dict[str, dict[str, Any]] = {
    "crater_valley": {
        "biome_id": "crater_valley",
        "name": "Enclave Crater Valley",
        "canonical_biome_cell": BIOME_CELLS[0],
        "crucible_hearth_biome": "Porch Hearth",
        "subtitle": "Bioluminescent mycelial moss, ferrofluid river channel & copper-basalt cobbles",
        "ground_palette": ["#2d5e40", "#346b49", "#265237"],
        "water_color": "#16384c",
        "water_highlight": "#32f5c8",
        "road_color": "#8c6d46",
        "plaza_color": "#b88a4b",
        "tree_foliage": ["#22784b", "#2e965e", "#44b878"],
        "ambient_kp_baseline": 3.8,
        "micro_climate_regime": MICRO_CLIMATE_REGIMES[0],
    },
    "storm_ridge": {
        "biome_id": "storm_ridge",
        "name": "Stormbreaker Frost-Shear Crest",
        "canonical_biome_cell": BIOME_CELLS[1],
        "crucible_hearth_biome": "Flow Hourglass",
        "subtitle": "Rime-slate tundra, piezo-quartz outcrops & supercooled ferrofluid channels",
        "ground_palette": ["#4a6274", "#587285", "#3d5363"],
        "water_color": "#1a334a",
        "water_highlight": "#70e4ff",
        "road_color": "#738290",
        "plaza_color": "#94a8b8",
        "tree_foliage": ["#5c8ca8", "#74a8c4", "#9be0ff"],
        "ambient_kp_baseline": 5.6,
        "micro_climate_regime": MICRO_CLIMATE_REGIMES[2],
    },
    "genesis_terraces": {
        "biome_id": "genesis_terraces",
        "name": "Genesis Agricultural Terraces",
        "canonical_biome_cell": BIOME_CELLS[2],
        "crucible_hearth_biome": "Rain Garden",
        "subtitle": "Chelated golden loam, crystalline iron-wheat plots & geothermal irrigation canals",
        "ground_palette": ["#4d6b32", "#5a7a3c", "#3f5927"],
        "water_color": "#1d4c54",
        "water_highlight": "#52ffd8",
        "road_color": "#9e7340",
        "plaza_color": "#d49b4b",
        "tree_foliage": ["#588c28", "#72ab38", "#9cd14f"],
        "ambient_kp_baseline": 3.2,
        "micro_climate_regime": MICRO_CLIMATE_REGIMES[3],
    },
    "spore_glade": {
        "biome_id": "spore_glade",
        "name": "Fern-Gorge Spore Sanctuary",
        "canonical_biome_cell": BIOME_CELLS[3],
        "crucible_hearth_biome": "Rain Garden",
        "subtitle": "Deep violet-emerald mycelial marsh, resonant spore-fog pools & glowing fungi",
        "ground_palette": ["#2a444e", "#32525e", "#223840"],
        "water_color": "#202b4a",
        "water_highlight": "#b066ff",
        "road_color": "#6e5a4f",
        "plaza_color": "#8f7565",
        "tree_foliage": ["#228b78", "#34b89a", "#78f5d4"],
        "ambient_kp_baseline": 4.4,
        "micro_climate_regime": MICRO_CLIMATE_REGIMES[1],
    },
    "forge_caldera": {
        "biome_id": "forge_caldera",
        "name": "Eastern Forge Basalt Caldera",
        "canonical_biome_cell": BIOME_CELLS[4],
        "crucible_hearth_biome": "Alchemist Crucible",
        "subtitle": "Obsidian-basalt floor, molten bismuth-slag channels & copper busbar roads",
        "ground_palette": ["#3b383c", "#464247", "#302d30"],
        "water_color": "#42231b",
        "water_highlight": "#ff9838",
        "road_color": "#8c5220",
        "plaza_color": "#c88732",
        "tree_foliage": ["#6e5838", "#8f6e40", "#c89648"],
        "ambient_kp_baseline": 5.1,
        "micro_climate_regime": MICRO_CLIMATE_REGIMES[4],
    },
}

# ============================================================================
# 2. EIGHTEEN DETAILED VOXEL STRUCTURES
#    (8 Grand Projects + 4 Animal Crossing Facilities + 6 Squad Cottages)
# ============================================================================
ENCLAVE_BUILDINGS: tuple[dict[str, Any], ...] = (
    # --- 8 Canonical Grand Project Landmarks ---
    {
        "building_id": "proj_01_first_forge",
        "name": "The First Forge",
        "category": "grand_project",
        "project_id": "proj_01_first_forge",
        "squad": "The Forge",
        "x": 30,
        "y": 9,
        "w": 5,
        "d": 4,
        "h": 4,
        "wall_color": "#6e473b",
        "roof_color": "#c86428",
        "trim_color": "#e6ac55",
        "icon": "⚒️",
        "residents": ["enclave_03_silas", "enclave_04_leo"],
        "tycoon_theme_id": "theme_enclave_first_forge",
        "hearth_biome": "Alchemist Crucible",
        "description": "Induction smelter & bismuth-bronze busbar foundry anchored by Silas and Leo.",
    },
    {
        "building_id": "proj_02_stormbreaker",
        "name": "The Stormbreaker Spire",
        "category": "grand_project",
        "project_id": "proj_02_stormbreaker",
        "squad": "The Forge",
        "x": 38,
        "y": 6,
        "w": 4,
        "d": 4,
        "h": 6,
        "wall_color": "#4f6272",
        "roof_color": "#32a8d4",
        "trim_color": "#32f5c8",
        "icon": "⚡",
        "residents": ["enclave_01_hector", "enclave_02_jane"],
        "hearth_biome": "Flow Hourglass",
        "description": "High-ridge copper lightning harvester & Babbage fluid-loom weather tower.",
    },
    {
        "building_id": "proj_03_sanctuary",
        "name": "The Sanctuary Paddock",
        "category": "grand_project",
        "project_id": "proj_03_sanctuary",
        "squad": "The Wilds",
        "x": 6,
        "y": 33,
        "w": 5,
        "d": 4,
        "h": 3,
        "wall_color": "#4b6b48",
        "roof_color": "#2e8b57",
        "trim_color": "#8be898",
        "icon": "🦌",
        "residents": ["enclave_05_kaio", "enclave_06_zara"],
        "hearth_biome": "Rain Garden",
        "description": "Mutualistic magnetotropic fauna refuge & acoustic-shielded grove.",
    },
    {
        "building_id": "proj_04_genesis_garden",
        "name": "The Genesis Garden Conservatory",
        "category": "grand_project",
        "project_id": "proj_04_genesis_garden",
        "squad": "The Wilds",
        "x": 11,
        "y": 24,
        "w": 5,
        "d": 4,
        "h": 4,
        "wall_color": "#587844",
        "roof_color": "#3cb371",
        "trim_color": "#e6ac55",
        "icon": "🌿",
        "residents": ["enclave_07_willow", "enclave_08_terra"],
        "hearth_biome": "Rain Garden",
        "description": "Chelated piezo-mycorrhizal greenhouse & Crystalline Iron-Wheat terrace.",
    },
    {
        "building_id": "proj_05_simulacrum",
        "name": "The Simulacrum Rotunda",
        "category": "grand_project",
        "project_id": "proj_05_simulacrum",
        "squad": "The Mind",
        "x": 8,
        "y": 8,
        "w": 5,
        "d": 4,
        "h": 5,
        "wall_color": "#484c6c",
        "roof_color": "#6a5acd",
        "trim_color": "#32f5c8",
        "icon": "🔮",
        "residents": ["enclave_09_orion", "enclave_10_isla"],
        "hearth_biome": "Flow Hourglass",
        "description": "Thirty-two-ring brass Helmholtz ferrofluid phase-space observatory.",
    },
    {
        "building_id": "proj_06_lyceum_of_the_mind",
        "name": "The Lyceum of the Mind",
        "category": "grand_project",
        "project_id": "proj_06_lyceum_of_the_mind",
        "squad": "The Mind",
        "x": 16,
        "y": 8,
        "w": 4,
        "d": 4,
        "h": 4,
        "wall_color": "#5d5370",
        "roof_color": "#8a6bbd",
        "trim_color": "#f4ead5",
        "icon": "🧠",
        "residents": ["enclave_11_kenna", "enclave_12_elias"],
        "hearth_biome": "Porch Hearth",
        "description": "Acoustic-somatic grounding sanctuary & circadian neuro-harmonics hall.",
    },
    {
        "building_id": "proj_07_living_atlas",
        "name": "The Living Atlas Observatory & Colony Museum",
        "category": "grand_project",
        "project_id": "proj_07_living_atlas",
        "squad": "The Hub",
        "x": 31,
        "y": 24,
        "w": 5,
        "d": 4,
        "h": 5,
        "wall_color": "#6c563e",
        "roof_color": "#b8860b",
        "trim_color": "#32f5c8",
        "icon": "🏛️",
        "residents": ["enclave_14_vex", "enclave_15_dorian"],
        "tycoon_theme_id": "theme_enclave_living_atlas",
        "hearth_biome": "Flow Hourglass",
        "description": "Colony Museum of Geodes, Critters, Ferro-Fish & Mycelial Concordance Archives.",
    },
    {
        "building_id": "proj_08_hearth_metabolic_engine",
        "name": "The Hearth & Metabolic Galley",
        "category": "grand_project",
        "project_id": "proj_08_hearth_metabolic_engine",
        "squad": "The Hub",
        "x": 21,
        "y": 15,
        "w": 6,
        "d": 4,
        "h": 4,
        "wall_color": "#8c5220",
        "roof_color": "#d2691e",
        "trim_color": "#ffcf66",
        "icon": "🍲",
        "residents": ["enclave_13_ryn", "enclave_16_elara"],
        "hearth_biome": "Porch Hearth",
        "description": "Central Main Bus dining hall where all 16 citizens gather nightly for The Feast.",
    },
    # --- 4 Animal Crossing Civic & Player Companion Facilities ---
    {
        "building_id": "bldg_willow_homestead",
        "name": "Willow's Alchemist Homestead & Custom Yard",
        "category": "ac_player_home",
        "project_id": "proj_04_genesis_garden",
        "squad": "The Wilds",
        "x": 16,
        "y": 28,
        "w": 4,
        "d": 4,
        "h": 4,
        "wall_color": "#3c6e58",
        "roof_color": "#26a678",
        "trim_color": "#ffd866",
        "icon": "🏡",
        "residents": ["enclave_07_willow"],
        "hearth_biome": "Alchemist Crucible",
        "description": "Willow's cozy copper-glass cottage, fractional alembic workbench, wardrobe mirror, and customizable yard.",
    },
    {
        "building_id": "bldg_sibling_post",
        "name": "Sibling Grid Pneumatic Post & Notice Board",
        "category": "ac_civic",
        "project_id": "proj_07_living_atlas",
        "squad": "The Hub",
        "x": 27,
        "y": 19,
        "w": 3,
        "d": 3,
        "h": 3,
        "wall_color": "#705842",
        "roof_color": "#cd853f",
        "trim_color": "#32f5c8",
        "icon": "📮",
        "residents": ["enclave_05_kaio", "enclave_15_dorian"],
        "hearth_biome": "Porch Hearth",
        "description": "Daily Villager Favor Bulletin Board, friendly pneumatic letters & 3-Sol Shadow Economy prank dispatch.",
    },
    {
        "building_id": "bldg_curio_pavilion",
        "name": "Aegis Outfitters & Curio Pavilion",
        "category": "ac_civic",
        "project_id": "proj_08_hearth_metabolic_engine",
        "squad": "The Hub",
        "x": 17,
        "y": 19,
        "w": 3,
        "d": 3,
        "h": 3,
        "wall_color": "#64486e",
        "roof_color": "#ba55d3",
        "trim_color": "#ffd866",
        "icon": "🎀",
        "residents": ["enclave_09_orion", "enclave_15_dorian"],
        "hearth_biome": "Porch Hearth",
        "description": "Steampunk-botanical wardrobe showcase, DIY furniture exchange & window.ArcadeAssetBridge Rupee counter.",
    },
    {
        "building_id": "bldg_ferro_pier",
        "name": "Ferrofluid Basin Pier & Tide Dock",
        "category": "ac_civic",
        "project_id": "proj_03_sanctuary",
        "squad": "The Wilds",
        "x": 22,
        "y": 32,
        "w": 4,
        "d": 3,
        "h": 2,
        "wall_color": "#546875",
        "roof_color": "#2f9fb8",
        "trim_color": "#32f5c8",
        "icon": "🎣",
        "residents": ["enclave_06_zara", "enclave_07_willow"],
        "hearth_biome": "Rain Garden",
        "description": "Brass-railed angling pier jutting over the colloidal magnetite river channel.",
    },
    # --- 6 Squad Residential Cottages ---
    {
        "building_id": "bldg_forge_lodge",
        "name": "Forge Anchor Lodge",
        "category": "residential",
        "project_id": "proj_01_first_forge",
        "squad": "The Forge",
        "x": 37,
        "y": 14,
        "w": 4,
        "d": 3,
        "h": 3,
        "wall_color": "#7a5244",
        "roof_color": "#b8572c",
        "trim_color": "#e6ac55",
        "icon": "🏠",
        "residents": ["enclave_03_silas", "enclave_04_leo"],
        "hearth_biome": "Porch Hearth",
        "description": "Warm hearth-heated basalt cottage with micrometer tool racks for Silas and Leo.",
    },
    {
        "building_id": "bldg_wilds_nook",
        "name": "Wilds Botanical Nook",
        "category": "residential",
        "project_id": "proj_04_genesis_garden",
        "squad": "The Wilds",
        "x": 6,
        "y": 26,
        "w": 4,
        "d": 3,
        "h": 3,
        "wall_color": "#4f6d4a",
        "roof_color": "#439960",
        "trim_color": "#f4ead5",
        "icon": "🛖",
        "residents": ["enclave_06_zara", "enclave_08_terra"],
        "hearth_biome": "Rain Garden",
        "description": "Moss-roofed timber cottage hung with drying heirloom seed braids and fauna perches.",
    },
    {
        "building_id": "bldg_mind_loft",
        "name": "Mind Contemplative Loft",
        "category": "residential",
        "project_id": "proj_06_lyceum_of_the_mind",
        "squad": "The Mind",
        "x": 7,
        "y": 15,
        "w": 4,
        "d": 3,
        "h": 3,
        "wall_color": "#545875",
        "roof_color": "#5f6caf",
        "trim_color": "#32f5c8",
        "icon": "🏘️",
        "residents": ["enclave_11_kenna", "enclave_12_elias"],
        "hearth_biome": "Flow Hourglass",
        "description": "Quiet cedar-and-brass study overlooking the upper river bend for Kenna and Elias.",
    },
    {
        "building_id": "bldg_hub_gables",
        "name": "Hub Chronicler Gables",
        "category": "residential",
        "project_id": "proj_07_living_atlas",
        "squad": "The Hub",
        "x": 38,
        "y": 25,
        "w": 4,
        "d": 3,
        "h": 3,
        "wall_color": "#755a44",
        "roof_color": "#c87d32",
        "trim_color": "#f4ead5",
        "icon": "🏘️",
        "residents": ["enclave_15_dorian", "enclave_16_elara"],
        "hearth_biome": "Porch Hearth",
        "description": "Gabled apothecary and bardic archive cottage shared by Elara and Dorian.",
    },
    {
        "building_id": "bldg_prodigy_east",
        "name": "Prodigy Quarters East",
        "category": "residential",
        "project_id": "proj_02_stormbreaker",
        "squad": "The Forge",
        "x": 31,
        "y": 15,
        "w": 4,
        "d": 3,
        "h": 3,
        "wall_color": "#645852",
        "roof_color": "#d47a38",
        "trim_color": "#32f5c8",
        "icon": "⛺",
        "residents": ["enclave_01_hector", "enclave_02_jane", "enclave_05_kaio", "enclave_13_ryn"],
        "hearth_biome": "Porch Hearth",
        "description": "Bunkhouse loft humming with wind-glider harnesses, Babbage punch-cards, and midnight snacks.",
    },
    {
        "building_id": "bldg_prodigy_west",
        "name": "Prodigy Quarters West",
        "category": "residential",
        "project_id": "proj_05_simulacrum",
        "squad": "The Mind",
        "x": 13,
        "y": 15,
        "w": 3,
        "d": 3,
        "h": 3,
        "wall_color": "#58526e",
        "roof_color": "#8862b8",
        "trim_color": "#ffd866",
        "icon": "⛺",
        "residents": ["enclave_09_orion", "enclave_10_isla", "enclave_14_vex"],
        "hearth_biome": "Flow Hourglass",
        "description": "Skylit studio dormitory stacked with star-charts, cymatic tuning forks, and architectural blueprints.",
    },
)

# ============================================================================
# 3. SIX ANIMAL CROSSING INTERACTIVE TOOLS FOR WILLOW
# ============================================================================
WILLOW_AC_TOOLS: tuple[dict[str, Any], ...] = (
    {
        "tool_id": "trowel",
        "slot": 1,
        "name": "Copper Trowel & Chelation Flask",
        "short_label": "⚗️ Trowel",
        "icon": "⚗️",
        "action_type": "forage_dig",
        "description": "Forage cave-truffles & glowing lichen, dig resonant geode cracks, and chelate ferro-silicate soil.",
    },
    {
        "tool_id": "bug_net",
        "slot": 2,
        "name": "Magnetotropic Bug Net",
        "short_label": "🦋 Bug Net",
        "icon": "🦋",
        "action_type": "catch_critter",
        "description": "Catch Prism-Moths, Soliton Fireflies, Luminescent Cave-Beetles, and Bismuth Dragonflies.",
    },
    {
        "tool_id": "dip_rod",
        "slot": 3,
        "name": "Ferrofluid Dip-Rod",
        "short_label": "🎣 Dip-Rod",
        "icon": "🎣",
        "action_type": "catch_fish",
        "description": "Angle for Magnetite Ammonites, Rosensweig Eels, Colloidal Pike, and Fulgurite Crabs in ferrofluid waters.",
    },
    {
        "tool_id": "watering_can",
        "slot": 4,
        "name": "Distilled Rainwater Can",
        "short_label": "💧 Water Can",
        "icon": "💧",
        "action_type": "water_crop",
        "description": "Irrigate Crystalline Iron-Wheat plots and hybridize bioluminescent Spore-Orchids.",
    },
    {
        "tool_id": "tinker_wrench",
        "slot": 5,
        "name": "Tinker Wrench & Yard Decorator",
        "short_label": "🪑 Decorate",
        "icon": "🪑",
        "action_type": "place_decor",
        "description": "Craft DIY recipes & place or rearrange voxel yard furniture, lanterns, chimes, and alembic stills.",
    },
    {
        "tool_id": "gift_satchel",
        "slot": 6,
        "name": "Favor & Gift Satchel",
        "short_label": "🎁 Gift/Favor",
        "icon": "🎁",
        "action_type": "gift_citizen",
        "description": "Deliver favorite alchemical gifts & complete Daily Bulletin Board Favors for the 15 Enclave citizens.",
    },
)

# ============================================================================
# 4. LIVING ATLAS COLONY MUSEUM CATALOG (16 SPECIMENS ACROSS 4 WINGS + SR-05 EPISTEMIC TIERS)
# ============================================================================
MUSEUM_CATALOG: tuple[dict[str, Any], ...] = (
    # Wing 1: Captured Lightning Geodes & Minerals (4)
    {
        "specimen_id": "spec_geode_bismuth",
        "name": "Hopper-Crystal Bismuth Geode",
        "wing": "geodes",
        "wing_label": "⚡ Captured Geodes",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "💎",
        "rarity": "Rare",
        "rup_reward": 10,
        "lore": "Iridescent stepped bismuth-telluride nodule trapping a 40-ampere persistent atmospheric current.",
    },
    {
        "specimen_id": "spec_geode_fulgurite",
        "name": "Bifurcated Ridge Fulgurite Tube",
        "wing": "geodes",
        "wing_label": "⚡ Captured Geodes",
        "epistemic_tier": "TIER_1_VERIFIED_EVENT",
        "icon": "⚡",
        "rarity": "Uncommon",
        "rup_reward": 10,
        "lore": "Vitrified ferro-silicate lightning glass fused during a Kp 7.2 storm on Stormbreaker Ridge.",
    },
    {
        "specimen_id": "spec_geode_piezo",
        "name": "Singing Piezo-Quartz Cluster",
        "wing": "geodes",
        "wing_label": "⚡ Captured Geodes",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🔮",
        "rarity": "Rare",
        "rup_reward": 10,
        "lore": "Resonates at a pure 432 Hz harmonic whenever Luna Gamma passes perigee.",
    },
    {
        "specimen_id": "spec_geode_lodestone",
        "name": "Octahedral Magnetite Lodestone",
        "wing": "geodes",
        "wing_label": "⚡ Captured Geodes",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🪨",
        "rarity": "Common",
        "rup_reward": 10,
        "lore": "Naturally polarized core-ore used by Silas to calibrate compasses and Helmholtz rings.",
    },
    # Wing 2: Magnetotropic Critters & Pollinators (4)
    {
        "specimen_id": "spec_critter_prism_moth",
        "name": "Aurora Prism-Moth",
        "wing": "critters",
        "wing_label": "🦋 Magneto-Critters",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🦋",
        "rarity": "Rare",
        "rup_reward": 10,
        "lore": "Diffracts twin-sun ultraviolet rays through chitinous wing-scales to orient along magnetic field lines.",
    },
    {
        "specimen_id": "spec_critter_soliton_firefly",
        "name": "Mycelial Soliton Firefly",
        "wing": "critters",
        "wing_label": "🦋 Magneto-Critters",
        "epistemic_tier": "TIER_4_SPECULATIVE_HYPOTHESIS",
        "icon": "✨",
        "rarity": "Common",
        "rup_reward": 10,
        "lore": "Flashes in synchronized 10 Hz wave-trains matching subterranean fungal telemetry.",
    },
    {
        "specimen_id": "spec_critter_cave_beetle",
        "name": "Copper-Carapace Pollinator Beetle",
        "wing": "critters",
        "wing_label": "🦋 Magneto-Critters",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🪲",
        "rarity": "Uncommon",
        "rup_reward": 10,
        "lore": "Zara's favorite sanctuary helper; carries chelated pollen between Crystalline Iron-Wheat blossoms.",
    },
    {
        "specimen_id": "spec_critter_bismuth_dragonfly",
        "name": "Rainbow Bismuth Skimmer",
        "wing": "critters",
        "wing_label": "🦋 Magneto-Critters",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "蜻",
        "rarity": "Rare",
        "rup_reward": 10,
        "lore": "Hovers effortlessly over standing-wave crests in the ferrofluid river basin.",
    },
    # Wing 3: Ferrofluid Basin Fauna (4)
    {
        "specimen_id": "spec_fish_ammonite",
        "name": "Coiled Magnetite Ammonite",
        "wing": "ferro_fish",
        "wing_label": "🐟 Ferro-Basin Fauna",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🐚",
        "rarity": "Rare",
        "rup_reward": 10,
        "lore": "Living logarithmic spiral shell plated in nanoscale iron-oxide that surfs lunar tidal surges.",
    },
    {
        "specimen_id": "spec_fish_rosensweig_eel",
        "name": "Rosensweig Ribbon-Eel",
        "wing": "ferro_fish",
        "wing_label": "🐟 Ferro-Basin Fauna",
        "epistemic_tier": "TIER_4_SPECULATIVE_HYPOTHESIS",
        "icon": "🐍",
        "rarity": "Rare",
        "rup_reward": 10,
        "lore": "Camouflages among geometric ferrofluid spikes and emits gentle millivolt navigation hums.",
    },
    {
        "specimen_id": "spec_fish_colloidal_pike",
        "name": "Silver-Scale Colloidal Darter",
        "wing": "ferro_fish",
        "wing_label": "🐟 Ferro-Basin Fauna",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🐟",
        "rarity": "Common",
        "rup_reward": 10,
        "lore": "Fast-swimming river fish prized for studying non-toxic heavy-metal filtration membranes.",
    },
    {
        "specimen_id": "spec_fish_fulgurite_crab",
        "name": "Vent-Warmth Fulgurite Crab",
        "wing": "ferro_fish",
        "wing_label": "🐟 Ferro-Basin Fauna",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🦀",
        "rarity": "Uncommon",
        "rup_reward": 10,
        "lore": "Gathers around geothermal bridge pilings and polishes copper pebbles with its claws.",
    },
    # Wing 4: Exoplanet Flora & Old-Earth Relics (4)
    {
        "specimen_id": "spec_flora_iron_wheat",
        "name": "Golden Crystalline Iron-Wheat Sheaf",
        "wing": "flora_relics",
        "wing_label": "🌿 Flora & Relics",
        "epistemic_tier": "TIER_1_VERIFIED_EVENT",
        "icon": "🌾",
        "rarity": "Common",
        "rup_reward": 10,
        "lore": "Willow and Terra's signature hybrid crop—chelated roots yield sweet, mineral-rich grain for The Feast.",
    },
    {
        "specimen_id": "spec_flora_spore_orchid",
        "name": "Bioluminescent Spore-Orchid",
        "wing": "flora_relics",
        "wing_label": "🌿 Flora & Relics",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🌺",
        "rarity": "Rare",
        "rup_reward": 10,
        "lore": "Blooms during Dusk Craft with soft cyan-violet petals that soothe cortical fatigue.",
    },
    {
        "specimen_id": "spec_flora_cave_truffle",
        "name": "Mycelial Amber Cave-Truffle",
        "wing": "flora_relics",
        "wing_label": "🌿 Flora & Relics",
        "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN",
        "icon": "🍄",
        "rarity": "Uncommon",
        "rup_reward": 10,
        "lore": "Aromatic subterranean fruiting body sought by Ryn for Feast gravies and by Willow for tonics.",
    },
    {
        "specimen_id": "spec_flora_jade_pestle",
        "name": "Cloud-Forest Jade Mortar Inlay",
        "wing": "flora_relics",
        "wing_label": "🌿 Flora & Relics",
        "epistemic_tier": "TIER_3_ORAL_BALLAD",
        "icon": "🏺",
        "rarity": "Legendary",
        "rup_reward": 25,
        "lore": "Commemorative botanical pressing honoring Old Earth alpine cloud-forest phytochemistry.",
    },
)

# ============================================================================
# 5. TWELVE DIY ALCHEMY & VOXEL FURNITURE RECIPES (Includes SR-02 lfs-tycoon items)
# ============================================================================
DIY_RECIPES: tuple[dict[str, Any], ...] = (
    {
        "recipe_id": "diy_herbal_liniment",
        "name": "Herbal Joint-Liniment Vial",
        "category": "alchemy_gift",
        "icon": "🧪",
        "placeable": False,
        "ingredients": {"spec_flora_cave_truffle": 1, "spec_geode_lodestone": 1},
        "favorite_of": ["enclave_03_silas", "enclave_04_leo", "enclave_16_elara"],
        "comfort_bonus": 2,
        "description": "Warming pine-resin and sulfur salve Willow slips beside Silas and Leo's plates at The Feast.",
    },
    {
        "recipe_id": "diy_blackberry_cordial",
        "name": "Spiced Blackberry & Lichen Cordial",
        "category": "alchemy_gift",
        "icon": "🍷",
        "placeable": False,
        "ingredients": {"spec_flora_iron_wheat": 1, "spec_flora_spore_orchid": 1},
        "favorite_of": ["enclave_07_willow", "enclave_08_terra", "enclave_13_ryn", "enclave_15_dorian"],
        "comfort_bonus": 2,
        "description": "Kept in the green flask next to Willow's skull-shaped gourd; restores warmth after ridge shifts.",
    },
    {
        "recipe_id": "diy_chelation_elixir",
        "name": "Organometallic Soil Chelation Elixir",
        "category": "alchemy_gift",
        "icon": "⚗️",
        "placeable": False,
        "ingredients": {"spec_geode_fulgurite": 1, "spec_flora_iron_wheat": 1},
        "favorite_of": ["enclave_08_terra", "enclave_06_zara", "enclave_05_kaio"],
        "comfort_bonus": 3,
        "description": "Detoxifies raw ferro-silicate soil so heirloom seedlings sprout without iron lockup.",
    },
    {
        "recipe_id": "diy_bismuth_lantern",
        "name": "Bismuth-Glass Geode Streetlamp",
        "category": "voxel_decor",
        "icon": "🏮",
        "placeable": True,
        "decor_color": "#32f5c8",
        "ingredients": {"spec_geode_bismuth": 1, "spec_geode_lodestone": 1},
        "favorite_of": ["enclave_01_hector", "enclave_02_jane"],
        "comfort_bonus": 5,
        "description": "Hand-brazed copper lantern housing a softly glowing captured-lightning geode core.",
    },
    {
        "recipe_id": "diy_cymatic_chime",
        "name": "Helmholtz Cymatic Wind-Chime",
        "category": "voxel_decor",
        "icon": "🎐",
        "placeable": True,
        "decor_color": "#e6ac55",
        "ingredients": {"spec_geode_piezo": 1, "spec_geode_lodestone": 1},
        "favorite_of": ["enclave_09_orion", "enclave_10_isla", "enclave_11_kenna", "enclave_12_elias"],
        "comfort_bonus": 6,
        "description": "Tuned brass tubes that ring in soothing fifth intervals during bifurcated valley breezes.",
    },
    {
        "recipe_id": "diy_resonant_terrarium",
        "name": "Bioluminescent Wardian Terrarium",
        "category": "voxel_decor",
        "icon": "🪴",
        "placeable": True,
        "decor_color": "#38e595",
        "ingredients": {"spec_flora_spore_orchid": 1, "spec_critter_soliton_firefly": 1},
        "favorite_of": ["enclave_06_zara", "enclave_08_terra", "enclave_14_vex"],
        "comfort_bonus": 6,
        "description": "Faceted glass case nurturing glowing mycelial moss and friendly soliton fireflies.",
    },
    {
        "recipe_id": "diy_bismuth_bench",
        "name": "Tempered Bismuth-Bronze Garden Bench",
        "category": "voxel_decor",
        "icon": "🪑",
        "placeable": True,
        "decor_color": "#c88732",
        "ingredients": {"spec_geode_lodestone": 1, "spec_flora_iron_wheat": 1},
        "favorite_of": ["enclave_03_silas", "enclave_12_elias", "enclave_15_dorian"],
        "comfort_bonus": 4,
        "description": "Ergonomic courtyard bench where Anchors and Prodigies swap stories over hot tea.",
    },
    {
        "recipe_id": "diy_alembic_still",
        "name": "Fractional Copper Yard Alembic",
        "category": "voxel_decor",
        "icon": "🏺",
        "placeable": True,
        "decor_color": "#ff9838",
        "ingredients": {"spec_geode_fulgurite": 1, "spec_flora_cave_truffle": 1},
        "favorite_of": ["enclave_07_willow", "enclave_16_elara"],
        "comfort_bonus": 7,
        "description": "Outdoor distillation coil that perfumes Willow's homestead with crisp pine resin and ozone.",
    },
    {
        "recipe_id": "diy_orchid_planter",
        "name": "Cedar & Copper Spore-Orchid Planter",
        "category": "voxel_decor",
        "icon": "🌷",
        "placeable": True,
        "decor_color": "#b066ff",
        "ingredients": {"spec_flora_spore_orchid": 1, "spec_flora_iron_wheat": 1},
        "favorite_of": ["enclave_08_terra", "enclave_11_kenna"],
        "comfort_bonus": 5,
        "description": "Raised chelated flower box bursting with pollinator-friendly exoplanet blooms.",
    },
    {
        "recipe_id": "theme_enclave_first_forge",
        "name": "First Forge Bismuth Anvil & Busbar Pedestal (SR-02 Tycoon)",
        "category": "voxel_decor",
        "synergy_id": "SR-02",
        "icon": "⚒️",
        "placeable": True,
        "decor_color": "#e6ac55",
        "ingredients": {"spec_geode_bismuth": 1, "spec_geode_lodestone": 1},
        "favorite_of": ["enclave_03_silas", "enclave_04_leo", "enclave_01_hector"],
        "comfort_bonus": 8,
        "description": "Cross-capsule SR-02 craft item shared with lfs-tycoon (theme_enclave_first_forge).",
    },
    {
        "recipe_id": "theme_enclave_living_atlas",
        "name": "Living Atlas Concordance Globe & Astrolabe (SR-02 Tycoon)",
        "category": "voxel_decor",
        "synergy_id": "SR-02",
        "icon": "🧭",
        "placeable": True,
        "decor_color": "#32f5c8",
        "ingredients": {"spec_geode_piezo": 1, "spec_geode_bismuth": 1},
        "favorite_of": ["enclave_14_vex", "enclave_15_dorian", "enclave_05_kaio"],
        "comfort_bonus": 8,
        "description": "Cross-capsule SR-02 craft item shared with lfs-tycoon (theme_enclave_living_atlas).",
    },
    {
        "recipe_id": "diy_feast_bread_basket",
        "name": "Warm Iron-Wheat Feast Basket",
        "category": "alchemy_gift",
        "icon": "🥖",
        "placeable": False,
        "ingredients": {"spec_flora_iron_wheat": 1, "spec_flora_cave_truffle": 1},
        "favorite_of": ["enclave_13_ryn", "enclave_16_elara", "enclave_01_hector", "enclave_05_kaio"],
        "comfort_bonus": 3,
        "description": "Freshly milled Crystalline Iron-Wheat loaves glazed with cave-truffle butter.",
    },
)

SQUAD_COLORS: dict[str, str] = {
    "The Forge": "#e67e22",
    "The Wilds": "#2ecc71",
    "The Mind": "#9b59b6",
    "The Hub": "#f1c40f",
}

CHARACTER_VISUAL_PROFILES: dict[str, dict[str, str]] = {
    "enclave_01_hector": {"icon": "⚡", "shirt": "#d35400", "hair": "#5d4037", "home_bldg": "proj_02_stormbreaker"},
    "enclave_02_jane": {"icon": "🧮", "shirt": "#2980b9", "hair": "#2c3e50", "home_bldg": "proj_02_stormbreaker"},
    "enclave_03_silas": {"icon": "🔧", "shirt": "#8c5220", "hair": "#bdc3c7", "home_bldg": "proj_01_first_forge"},
    "enclave_04_leo": {"icon": "⚒️", "shirt": "#c0392b", "hair": "#d5d8dc", "home_bldg": "proj_01_first_forge"},
    "enclave_05_kaio": {"icon": "🧭", "shirt": "#27ae60", "hair": "#3e2723", "home_bldg": "proj_03_sanctuary"},
    "enclave_06_zara": {"icon": "🦌", "shirt": "#16a085", "hair": "#4a235a", "home_bldg": "proj_03_sanctuary"},
    "enclave_07_willow": {"icon": "⚗️", "shirt": "#1abc9c", "hair": "#e5e8e8", "home_bldg": "bldg_willow_homestead"},
    "enclave_08_terra": {"icon": "🌱", "shirt": "#2e8b57", "hair": "#d7ccc8", "home_bldg": "proj_04_genesis_garden"},
    "enclave_09_orion": {"icon": "🎨", "shirt": "#8e44ad", "hair": "#34495e", "home_bldg": "proj_05_simulacrum"},
    "enclave_10_isla": {"icon": "📐", "shirt": "#5b2c6f", "hair": "#1c2833", "home_bldg": "proj_05_simulacrum"},
    "enclave_11_kenna": {"icon": "🕊️", "shirt": "#9b59b6", "hair": "#cfd8dc", "home_bldg": "proj_06_lyceum_of_the_mind"},
    "enclave_12_elias": {"icon": "📜", "shirt": "#6c3483", "hair": "#eaeded", "home_bldg": "proj_06_lyceum_of_the_mind"},
    "enclave_13_ryn": {"icon": "🍳", "shirt": "#e67e22", "hair": "#4e342e", "home_bldg": "proj_08_hearth_metabolic_engine"},
    "enclave_14_vex": {"icon": "🔭", "shirt": "#d4ac0d", "hair": "#212f3d", "home_bldg": "proj_07_living_atlas"},
    "enclave_15_dorian": {"icon": "🎻", "shirt": "#b7950b", "hair": "#d0d3d4", "home_bldg": "proj_07_living_atlas"},
    "enclave_16_elara": {"icon": "🩺", "shirt": "#f39c12", "hair": "#f2f4f4", "home_bldg": "proj_08_hearth_metabolic_engine"},
}

# ============================================================================
# 6. FIVE POKÉMON EMERALD (GEN-3 HOENN) OVERWORLD DISTRICTS & THREE INDOOR ROOMS
#    Distributes all 18 canonical buildings and 16 canonical citizens cleanly
#    so no single screen is overcrowded (2-5 landmarks and 1-5 citizens per zone).
# ============================================================================
ENCLAVE_EMERALD_DISTRICTS: dict[str, dict[str, Any]] = {
    "zone_01_homestead_grove": {
        "zone_id": "zone_01_homestead_grove",
        "name": "Littleroot Homestead & Genesis Grove",
        "hoenn_route_banner": "🌿 LITTLEROOT HOMESTEAD GROVE",
        "biome_id": "crater_valley",
        "hearth_biome": "Porch Hearth",
        "grid_width": 24,
        "grid_height": 18,
        "willow_spawn": {"x": 11, "y": 10},
        "buildings": [
            "bldg_willow_homestead",
            "proj_04_genesis_garden",
            "bldg_wilds_nook",
        ],
        "citizens": [
            "enclave_07_willow",
            "enclave_08_terra",
            "enclave_05_kaio",
        ],
        "enterable_rooms": ["room_willow_home"],
        "connections": {
            "east": "zone_02_hearth_plaza",
            "south": "zone_04_ferro_pier",
            "north": "zone_03_atlas_terrace",
        },
        "description": (
            "Lush Hoenn-style starter grove centering on Willow's emerald-roofed Alchemist Homestead, "
            "Terra's Genesis Garden Conservatory, jumpable ledges, and rustling spore-grass."
        ),
    },
    "zone_02_hearth_plaza": {
        "zone_id": "zone_02_hearth_plaza",
        "name": "Mauville Hearth & Metabolic Plaza",
        "hoenn_route_banner": "🍲 MAUVILLE HEARTH PLAZA",
        "biome_id": "crater_valley",
        "hearth_biome": "Porch Hearth",
        "grid_width": 24,
        "grid_height": 18,
        "willow_spawn": {"x": 5, "y": 10},
        "buildings": [
            "proj_08_hearth_metabolic_engine",
            "bldg_sibling_post",
            "bldg_curio_pavilion",
            "bldg_hub_gables",
        ],
        "citizens": [
            "enclave_13_ryn",
            "enclave_16_elara",
            "enclave_09_orion",
        ],
        "enterable_rooms": ["room_hearth_galley"],
        "connections": {
            "west": "zone_01_homestead_grove",
            "north": "zone_03_atlas_terrace",
            "east": "zone_05_forge_summit",
            "south": "zone_04_ferro_pier",
        },
        "description": (
            "Bustling cobble plaza anchored by Ryn and Elara's crimson-roofed Hearth Galley, "
            "the Sibling Grid Pneumatic Notice Board, and Aegis Curio Pavilion."
        ),
    },
    "zone_03_atlas_terrace": {
        "zone_id": "zone_03_atlas_terrace",
        "name": "Lilycove Living Atlas & Mind Terrace",
        "hoenn_route_banner": "🏛️ LILYCOVE ATLAS TERRACE",
        "biome_id": "genesis_terraces",
        "hearth_biome": "Flow Hourglass",
        "grid_width": 24,
        "grid_height": 18,
        "willow_spawn": {"x": 12, "y": 14},
        "buildings": [
            "proj_07_living_atlas",
            "proj_05_simulacrum",
            "proj_06_lyceum_of_the_mind",
            "bldg_mind_loft",
            "bldg_prodigy_west",
        ],
        "citizens": [
            "enclave_15_dorian",
            "enclave_14_vex",
            "enclave_10_isla",
            "enclave_11_kenna",
            "enclave_12_elias",
        ],
        "enterable_rooms": ["room_atlas_museum"],
        "connections": {
            "south": "zone_02_hearth_plaza",
            "west": "zone_01_homestead_grove",
            "east": "zone_05_forge_summit",
        },
        "description": (
            "Elevated sapphire-roofed museum terrace housing Dorian and Vex's Living Atlas Colony Museum, "
            "the Simulacrum Rotunda, and the Lyceum of the Mind."
        ),
    },
    "zone_04_ferro_pier": {
        "zone_id": "zone_04_ferro_pier",
        "name": "Slateport Ferrofluid Basin Pier & Sanctuary",
        "hoenn_route_banner": "🌊 SLATEPORT FERROFLUID PIER",
        "biome_id": "spore_glade",
        "hearth_biome": "Rain Garden",
        "grid_width": 24,
        "grid_height": 18,
        "willow_spawn": {"x": 11, "y": 5},
        "buildings": [
            "bldg_ferro_pier",
            "proj_03_sanctuary",
        ],
        "citizens": [
            "enclave_06_zara",
        ],
        "enterable_rooms": [],
        "connections": {
            "north": "zone_01_homestead_grove",
            "east": "zone_02_hearth_plaza",
        },
        "description": (
            "Cerulean ferrofluid waterfront with white shoreline foam, brass-railed angling pier, "
            "and Zara's Magnetotropic Fauna Sanctuary."
        ),
    },
    "zone_05_forge_summit": {
        "zone_id": "zone_05_forge_summit",
        "name": "Lavaridge First Forge & Stormbreaker Summit",
        "hoenn_route_banner": "🌋 LAVARIDGE FORGE SUMMIT",
        "biome_id": "forge_caldera",
        "hearth_biome": "Alchemist Crucible",
        "grid_width": 24,
        "grid_height": 18,
        "willow_spawn": {"x": 5, "y": 11},
        "buildings": [
            "proj_01_first_forge",
            "proj_02_stormbreaker",
            "bldg_forge_lodge",
            "bldg_prodigy_east",
        ],
        "citizens": [
            "enclave_03_silas",
            "enclave_04_leo",
            "enclave_01_hector",
            "enclave_02_jane",
        ],
        "enterable_rooms": [],
        "connections": {
            "west": "zone_02_hearth_plaza",
            "north": "zone_03_atlas_terrace",
        },
        "description": (
            "Obsidian-and-gold caldera ridge where Silas and Leo tend The First Forge busbars "
            "and Hector and Jane harvest lightning at The Stormbreaker Spire."
        ),
    },
}

ENCLAVE_INDOOR_ROOMS: dict[str, dict[str, Any]] = {
    "room_willow_home": {
        "room_id": "room_willow_home",
        "name": "Willow's Alchemist Homestead Interior",
        "hoenn_route_banner": "🏡 WILLOW'S ALCHEMIST LAB",
        "parent_zone_id": "zone_01_homestead_grove",
        "parent_building_id": "bldg_willow_homestead",
        "hearth_biome": "Alchemist Crucible",
        "grid_width": 14,
        "grid_height": 10,
        "entry_spawn": {"x": 7, "y": 8},
        "exit_spawn": {"zone_id": "zone_01_homestead_grove", "x": 8, "y": 10},
        "residents": ["enclave_07_willow"],
        "interactive_props": [
            "Copper Alembic Workbench (DIY Crafting)",
            "Steampunk Wardrobe Mirror (SR-08 Bridge)",
            "Blackberry Cordial Gourd Shelf",
            "Porch Hearth Fireplace",
        ],
    },
    "room_hearth_galley": {
        "room_id": "room_hearth_galley",
        "name": "The Hearth & Metabolic Galley Interior",
        "hoenn_route_banner": "🍲 RYN & ELARA'S HEARTH GALLEY",
        "parent_zone_id": "zone_02_hearth_plaza",
        "parent_building_id": "proj_08_hearth_metabolic_engine",
        "hearth_biome": "Porch Hearth",
        "grid_width": 16,
        "grid_height": 11,
        "entry_spawn": {"x": 8, "y": 9},
        "exit_spawn": {"zone_id": "zone_02_hearth_plaza", "x": 11, "y": 10},
        "residents": ["enclave_13_ryn", "enclave_16_elara"],
        "interactive_props": [
            "Iron-Wheat Steam Oven",
            "Long Feast Convergence Table (Law L13)",
            "Elara's Herbal Apothecary Counter",
            "Whistling Kettle Pressure Gauge (3-Sol Prank)",
        ],
    },
    "room_atlas_museum": {
        "room_id": "room_atlas_museum",
        "name": "Living Atlas Observatory & Colony Museum Hall",
        "hoenn_route_banner": "🏛️ LIVING ATLAS MUSEUM HALL",
        "parent_zone_id": "zone_03_atlas_terrace",
        "parent_building_id": "proj_07_living_atlas",
        "hearth_biome": "Flow Hourglass",
        "grid_width": 16,
        "grid_height": 11,
        "entry_spawn": {"x": 8, "y": 9},
        "exit_spawn": {"zone_id": "zone_03_atlas_terrace", "x": 11, "y": 10},
        "residents": ["enclave_15_dorian", "enclave_14_vex"],
        "interactive_props": [
            "Captured Geodes Wing Pedestal",
            "Magneto-Critter Vivarium",
            "Ferro-Basin Aquarium Tank",
            "Concordance Epistemic Archive Desk (SR-05)",
        ],
    },
}

# ============================================================================
# 7. SIX-STEP GUIDED POKÉMON EMERALD ONBOARDING TUTORIAL
# ============================================================================
ENCLAVE_ONBOARDING_TUTORIAL_STEPS: tuple[dict[str, Any], ...] = (
    {
        "step_index": 1,
        "step_id": "STEP_1_MEET_SOREN",
        "title": "Meet Mentor Soren & Terra by Your Porch",
        "zone_id": "zone_01_homestead_grove",
        "required_action": "advance_tutorial",
        "target_entity_id": "enclave_08_terra",
        "target_x": 12,
        "target_y": 9,
        "rup_reward": 5,
        "prompt": (
            "Step 1/6: Walk with [WASD / Arrows] to Mentor Soren & Terra by your porch "
            "and press [Z / E / Space]"
        ),
        "dialogue": (
            "Welcome to Littleroot Homestead Grove, Willow! Mentor Soren (Silas) and Terra have "
            "calibrated your 6 Alchemist Tools. Let's test your Copper Trowel on a resonant geode fissure!"
        ),
    },
    {
        "step_index": 2,
        "step_id": "STEP_2_DIG_GEODE",
        "title": "Unearth the Glowing Bismuth Geode Fissure",
        "zone_id": "zone_01_homestead_grove",
        "required_action": "forage_dig",
        "target_entity_id": "node_geode_01",
        "target_x": 15,
        "target_y": 11,
        "rup_reward": 5,
        "prompt": (
            "Step 2/6: Equip [1] Copper Trowel, walk to the glowing ✦ Geode Fissure, "
            "and press [Z / E / Space] to dig"
        ),
        "dialogue": (
            "Splendid chelation! You unearthed a Hopper-Crystal Bismuth Geode and an aromatic Cave-Truffle. "
            "Next, let's irrigate the Crystalline Iron-Wheat sprouts!"
        ),
    },
    {
        "step_index": 3,
        "step_id": "STEP_3_WATER_SPROUT",
        "title": "Irrigate Crystalline Iron-Wheat Sprouts",
        "zone_id": "zone_01_homestead_grove",
        "required_action": "water_crop",
        "target_entity_id": "node_crop_01",
        "target_x": 7,
        "target_y": 12,
        "rup_reward": 5,
        "prompt": (
            "Step 3/6: Press [4] for Distilled Rainwater Can and water the 🌱 Iron-Wheat Plot "
            "with [Z / E / Space]"
        ),
        "dialogue": (
            "The Crystalline Iron-Wheat is singing in 432 Hz resonance! Look—an Aurora Prism-Moth "
            "just fluttered into the tall spore-grass!"
        ),
    },
    {
        "step_index": 4,
        "step_id": "STEP_4_CATCH_MOTH",
        "title": "Catch an Aurora Prism-Moth in the Spore Grass",
        "zone_id": "zone_01_homestead_grove",
        "required_action": "catch_critter",
        "target_entity_id": "node_critter_01",
        "target_x": 17,
        "target_y": 7,
        "rup_reward": 5,
        "prompt": (
            "Step 4/6: Press [2] for Magnetotropic Bug Net and catch the fluttering 🦋 Prism-Moth "
            "with [Z / E / Space]"
        ),
        "dialogue": (
            "Gentle sweep! You cataloged an Aurora Prism-Moth without disturbing its magnetite antennae. "
            "Now head East to Mauville Hearth Plaza to greet Chef Ryn!"
        ),
    },
    {
        "step_index": 5,
        "step_id": "STEP_5_PLAZA_MEET_RYN",
        "title": "Visit Hearth Plaza & Share a Tonic with Ryn",
        "zone_id": "zone_02_hearth_plaza",
        "required_action": "gift_citizen",
        "target_entity_id": "enclave_13_ryn",
        "target_x": 11,
        "target_y": 10,
        "rup_reward": 10,
        "prompt": (
            "Step 5/6: Travel East to Hearth Plaza, equip [6] Gift Satchel, and share a tonic "
            "with Chef Ryn [Z / E / Space]"
        ),
        "dialogue": (
            "Ryn beamed and handed you a warm Crystalline Iron-Wheat roll! Finally, visit the "
            "Living Atlas Museum or your Homestead Alembic to archive your specimen!"
        ),
    },
    {
        "step_index": 6,
        "step_id": "STEP_6_MUSEUM_OR_HOMESTEAD",
        "title": "Donate to the Living Atlas Museum or Craft at Home",
        "zone_id": "zone_03_atlas_terrace",
        "required_action": "donate_museum",
        "target_entity_id": "proj_07_living_atlas",
        "target_x": 11,
        "target_y": 9,
        "rup_reward": 15,
        "prompt": (
            "Step 6/6: Donate your specimen at the Living Atlas Museum or craft DIY decor "
            "via the [START] Menu!"
        ),
        "dialogue": (
            "Congratulations, Willow! You've mastered all 6 Alchemist Tools and unlocked full "
            "free-roam across all 5 Hoenn Districts and 3 Indoor Rooms of The Enclave!"
        ),
    },
)


def _building_zone_id(building_id: str) -> str:
    for zid, zspec in ENCLAVE_EMERALD_DISTRICTS.items():
        if building_id in zspec["buildings"]:
            return zid
    return "zone_01_homestead_grove"


def _citizen_zone_id(character_id: str) -> str:
    for zid, zspec in ENCLAVE_EMERALD_DISTRICTS.items():
        if character_id in zspec["citizens"]:
            return zid
    return "zone_01_homestead_grove"


def _sanitize_pve_text(text: str) -> str:
    """Guarantee Law L11 compliance by scrubbing any accidental hostile keyword."""
    cleaned = str(text)
    for kw in HOSTILE_PVE_KEYWORDS:
        if kw in cleaned.lower():
            cleaned = cleaned.replace(kw, "friction").replace(kw.capitalize(), "Friction")
    return cleaned


def _build_initial_daily_favors(colony_sol: int) -> list[dict[str, Any]]:
    """Construct 3 deterministic non-monetary Daily Bulletin Board Favors (Law L12)."""
    return [
        {
            "favor_id": f"favor_sol_{colony_sol:03d}_silas_liniment",
            "requester_id": "enclave_03_silas",
            "requester_name": "Silas (The Engineer)",
            "title": "Warm Joint-Liniment for the Busbar Shift",
            "description": (
                "Silas's knuckles are stiff from calibrating the bismuth-bronze busbars in the morning frost. "
                "Deliver an Herbal Joint-Liniment Vial or cave-truffle salve to The First Forge."
            ),
            "requested_item_id": "diy_herbal_liniment",
            "fallback_specimen_id": "spec_flora_cave_truffle",
            "bond_delta": 0.05,
            "stress_delta": -0.10,
            "meta_rup_reward": 10,
            "completed": False,
        },
        {
            "favor_id": f"favor_sol_{colony_sol:03d}_terra_chelation",
            "requester_id": "enclave_08_terra",
            "requester_name": "Terra (The Gardener)",
            "title": "Chelation Catalyst for Iron-Wheat Batch #14",
            "description": (
                "Terra needs reduced sulfur and fulgurite chelation drops to protect the new Crystalline "
                "Iron-Wheat seedlings from ridge-frost lockup."
            ),
            "requested_item_id": "diy_chelation_elixir",
            "fallback_specimen_id": "spec_geode_fulgurite",
            "bond_delta": 0.05,
            "stress_delta": -0.10,
            "meta_rup_reward": 10,
            "completed": False,
        },
        {
            "favor_id": f"favor_sol_{colony_sol:03d}_dorian_museum",
            "requester_id": "enclave_15_dorian",
            "requester_name": "Dorian & Vex (The Living Atlas)",
            "title": "Catalog a Fresh Crater Specimen",
            "description": (
                "Dorian and Vex are updating the Living Atlas Concordance before tonight's Evening Dispatch. "
                "Forage or angle any specimen and donate it to the Colony Museum."
            ),
            "requested_item_id": "ANY_SPECIMEN",
            "fallback_specimen_id": "spec_geode_bismuth",
            "bond_delta": 0.04,
            "stress_delta": -0.08,
            "meta_rup_reward": 10,
            "completed": False,
        },
    ]


def generate_enclave_city_state(
    repo_root: Path | str | None = None,
    seed: str = "enclave_sol_001",
    biome_id: str = "crater_valley",
) -> dict[str, Any]:
    """Generate a deterministic 48x48 2.5D Voxel City & Willow Animal Crossing Companion state.

    Reuses `engine.chronosphere`, `engine.magneto_weather`, `engine.state_ode`,
    and `engine.drama_director` directly rather than reinventing parallel simulation physics.
    """
    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
    selected_biome_id = biome_id if biome_id in ENCLAVE_BIOMES else "crater_valley"
    biome = copy.deepcopy(ENCLAVE_BIOMES[selected_biome_id])

    # Load canonical character cores
    cores_by_id: dict[str, dict[str, Any]] = {}
    char_dir = root / "canon" / "characters"
    for p in sorted(char_dir.glob("*.core.json")):
        card = json.loads(p.read_text(encoding="utf-8"))
        cid = str(card["agent_identity"]["character_id"])
        cores_by_id[cid] = card

    # Load Grand Projects
    gp_path = root / "canon" / "projects" / "grand_projects.json"
    gp_data = json.loads(gp_path.read_text(encoding="utf-8"))
    projects_by_id: dict[str, dict[str, Any]] = {}
    for proj in gp_data.get("projects") or []:
        projects_by_id[str(proj["project_id"])] = proj

    # Load Lorebook
    lore_path = root / "canon" / "lore_cards" / "lorebook.json"
    lore_data = json.loads(lore_path.read_text(encoding="utf-8"))
    lore_entries = lore_data.get("entries") or []

    # Load 120-Pair Relationship Matrix
    rel_path = root / "relationships" / "initial_matrix_120.json"
    rel_data = json.loads(rel_path.read_text(encoding="utf-8"))
    pairs = rel_data.get("pairs") or []

    # Reuse engine.chronosphere & engine.magneto_weather directly
    latest_path = root / "snapshots" / "latest.json"
    latest_snap: dict[str, Any] = {}
    if latest_path.is_file():
        try:
            latest_snap = json.loads(latest_path.read_text(encoding="utf-8"))
        except Exception:
            latest_snap = {}

    tick_id = int(latest_snap.get("tick_id", 1) or 1)
    chrono = (
        initial_chronosphere(epoch_seed=seed)
        if tick_id <= 1
        else build_chronosphere_for_tick(tick_id=tick_id, epoch_seed=seed)
    )
    colony_sol = int(latest_snap.get("colony_sol", chrono["colony_sol"]) or chrono["colony_sol"])
    day_phase = str(latest_snap.get("day_phase") or chrono["day_phase"])
    weather = compute_exoplanet_weather(
        tick_id=tick_id,
        colony_sol=colony_sol,
        day_phase=day_phase,
        epoch_seed=seed,
    )
    kp_exo = float(weather["kp_exo"])
    drama_beat = evaluate_pacing_and_beat(
        recent_events=[],
        colony_sol=colony_sol,
        day_phase=day_phase,
    )
    snap_states = latest_snap.get("character_states") if isinstance(latest_snap.get("character_states"), dict) else {}

    # Build bond lookup per character
    bonds_by_char: dict[str, dict[str, float]] = {cid: {} for cid in CANONICAL_16_CHARACTER_IDS}
    for pair in pairs:
        ca = str(pair.get("character_a") or pair.get("agent_a") or "")
        cb = str(pair.get("character_b") or pair.get("agent_b") or "")
        bs = round(min(1.0, max(0.35, float(pair.get("bond_strength", 0.75) or 0.75))), 3)
        if ca in bonds_by_char and cb in bonds_by_char:
            bonds_by_char[ca][cb] = bs
            bonds_by_char[cb][ca] = bs

    # Build 18 Voxel Buildings with enriched Grand Project metadata
    buildings: list[dict[str, Any]] = []
    buildings_by_id: dict[str, dict[str, Any]] = {}
    for b_spec in ENCLAVE_BUILDINGS:
        b_item = copy.deepcopy(b_spec)
        b_item["zone_id"] = _building_zone_id(str(b_item["building_id"]))
        pid = b_item.get("project_id")
        if pid and pid in projects_by_id:
            proj = projects_by_id[pid]
            b_item["project_progress_pct"] = float(proj.get("current_progress_pct", 50.0))
            b_item["central_scientific_question"] = str(proj.get("central_scientific_question") or "")
            b_item["thematic_resonance"] = str(proj.get("thematic_resonance") or "")
        else:
            b_item["project_progress_pct"] = 100.0
            b_item["central_scientific_question"] = "Community comfort, companionship, and alchemical craft."
            b_item["thematic_resonance"] = "Turns the crater valley into a warm, playable home."
        buildings.append(b_item)
        buildings_by_id[str(b_item["building_id"])] = b_item

    # Build 16 Canonical Citizens using `engine.state_ode.sample_character_state`
    citizens: list[dict[str, Any]] = []
    for idx, cid in enumerate(CANONICAL_16_CHARACTER_IDS):
        core = cores_by_id[cid]
        ident = core["agent_identity"]
        b5 = core["tier_1_causal_trait_distributions"]["big_five_distributions"]
        t3 = core["tier_3_momentary_state_and_override_physics"]
        t4 = core["tier_4_self_concept_and_narrative_arc"]
        lens = t4["cognitive_lens"]
        voice = t4["voice_and_syntax_anchors"]
        arc = t4["narrative_arc"]
        vis = CHARACTER_VISUAL_PROFILES[cid]

        home_bldg = buildings_by_id.get(vis["home_bldg"], buildings[0])
        spawn_x = int(home_bldg["x"] + (idx % 3) - 1)
        spawn_y = int(home_bldg["y"] + int(home_bldg["d"]) + 1)
        spawn_x = max(2, min(GRID_SIZE - 3, spawn_x))
        spawn_y = max(2, min(GRID_SIZE - 3, spawn_y))

        prev_st = snap_states.get(cid) if isinstance(snap_states.get(cid), dict) else (t3.get("current_state_vector") or {})
        ode_state = sample_character_state(
            core_card=core,
            prev_state=prev_st,
            world_slice=weather,
            active_situation={
                "tick_id": tick_id,
                "colony_sol": colony_sol,
                "day_phase": day_phase,
                "event_type": drama_beat["event_type"],
                "location": biome["canonical_biome_cell"],
            },
            rng_seed=f"{seed}:tick{tick_id:04d}:{cid}",
        )

        quotes = list(voice.get("pinned_example_dialogues") or [])
        default_quote = quotes[0].strip('"') if quotes else voice.get("tagline", "Working on our Grand Project.")

        citizen_obj = {
            "character_id": cid,
            "name": str(ident["name"]),
            "epithet": str(ident["epithet"]),
            "squad": str(ident["squad"]),
            "squad_color": SQUAD_COLORS.get(str(ident["squad"]), "#32f5c8"),
            "dialectic_role": str(ident["dialectic_role"]),
            "age_years": int(ident["age_years"]),
            "grand_project": str(ident["grand_project"]),
            "grand_project_partner": str(ident["grand_project_partner"]),
            "mbti_type": str(lens["mbti_type"]),
            "enneagram": str(lens["enneagram_self_concept"]),
            "problem_solving_lens": str(lens["problem_solving_lens"]),
            "tagline": str(voice["tagline"]),
            "default_quote": default_quote,
            "formative_memory": str(arc["formative_memory"]),
            "genius_vs_mundane": str(arc["genius_vs_mundane_frustration"]),
            "polarity_inversion_profile": copy.deepcopy(t3["polarity_inversion_profile"]),
            "ocean_mean": {
                "openness": float(b5["openness"]["mean"]),
                "conscientiousness": float(b5["conscientiousness"]["mean"]),
                "extraversion": float(b5["extraversion"]["mean"]),
                "agreeableness": float(b5["agreeableness"]["mean"]),
                "neuroticism": float(b5["neuroticism"]["mean"]),
            },
            "trait_states": ode_state["trait_states"],
            "triggered_caps_rules": ode_state["triggered_caps_rules"],
            "behavioral_directives": ode_state["behavioral_directives"],
            "stress": round(float(ode_state["stress"]), 3),
            "fatigue": round(float(ode_state["fatigue"]), 3),
            "polarity_inversion_active": bool(ode_state["polarity_inversion_active"]),
            "x": float(spawn_x),
            "y": float(spawn_y),
            "zone_id": _citizen_zone_id(cid),
            "home_building_id": vis["home_bldg"],
            "icon": vis["icon"],
            "shirt_color": vis["shirt"],
            "hair_color": vis["hair"],
            "is_player_companion": cid == "enclave_07_willow",
            "willow_bond": float(bonds_by_char["enclave_07_willow"].get(cid, 1.0 if cid == "enclave_07_willow" else 0.78)),
            "bonds": bonds_by_char[cid],
            "current_activity": (
                ode_state["behavioral_directives"][0]
                if ode_state["behavioral_directives"]
                else f"Advancing {ident['grand_project']} ({day_phase})"
            ),
        }
        citizens.append(citizen_obj)

    # Compute sample domain friction between Willow (The Wilds) and Silas (The Forge) using engine.state_ode
    willow_ocean = list(citizens[6]["ocean_mean"].values())
    silas_ocean = list(citizens[2]["ocean_mean"].values())
    willow_silas_friction = compute_domain_friction(willow_ocean, silas_ocean)

    # Interactive Resource Nodes on the 48x48 Voxel Map
    resource_nodes: list[dict[str, Any]] = [
        {"node_id": "node_geode_01", "node_type": "geode_crack", "x": 35, "y": 11, "specimen_id": "spec_geode_bismuth", "active": True},
        {"node_id": "node_geode_02", "node_type": "geode_crack", "x": 40, "y": 10, "specimen_id": "spec_geode_fulgurite", "active": True},
        {"node_id": "node_geode_03", "node_type": "geode_crack", "x": 12, "y": 12, "specimen_id": "spec_geode_piezo", "active": True},
        {"node_id": "node_geode_04", "node_type": "geode_crack", "x": 28, "y": 13, "specimen_id": "spec_geode_lodestone", "active": True},
        {"node_id": "node_truffle_05", "node_type": "geode_crack", "x": 9, "y": 30, "specimen_id": "spec_flora_cave_truffle", "active": True},
        {"node_id": "node_critter_01", "node_type": "critter_swarm", "x": 14, "y": 29, "specimen_id": "spec_critter_prism_moth", "active": True},
        {"node_id": "node_critter_02", "node_type": "critter_swarm", "x": 19, "y": 26, "specimen_id": "spec_critter_soliton_firefly", "active": True},
        {"node_id": "node_critter_03", "node_type": "critter_swarm", "x": 10, "y": 36, "specimen_id": "spec_critter_cave_beetle", "active": True},
        {"node_id": "node_critter_04", "node_type": "critter_swarm", "x": 25, "y": 31, "specimen_id": "spec_critter_bismuth_dragonfly", "active": True},
        {"node_id": "node_fish_01", "node_type": "ferro_fish_shadow", "x": 23, "y": 35, "specimen_id": "spec_fish_ammonite", "active": True},
        {"node_id": "node_fish_02", "node_type": "ferro_fish_shadow", "x": 26, "y": 34, "specimen_id": "spec_fish_rosensweig_eel", "active": True},
        {"node_id": "node_fish_03", "node_type": "ferro_fish_shadow", "x": 19, "y": 33, "specimen_id": "spec_fish_colloidal_pike", "active": True},
        {"node_id": "node_fish_04", "node_type": "ferro_fish_shadow", "x": 29, "y": 35, "specimen_id": "spec_fish_fulgurite_crab", "active": True},
        {"node_id": "node_crop_01", "node_type": "crop_plot", "x": 12, "y": 29, "specimen_id": "spec_flora_iron_wheat", "watered": False, "active": True},
        {"node_id": "node_crop_02", "node_type": "crop_plot", "x": 13, "y": 29, "specimen_id": "spec_flora_spore_orchid", "watered": False, "active": True},
        {"node_id": "node_crop_03", "node_type": "crop_plot", "x": 14, "y": 29, "specimen_id": "spec_flora_iron_wheat", "watered": True, "active": True},
    ]

    placed_decorations: list[dict[str, Any]] = [
        {
            "decor_id": "decor_init_01",
            "recipe_id": "diy_bismuth_lantern",
            "name": "Bismuth-Glass Geode Streetlamp",
            "icon": "🏮",
            "x": 20,
            "y": 29,
            "color": "#32f5c8",
            "comfort_bonus": 5,
        },
        {
            "decor_id": "decor_init_02",
            "recipe_id": "diy_alembic_still",
            "name": "Fractional Copper Yard Alembic",
            "icon": "🏺",
            "x": 15,
            "y": 31,
            "color": "#ff9838",
            "comfort_bonus": 7,
        },
        {
            "decor_id": "decor_init_03",
            "recipe_id": "theme_enclave_first_forge",
            "name": "First Forge Bismuth Anvil & Busbar Pedestal (SR-02 Tycoon)",
            "icon": "⚒️",
            "x": 24,
            "y": 20,
            "color": "#e6ac55",
            "comfort_bonus": 8,
        },
    ]

    willow_inventory: dict[str, int] = {
        "spec_geode_lodestone": 2,
        "spec_geode_bismuth": 1,
        "spec_geode_fulgurite": 1,
        "spec_flora_cave_truffle": 2,
        "spec_flora_iron_wheat": 2,
        "spec_flora_spore_orchid": 1,
        "spec_critter_soliton_firefly": 1,
        "diy_herbal_liniment": 1,
        "diy_blackberry_cordial": 1,
        "theme_enclave_first_forge": 1,
        "theme_enclave_living_atlas": 1,
    }

    museum_donated_ids: list[str] = [
        "spec_geode_lodestone",
        "spec_flora_iron_wheat",
    ]

    story_feed: list[dict[str, Any]] = [
        {
            "feed_id": "feed_init_01",
            "sol": colony_sol,
            "day_phase": day_phase,
            "category": "COMPANION_AWAKENING",
            "title": "Willow Lights Her Copper Alembic",
            "summary": (
                f"Under {weather['micro_climate_regime']} (Kp={kp_exo}), Willow adjusted her brass-rimmed "
                f"spectacles in her Alchemist Homestead and stepped out into the Enclave Crater Valley."
            ),
            "actors": ["enclave_07_willow", "enclave_08_terra"],
            "science_vegetable": drama_beat["science_vegetable"],
            "lethality": 0,
        },
        {
            "feed_id": "feed_init_02",
            "sol": colony_sol,
            "day_phase": day_phase,
            "category": "GRAND_PROJECT_SYNC",
            "title": "Sixteen Specialists Across Four Squads",
            "summary": (
                "Silas and Hector calibrated The First Forge busbars while Dorian and Vex prepared the "
                "Living Atlas Museum wings across all 4 epistemic tiers."
            ),
            "actors": ["enclave_03_silas", "enclave_01_hector", "enclave_15_dorian", "enclave_14_vex"],
            "science_vegetable": drama_beat["science_vegetable"],
            "lethality": 0,
        },
    ]

    city_state: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "project_id": "PA-15",
        "capsule_id": "enclave-digital-twin",
        "seed": seed,
        "grid_size": GRID_SIZE,
        "colony_sol": colony_sol,
        "tick_id": tick_id,
        "day_phase": day_phase,
        "kp_exo": round(kp_exo, 2),
        "chronosphere": chrono,
        "weather": weather,
        "drama_beat": drama_beat,
        "willow_silas_domain_friction": willow_silas_friction,
        "active_biome_id": selected_biome_id,
        "active_biome": biome,
        "biomes_catalog": copy.deepcopy(ENCLAVE_BIOMES),
        "active_zone_id": "zone_01_homestead_grove",
        "active_indoor_room_id": None,
        "emerald_districts": copy.deepcopy(ENCLAVE_EMERALD_DISTRICTS),
        "indoor_rooms": copy.deepcopy(ENCLAVE_INDOOR_ROOMS),
        "onboarding_tutorial": {
            "steps": copy.deepcopy(list(ENCLAVE_ONBOARDING_TUTORIAL_STEPS)),
            "current_step_index": 1,
            "current_step_id": ENCLAVE_ONBOARDING_TUTORIAL_STEPS[0]["step_id"],
            "completed_step_ids": [],
            "completed": False,
        },
        "crucible_hearth_biomes": list(CRUCIBLE_ELEMENTAL_HEARTH_BIOMES),
        "living_atlas_epistemic_tiers": list(DADS_BOOK_LORE_EPISTEMIC_TIERS),
        "tycoon_crafting_themes": list(LFS_TYCOON_CRAFTING_THEMES),
        "cross_capsule_synergies": copy.deepcopy(SUITE_SYNERGY_ATLAS),
        "buildings": buildings,
        "citizens": citizens,
        "willow_companion": {
            "character_id": "enclave_07_willow",
            "name": "Willow",
            "epithet": "The Alchemist",
            "control_mode": "PLAYER_CONTROL",
            "equipped_tool_id": "trowel",
            "tools": copy.deepcopy(list(WILLOW_AC_TOOLS)),
            "inventory": willow_inventory,
            "unlocked_diy_recipes": [r["recipe_id"] for r in DIY_RECIPES],
            "homestead_building_id": "bldg_willow_homestead",
            "homestead_comfort_score": 82 + sum(int(d["comfort_bonus"]) for d in placed_decorations),
        },
        "diy_recipes": copy.deepcopy(list(DIY_RECIPES)),
        "museum": {
            "building_id": "proj_07_living_atlas",
            "curators": ["enclave_15_dorian", "enclave_14_vex"],
            "epistemic_tiers": list(DADS_BOOK_LORE_EPISTEMIC_TIERS),
            "catalog": copy.deepcopy(list(MUSEUM_CATALOG)),
            "donated_specimen_ids": museum_donated_ids,
            "total_specimens": len(MUSEUM_CATALOG),
        },
        "daily_favors": _build_initial_daily_favors(colony_sol),
        "resource_nodes": resource_nodes,
        "placed_decorations": placed_decorations,
        "shadow_prank_ledger": [],
        "matured_prank_events": [],
        "story_feed": story_feed,
        "lore_highlights": [
            {"card_id": str(e.get("card_id")), "title": str(e.get("title")), "entry": str(e.get("entry"))}
            for e in lore_entries[:8]
        ],
        "meta_Economy": {
            "currency_code": "RUP",
            "cmy_gem_tiers": list(OASIS_CMY_RUPEE_TIERS),
            "bridge_global": "window.ArcadeAssetBridge",
            "in_world_economy_monetary": False,
            "city_rupee_bonus": 25,
            "total_actions_performed": 0,
        },
    }
    return city_state


def advance_city_tick(
    city_state: dict[str, Any],
    repo_root: Path | str | None = None,
) -> dict[str, Any]:
    """Advance the city state by 1 tick (+6h) using canonical `chronosphere`, `magneto_weather`,
    `drama_director`, `state_ode`, and `shadow_economy` modules."""
    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
    seed = str(city_state.get("seed") or "enclave_sol_001")
    next_chrono = advance_tick(city_state.get("chronosphere") or {}, epoch_seed=seed)
    tick_id = int(next_chrono["tick_id"])
    colony_sol = int(next_chrono["colony_sol"])
    day_phase = str(next_chrono["day_phase"])

    weather = compute_exoplanet_weather(
        tick_id=tick_id,
        colony_sol=colony_sol,
        day_phase=day_phase,
        epoch_seed=seed,
    )
    beat = evaluate_pacing_and_beat(
        recent_events=city_state.get("story_feed") or [],
        colony_sol=colony_sol,
        day_phase=day_phase,
    )

    city_state["chronosphere"] = next_chrono
    city_state["weather"] = weather
    city_state["drama_beat"] = beat
    city_state["tick_id"] = tick_id
    city_state["colony_sol"] = colony_sol
    city_state["day_phase"] = day_phase
    city_state["kp_exo"] = float(weather["kp_exo"])

    # Process 3-Sol Shadow Economy ledger via engine.shadow_economy.process_shadow_ledger
    pending_pranks, matured_pranks = process_shadow_ledger(
        city_state.get("shadow_prank_ledger") or [],
        current_sol=colony_sol,
    )
    city_state["shadow_prank_ledger"] = pending_pranks
    if matured_pranks:
        city_state.setdefault("matured_prank_events", []).extend(matured_pranks)

    # Sample character states via engine.state_ode.sample_character_state if core cards are available
    char_dir = root / "canon" / "characters"
    if char_dir.is_dir():
        for cit in city_state.get("citizens") or []:
            cid = str(cit["character_id"])
            cpath = char_dir / f"{cid}.core.json"
            if cpath.is_file():
                core_card = json.loads(cpath.read_text(encoding="utf-8"))
                sampled = sample_character_state(
                    core_card=core_card,
                    prev_state=cit,
                    world_slice=weather,
                    active_situation={
                        "tick_id": tick_id,
                        "colony_sol": colony_sol,
                        "day_phase": day_phase,
                        "event_type": beat["event_type"],
                    },
                    rng_seed=f"{seed}:tick{tick_id:04d}:{cid}",
                )
                cit["stress"] = round(float(sampled["stress"]), 3)
                cit["fatigue"] = round(float(sampled["fatigue"]), 3)
                cit["trait_states"] = sampled["trait_states"]
                cit["triggered_caps_rules"] = sampled["triggered_caps_rules"]
                cit["polarity_inversion_active"] = bool(sampled["polarity_inversion_active"])

    return summarize_enclave_city_state(city_state)


def perform_willow_ac_action(
    city_state: dict[str, Any],
    action_type: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Deterministically execute an Animal Crossing companion action or colony catalyst on `city_state`."""
    params = payload or {}
    willow = city_state["willow_companion"]
    inv: dict[str, int] = willow["inventory"]
    meta_econ = city_state["meta_Economy"]
    citizens_by_id = {c["character_id"]: c for c in city_state["citizens"]}
    willow_cit = citizens_by_id["enclave_07_willow"]

    rup_delta = 0
    headline = ""
    summary = ""
    actors = ["enclave_07_willow"]

    if action_type == "forage_dig":
        specimen_id = str(params.get("specimen_id") or "spec_geode_bismuth")
        valid_ids = {s["specimen_id"] for s in MUSEUM_CATALOG}
        if specimen_id not in valid_ids:
            specimen_id = "spec_geode_bismuth"
        inv[specimen_id] = int(inv.get(specimen_id, 0)) + 1
        inv["spec_flora_cave_truffle"] = int(inv.get("spec_flora_cave_truffle", 0)) + 1
        rup_delta = 5
        spec_name = next((s["name"] for s in MUSEUM_CATALOG if s["specimen_id"] == specimen_id), specimen_id)
        headline = f"Unearthed {spec_name}"
        summary = (
            f"Willow tapped a resonant geode fissure with her Copper Trowel, chelating the surrounding loam "
            f"and extracting a {spec_name} plus an aromatic Cave-Truffle."
        )

    elif action_type == "catch_critter":
        specimen_id = str(params.get("specimen_id") or "spec_critter_prism_moth")
        critter_ids = [s["specimen_id"] for s in MUSEUM_CATALOG if s["wing"] == "critters"]
        if specimen_id not in critter_ids:
            specimen_id = critter_ids[0]
        inv[specimen_id] = int(inv.get(specimen_id, 0)) + 1
        rup_delta = 5
        spec_name = next((s["name"] for s in MUSEUM_CATALOG if s["specimen_id"] == specimen_id), specimen_id)
        headline = f"Caught {spec_name}"
        summary = (
            f"With a gentle sweep of her Magnetotropic Bug Net, Willow observed and cataloged a {spec_name} "
            f"without disturbing its magnetite homing antennae."
        )
        actors.append("enclave_06_zara")

    elif action_type == "catch_fish":
        specimen_id = str(params.get("specimen_id") or "spec_fish_ammonite")
        fish_ids = [s["specimen_id"] for s in MUSEUM_CATALOG if s["wing"] == "ferro_fish"]
        if specimen_id not in fish_ids:
            specimen_id = fish_ids[0]
        inv[specimen_id] = int(inv.get(specimen_id, 0)) + 1
        rup_delta = 5
        spec_name = next((s["name"] for s in MUSEUM_CATALOG if s["specimen_id"] == specimen_id), specimen_id)
        headline = f"Angled {spec_name} at Ferrofluid Pier"
        summary = (
            f"Willow cast her Ferrofluid Dip-Rod from the Tide Dock into a standing Rosensweig wave and "
            f"reeled in a gleaming {spec_name}."
        )

    elif action_type == "water_crop":
        for node in city_state.get("resource_nodes") or []:
            if node.get("node_type") == "crop_plot":
                node["watered"] = True
        inv["spec_flora_iron_wheat"] = int(inv.get("spec_flora_iron_wheat", 0)) + 1
        inv["spec_flora_spore_orchid"] = int(inv.get("spec_flora_spore_orchid", 0)) + 1
        for bldg in city_state["buildings"]:
            if bldg["building_id"] == "proj_04_genesis_garden":
                bldg["project_progress_pct"] = round(min(100.0, float(bldg["project_progress_pct"]) + 1.5), 1)
        willow_cit["stress"] = round(max(0.05, float(willow_cit["stress"]) - 0.04), 3)
        rup_delta = 5
        headline = "Irrigated Genesis Garden Terraces"
        summary = (
            "Willow sprinkled triple-distilled rainwater and reduced sulfur across the Crystalline Iron-Wheat "
            "and Spore-Orchids alongside Terra."
        )
        actors.append("enclave_08_terra")

    elif action_type == "craft_diy":
        recipe_id = str(params.get("recipe_id") or "diy_herbal_liniment")
        recipe = next((r for r in DIY_RECIPES if r["recipe_id"] == recipe_id), DIY_RECIPES[0])
        recipe_id = str(recipe["recipe_id"])
        for ing_id, qty in (recipe.get("ingredients") or {}).items():
            if int(inv.get(ing_id, 0)) >= int(qty):
                inv[ing_id] = max(0, int(inv[ing_id]) - int(qty))
        inv[recipe_id] = int(inv.get(recipe_id, 0)) + 1
        willow["homestead_comfort_score"] = int(willow["homestead_comfort_score"]) + int(recipe.get("comfort_bonus", 2))
        rup_delta = 10
        headline = f"Crafted {recipe['name']}"
        summary = (
            f"At her fractional copper alembic workbench, Willow synthesized {recipe['name']} "
            f"(+{recipe.get('comfort_bonus', 2)} Homestead Comfort)."
        )

    elif action_type == "place_decor":
        recipe_id = str(params.get("recipe_id") or "diy_bismuth_lantern")
        recipe = next(
            (r for r in DIY_RECIPES if r["recipe_id"] == recipe_id and r.get("placeable")),
            next(r for r in DIY_RECIPES if r.get("placeable")),
        )
        x = int(params.get("x", 18))
        y = int(params.get("y", 30))
        x = max(2, min(GRID_SIZE - 3, x))
        y = max(2, min(GRID_SIZE - 3, y))
        decor_entry = {
            "decor_id": f"decor_{len(city_state['placed_decorations']) + 1:03d}",
            "recipe_id": str(recipe["recipe_id"]),
            "name": str(recipe["name"]),
            "icon": str(recipe["icon"]),
            "x": x,
            "y": y,
            "color": str(recipe.get("decor_color") or "#32f5c8"),
            "comfort_bonus": int(recipe.get("comfort_bonus", 5)),
        }
        city_state["placed_decorations"].append(decor_entry)
        willow["homestead_comfort_score"] = int(willow["homestead_comfort_score"]) + int(recipe.get("comfort_bonus", 5))
        rup_delta = 5
        headline = f"Placed {recipe['name']} at ({x}, {y})"
        summary = (
            f"Willow arranged a {recipe['name']} in the valley courtyard, raising Homestead Comfort to "
            f"{willow['homestead_comfort_score']}."
        )

    elif action_type == "gift_citizen":
        target_id = str(params.get("target_id") or "enclave_03_silas")
        if target_id not in citizens_by_id or target_id == "enclave_07_willow":
            target_id = "enclave_03_silas"
        target = citizens_by_id[target_id]
        item_id = str(params.get("item_id") or "diy_herbal_liniment")
        if int(inv.get(item_id, 0)) > 0:
            inv[item_id] = int(inv[item_id]) - 1

        new_bond = round(min(1.0, max(0.35, float(target["willow_bond"]) + 0.04)), 3)
        target["willow_bond"] = new_bond
        target["bonds"]["enclave_07_willow"] = new_bond
        willow_cit["bonds"][target_id] = new_bond
        target["stress"] = round(max(0.05, float(target["stress"]) - 0.08), 3)
        target["fatigue"] = round(max(0.05, float(target["fatigue"]) - 0.05), 3)
        rup_delta = 10
        headline = f"Gifted Alchemical Tonic to {target['name']}"
        summary = (
            f"Willow shared a hand-crafted gift with {target['name']} ({target['epithet']}), strengthening "
            f"their found-family bond to {new_bond:.2f} and easing their shift stress to {target['stress']:.2f}."
        )
        actors.append(target_id)

    elif action_type == "complete_daily_favor":
        favor_id = str(params.get("favor_id") or "")
        favors = city_state.get("daily_favors") or []
        favor = next((f for f in favors if f["favor_id"] == favor_id), None)
        if favor is None:
            favor = next((f for f in favors if not f.get("completed")), favors[0] if favors else None)
        if favor is not None:
            favor["completed"] = True
            req_id = str(favor["requester_id"])
            if req_id in citizens_by_id:
                req_cit = citizens_by_id[req_id]
                new_bond = round(min(1.0, max(0.35, float(req_cit["willow_bond"]) + float(favor.get("bond_delta", 0.05)))), 3)
                req_cit["willow_bond"] = new_bond
                req_cit["bonds"]["enclave_07_willow"] = new_bond
                willow_cit["bonds"][req_id] = new_bond
                req_cit["stress"] = round(max(0.05, float(req_cit["stress"]) + float(favor.get("stress_delta", -0.10))), 3)
                actors.append(req_id)
            rup_delta = int(favor.get("meta_rup_reward", 10))
            headline = f"Completed Favor: {favor['title']}"
            summary = (
                f"Willow fulfilled {favor['requester_name']}'s Notice Board favor ('{favor['title']}'), "
                f"earning +{rup_delta} RUP meta-reward while keeping in-world exchanges 100% gift-based (Law L12)."
            )

    elif action_type == "donate_museum":
        donated: list[str] = city_state["museum"]["donated_specimen_ids"]
        specimen_id = str(params.get("specimen_id") or "")
        if not specimen_id or specimen_id not in {s["specimen_id"] for s in MUSEUM_CATALOG}:
            undonated_inv = [sid for sid, cnt in inv.items() if cnt > 0 and sid.startswith("spec_") and sid not in donated]
            if undonated_inv:
                specimen_id = undonated_inv[0]
            else:
                undonated_all = [s["specimen_id"] for s in MUSEUM_CATALOG if s["specimen_id"] not in donated]
                specimen_id = undonated_all[0] if undonated_all else MUSEUM_CATALOG[0]["specimen_id"]

        spec_entry = next((s for s in MUSEUM_CATALOG if s["specimen_id"] == specimen_id), MUSEUM_CATALOG[0])
        if specimen_id not in donated:
            donated.append(specimen_id)
        if int(inv.get(specimen_id, 0)) > 0:
            inv[specimen_id] = int(inv[specimen_id]) - 1
        rup_delta = int(spec_entry.get("rup_reward", 10))
        headline = f"Donated {spec_entry['name']} to Living Atlas Museum"
        summary = (
            f"Dorian and Vex archived Willow's {spec_entry['name']} ({spec_entry['epistemic_tier']}) in the "
            f"{spec_entry['wing_label']} Wing ({len(donated)}/{len(MUSEUM_CATALOG)} specimens cataloged, +{rup_delta} RUP)."
        )
        actors.extend(["enclave_15_dorian", "enclave_14_vex"])

    elif action_type == "trigger_catalyst":
        catalyst = str(params.get("catalyst") or "feast").lower()
        sol = int(city_state.get("colony_sol", 1))
        seed = str(city_state.get("seed") or "enclave_sol_001")
        if catalyst == "feast":
            city_state["day_phase"] = DAY_PHASES[3]  # THE_FEAST
            feast_beat = evaluate_pacing_and_beat(
                recent_events=city_state.get("story_feed") or [],
                colony_sol=sol,
                day_phase="THE_FEAST",
            )
            city_state["drama_beat"] = feast_beat
            hearth = next(b for b in city_state["buildings"] if b["building_id"] == "proj_08_hearth_metabolic_engine")
            for idx, cit in enumerate(city_state["citizens"]):
                cit["x"] = float(hearth["x"] + (idx % 6))
                cit["y"] = float(hearth["y"] + hearth["d"] + (idx // 6))
                cit["stress"] = round(max(0.05, float(cit["stress"]) - 0.18), 3)
                cit["fatigue"] = round(max(0.05, float(cit["fatigue"]) - 0.15), 3)
                cit["polarity_inversion_active"] = False
                cit["current_activity"] = "Sharing Iron-Wheat loaves & herbal tea at The Feast"
            rup_delta = 25
            actors = list(CANONICAL_16_CHARACTER_IDS)
            headline = f"Sol {sol} Nightly Feast Convergence (All 16 Citizens)"
            summary = (
                f"All 16 Enclave citizens converged around Ryn and Elara's Hearth (Law L13, pacing={feast_beat['pacing_state']}). "
                f"Willow slipped herbal joint-liniment vials beside Silas and Leo's plates while everyone debated "
                f"{feast_beat['science_vegetable'].lower()}."
            )
        elif catalyst == "prank":
            prank = seed_shadow_prank(
                node_a="enclave_01_hector",
                node_b="enclave_03_silas",
                node_c="enclave_13_ryn",
                origin_sol=sol,
                prank_description="Replaced the brass pressure-gauge bezel with a whistling tea-kettle reed",
            )
            pending_pranks, matured_pranks = process_shadow_ledger(
                list(city_state.get("shadow_prank_ledger") or []) + [prank],
                current_sol=sol,
            )
            city_state["shadow_prank_ledger"] = pending_pranks
            if matured_pranks:
                city_state.setdefault("matured_prank_events", []).extend(matured_pranks)
            rup_delta = 5
            actors = ["enclave_01_hector", "enclave_03_silas", "enclave_13_ryn"]
            headline = "Seeded 3-Sol Shadow Economy Prank Triad (Law L12)"
            summary = (
                f"Hector rigged a harmless whistling reed for Silas, which will mature on Sol {prank['maturity_sol']} "
                f"when Ryn discovers it in the galley (lethality=0, 3-Feast maturity delay)."
            )
        elif catalyst == "expedition":
            city_state["day_phase"] = DAY_PHASES[1]  # MIDDAY_EXPEDITION
            exp_weather = compute_exoplanet_weather(
                tick_id=int(city_state.get("tick_id", 2)),
                colony_sol=sol,
                day_phase="MIDDAY_EXPEDITION",
                epoch_seed=seed,
            )
            city_state["weather"] = exp_weather
            for bldg in city_state["buildings"]:
                if bldg["category"] == "grand_project":
                    bldg["project_progress_pct"] = round(min(100.0, float(bldg["project_progress_pct"]) + 2.0), 1)
            inv["spec_geode_bismuth"] = int(inv.get("spec_geode_bismuth", 0)) + 1
            inv["spec_geode_piezo"] = int(inv.get("spec_geode_piezo", 0)) + 1
            rup_delta = 10
            actors = ["enclave_07_willow", "enclave_05_kaio", "enclave_01_hector", "enclave_06_zara"]
            headline = "Midday Ridge Geode & Botanical Expedition"
            summary = (
                f"Willow, Kaio, Zara, and Hector ventured along the basalt fault-line under "
                f"{exp_weather['micro_climate_regime']}, harvesting fresh Captured Lightning Geodes and advancing all 8 Grand Projects."
            )
        elif catalyst == "solar_flare":
            city_state["kp_exo"] = 7.5
            for cit in city_state["citizens"]:
                cit["stress"] = round(min(0.78, float(cit["stress"]) + 0.08), 3)
            rup_delta = 10
            actors = ["enclave_02_jane", "enclave_01_hector", "enclave_07_willow", "enclave_11_kenna"]
            headline = "Twin-Sun Magnetospheric Shear Spike (Kp 7.5)"
            summary = (
                "Counter-rotating solar winds drove Kp_exo to 7.5! Jane and Hector channeled the megajoule "
                "surge into The Stormbreaker while Willow and Kenna grounded the crew with calming tonics."
            )
        else:
            # harvest_moot
            city_state["day_phase"] = DAY_PHASES[2]  # DUSK_CRAFT
            moot_beat = evaluate_pacing_and_beat(
                recent_events=city_state.get("story_feed") or [],
                colony_sol=sol,
                day_phase="DUSK_CRAFT",
            )
            city_state["drama_beat"] = moot_beat
            for bldg in city_state["buildings"]:
                if bldg["building_id"] in ("proj_01_first_forge", "proj_04_genesis_garden", "proj_08_hearth_metabolic_engine"):
                    bldg["project_progress_pct"] = round(min(100.0, float(bldg["project_progress_pct"]) + 2.5), 1)
            rup_delta = 10
            actors = ["enclave_07_willow", "enclave_08_terra", "enclave_03_silas", "enclave_13_ryn"]
            headline = "Schrödinger's Harvest Moot Accord"
            summary = (
                "The Wilds, The Forge, and The Hub reached a cooperative accord on Crystalline Iron-Wheat "
                "Batch #14: seed stock for Terra, husk ash flux for Silas, and warm flour for Ryn's galley."
            )

    elif action_type == "advance_tutorial":
        tut = city_state.setdefault(
            "onboarding_tutorial",
            {
                "steps": copy.deepcopy(list(ENCLAVE_ONBOARDING_TUTORIAL_STEPS)),
                "current_step_index": 1,
                "current_step_id": ENCLAVE_ONBOARDING_TUTORIAL_STEPS[0]["step_id"],
                "completed_step_ids": [],
                "completed": False,
            },
        )
        completed_ids: list[str] = tut.setdefault("completed_step_ids", [])
        requested_step_id = str(params.get("step_id") or "")
        step_obj = next(
            (s for s in ENCLAVE_ONBOARDING_TUTORIAL_STEPS if s["step_id"] == requested_step_id),
            None,
        )
        if step_obj is None:
            step_obj = next(
                (s for s in ENCLAVE_ONBOARDING_TUTORIAL_STEPS if s["step_id"] not in completed_ids),
                ENCLAVE_ONBOARDING_TUTORIAL_STEPS[-1],
            )
        sid = str(step_obj["step_id"])
        if sid not in completed_ids:
            completed_ids.append(sid)
        next_uncompleted = next(
            (s for s in ENCLAVE_ONBOARDING_TUTORIAL_STEPS if s["step_id"] not in completed_ids),
            None,
        )
        if next_uncompleted is None:
            tut["completed"] = True
            tut["current_step_index"] = len(ENCLAVE_ONBOARDING_TUTORIAL_STEPS)
            tut["current_step_id"] = ENCLAVE_ONBOARDING_TUTORIAL_STEPS[-1]["step_id"]
        else:
            tut["completed"] = False
            tut["current_step_index"] = int(next_uncompleted["step_index"])
            tut["current_step_id"] = str(next_uncompleted["step_id"])
            target_zone = str(next_uncompleted.get("zone_id") or city_state.get("active_zone_id") or "zone_01_homestead_grove")
            if target_zone in ENCLAVE_EMERALD_DISTRICTS:
                city_state["active_zone_id"] = target_zone
                willow_cit["zone_id"] = target_zone

        rup_delta = int(step_obj.get("rup_reward", 5))
        headline = f"Tutorial Step {step_obj['step_index']}/6 Complete: {step_obj['title']}"
        summary = str(step_obj["dialogue"])
        actors.extend(["enclave_08_terra", "enclave_03_silas"])

    elif action_type == "warp_zone":
        room_id = params.get("room_id")
        zone_id = str(params.get("zone_id") or city_state.get("active_zone_id") or "zone_01_homestead_grove")
        if room_id and str(room_id) in ENCLAVE_INDOOR_ROOMS:
            rm = ENCLAVE_INDOOR_ROOMS[str(room_id)]
            city_state["active_indoor_room_id"] = str(room_id)
            city_state["active_zone_id"] = str(rm["parent_zone_id"])
            willow_cit["zone_id"] = str(rm["parent_zone_id"])
            willow_cit["x"] = float(rm["entry_spawn"]["x"])
            willow_cit["y"] = float(rm["entry_spawn"]["y"])
            rup_delta = 5
            headline = f"Entered {rm['name']}"
            summary = f"Willow stepped inside {rm['name']} ({rm['hoenn_route_banner']})."
            actors.extend([cid for cid in rm.get("residents", []) if cid != "enclave_07_willow"])
        else:
            if zone_id not in ENCLAVE_EMERALD_DISTRICTS:
                zone_id = "zone_01_homestead_grove"
            dist = ENCLAVE_EMERALD_DISTRICTS[zone_id]
            city_state["active_indoor_room_id"] = None
            city_state["active_zone_id"] = zone_id
            biome_id = str(dist["biome_id"])
            if biome_id in ENCLAVE_BIOMES:
                city_state["active_biome_id"] = biome_id
                city_state["active_biome"] = copy.deepcopy(ENCLAVE_BIOMES[biome_id])
            willow_cit["zone_id"] = zone_id
            willow_cit["x"] = float(params.get("x", dist["willow_spawn"]["x"]))
            willow_cit["y"] = float(params.get("y", dist["willow_spawn"]["y"]))
            rup_delta = 5
            headline = f"Arrived at {dist['name']}"
            summary = f"Willow traveled to {dist['hoenn_route_banner']} — {dist['description']}"
    else:
        raise ValueError(f"Unsupported Willow AC action_type: {action_type!r}")

    # Automatically advance onboarding tutorial when an in-world action satisfies a tutorial step
    if action_type != "advance_tutorial" and "onboarding_tutorial" in city_state:
        tut = city_state["onboarding_tutorial"]
        completed_ids = tut.setdefault("completed_step_ids", [])
        action_alias = "donate_museum" if action_type in ("craft_diy", "place_decor") else action_type
        for step_spec in ENCLAVE_ONBOARDING_TUTORIAL_STEPS:
            sid = str(step_spec["step_id"])
            if sid in completed_ids:
                continue
            if step_spec["required_action"] == action_alias:
                if sid == "STEP_2_DIG_GEODE" and "STEP_1_MEET_SOREN" not in completed_ids:
                    completed_ids.append("STEP_1_MEET_SOREN")
                completed_ids.append(sid)
                break
        next_uncompleted = next(
            (s for s in ENCLAVE_ONBOARDING_TUTORIAL_STEPS if s["step_id"] not in completed_ids),
            None,
        )
        if next_uncompleted is None:
            tut["completed"] = True
            tut["current_step_index"] = len(ENCLAVE_ONBOARDING_TUTORIAL_STEPS)
            tut["current_step_id"] = ENCLAVE_ONBOARDING_TUTORIAL_STEPS[-1]["step_id"]
        else:
            tut["completed"] = False
            tut["current_step_index"] = int(next_uncompleted["step_index"])
            tut["current_step_id"] = str(next_uncompleted["step_id"])

    meta_econ["city_rupee_bonus"] = int(meta_econ.get("city_rupee_bonus", 0)) + int(rup_delta)
    meta_econ["total_actions_performed"] = int(meta_econ.get("total_actions_performed", 0)) + 1

    feed_entry = {
        "feed_id": f"feed_{int(meta_econ['total_actions_performed']) + 2:03d}",
        "sol": int(city_state.get("colony_sol", 1)),
        "day_phase": str(city_state.get("day_phase", "DAWN_SHIFT")),
        "category": action_type.upper(),
        "title": _sanitize_pve_text(headline),
        "summary": _sanitize_pve_text(summary),
        "actors": actors,
        "rup_earned": int(rup_delta),
        "lethality": 0,
    }
    city_state["story_feed"].insert(0, feed_entry)
    return {
        "ok": True,
        "action_type": action_type,
        "rup_earned": int(rup_delta),
        "feed_entry": feed_entry,
        "summary": summarize_enclave_city_state(city_state),
    }


def summarize_enclave_city_state(city_state: dict[str, Any]) -> dict[str, Any]:
    """Build a compact `enclaveCitySummary` for `oasis_twin_bridge.py` and `aegis_asset_bridge.json`."""
    willow = city_state.get("willow_companion") or {}
    museum = city_state.get("museum") or {}
    favors = city_state.get("daily_favors") or []
    meta_econ = city_state.get("meta_Economy") or {}
    tut = city_state.get("onboarding_tutorial") or {}
    donated_ids = list(museum.get("donated_specimen_ids") or [])
    completed_favors = sum(1 for f in favors if f.get("completed"))

    return {
        "schema": SCHEMA_VERSION,
        "grid_size": int(city_state.get("grid_size", GRID_SIZE)),
        "active_biome_id": str(city_state.get("active_biome_id") or "crater_valley"),
        "active_biome_name": str((city_state.get("active_biome") or {}).get("name") or "Enclave Crater Valley"),
        "active_zone_id": str(city_state.get("active_zone_id") or "zone_01_homestead_grove"),
        "active_indoor_room_id": city_state.get("active_indoor_room_id"),
        "emerald_districts_count": len(city_state.get("emerald_districts") or ENCLAVE_EMERALD_DISTRICTS),
        "indoor_rooms_count": len(city_state.get("indoor_rooms") or ENCLAVE_INDOOR_ROOMS),
        "tutorial_step_index": int(tut.get("current_step_index", 1)),
        "tutorial_completed": bool(tut.get("completed", False)),
        "crucible_hearth_biomes": list(CRUCIBLE_ELEMENTAL_HEARTH_BIOMES),
        "living_atlas_epistemic_tiers": list(DADS_BOOK_LORE_EPISTEMIC_TIERS),
        "tycoon_crafting_themes": list(LFS_TYCOON_CRAFTING_THEMES),
        "bridge_global": "window.ArcadeAssetBridge",
        "citizens_count": len(city_state.get("citizens") or []),
        "buildings_count": len(city_state.get("buildings") or []),
        "museum_donations_count": len(donated_ids),
        "museum_total_specimens": int(museum.get("total_specimens", len(MUSEUM_CATALOG))),
        "diy_recipes_unlocked": len(willow.get("unlocked_diy_recipes") or []),
        "daily_favors_completed": completed_favors,
        "daily_favors_total": len(favors),
        "placed_decorations_count": len(city_state.get("placed_decorations") or []),
        "willow_homestead_comfort_score": int(willow.get("homestead_comfort_score", 100)),
        "city_rupee_bonus": int(meta_econ.get("city_rupee_bonus", 25)),
        "currency_code": "RUP",
        "in_world_economy_monetary": False,
    }


def sync_city_with_oasis_bridge(
    repo_root: Path | str | None = None,
    save_root: Path | str | None = None,
    bridge_path: Path | str | None = None,
) -> dict[str, Any]:
    """Delegate save-lineage and Rupee (`RUP`) bridge synchronization to `engine.oasis_twin_bridge`."""
    from engine.oasis_twin_bridge import (
        compute_enclave_player_meta_rewards,
        extract_enclave_twin_live_state,
        sync_enclave_oasis_save_and_bridge,
    )

    root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
    rewards = compute_enclave_player_meta_rewards(root)
    live_state = extract_enclave_twin_live_state(root)
    sync_res = sync_enclave_oasis_save_and_bridge(
        repo_root=root,
        save_root=save_root,
        bridge_path=bridge_path,
    )
    return {
        "rewards": rewards,
        "live_state": live_state,
        "sync_result": sync_res,
    }


class EnclaveVoxelCityEngine:
    """Object-oriented facade for The Enclave of the 16 2.5D Voxel City & Willow Animal Crossing Sim."""

    def __init__(
        self,
        repo_root: Path | str | None = None,
        seed: str = "enclave_sol_001",
        biome_id: str = "crater_valley",
    ) -> None:
        self.repo_root = Path(repo_root).resolve() if repo_root else Path(__file__).resolve().parent.parent
        self.seed = seed
        self.state = generate_enclave_city_state(self.repo_root, seed=seed, biome_id=biome_id)

    def perform_action(self, action_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return perform_willow_ac_action(self.state, action_type=action_type, payload=payload)

    def advance_tutorial(self, step_id: str | None = None) -> dict[str, Any]:
        payload = {"step_id": step_id} if step_id else {}
        return perform_willow_ac_action(self.state, action_type="advance_tutorial", payload=payload)

    def warp_zone(self, zone_id: str | None = None, room_id: str | None = None) -> dict[str, Any]:
        return perform_willow_ac_action(
            self.state,
            action_type="warp_zone",
            payload={"zone_id": zone_id, "room_id": room_id},
        )

    def advance_tick(self) -> dict[str, Any]:
        return advance_city_tick(self.state, repo_root=self.repo_root)

    def switch_biome(self, biome_id: str) -> dict[str, Any]:
        if biome_id not in ENCLAVE_BIOMES:
            raise ValueError(f"Unknown biome_id: {biome_id!r}")
        self.state["active_biome_id"] = biome_id
        self.state["active_biome"] = copy.deepcopy(ENCLAVE_BIOMES[biome_id])
        return self.summary()

    def sync_oasis_bridge(
        self,
        save_root: Path | str | None = None,
        bridge_path: Path | str | None = None,
    ) -> dict[str, Any]:
        return sync_city_with_oasis_bridge(
            repo_root=self.repo_root,
            save_root=save_root,
            bridge_path=bridge_path,
        )

    def summary(self) -> dict[str, Any]:
        return summarize_enclave_city_state(self.state)
