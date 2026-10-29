class_name EnclaveStateBridge
extends RefCounted
## Canonical Enclave Digital Twin State & Cross-Capsule Synergy Bridge for Godot 4.3 Overworld.
## Synchronizes all 16 Citizens, 6 Tools, 16 Living Atlas Museum Specimens (SR-05 TIER_1..TIER_4),
## 12 DIY Recipes (SR-02 lfs-tycoon items), 4 Elemental Hearth Biomes (SR-04), and RUP rewards (SR-08).

const CANONICAL_16_IDS: Array[String] = [
	"enclave_01_hector", "enclave_02_jane", "enclave_03_silas", "enclave_04_leo",
	"enclave_05_kaio", "enclave_06_zara", "enclave_07_willow", "enclave_08_terra",
	"enclave_09_orion", "enclave_10_isla", "enclave_11_kenna", "enclave_12_elias",
	"enclave_13_ryn", "enclave_14_vex", "enclave_15_dorian", "enclave_16_elara"
]

const LDS_THEME_PACKS: Array[String] = [
	"evergreen-dark",
	"evergreen-light",
	"high-contrast",
	"calm"
]

const DAY_PHASES: Array[String] = [
	"DAWN_SHIFT",
	"MIDDAY_EXPEDITION",
	"DUSK_CRAFT",
	"THE_FEAST"
]

const TOOLS: Array[Dictionary] = [
	{"tool_id": "trowel", "slot": 1, "name": "Copper Trowel & Chelation Flask", "short_label": "⚗️ Trowel", "icon": "⚗️", "action_type": "forage_dig"},
	{"tool_id": "bug_net", "slot": 2, "name": "Magnetotropic Bug Net", "short_label": "🦋 Bug Net", "icon": "🦋", "action_type": "catch_critter"},
	{"tool_id": "dip_rod", "slot": 3, "name": "Ferrofluid Dip-Rod", "short_label": "🎣 Dip-Rod", "icon": "🎣", "action_type": "catch_fish"},
	{"tool_id": "watering_can", "slot": 4, "name": "Distilled Rainwater Can", "short_label": "💧 Water Can", "icon": "💧", "action_type": "water_crop"},
	{"tool_id": "tinker_wrench", "slot": 5, "name": "Tinker Wrench & Yard Decorator", "short_label": "🪑 Decorate", "icon": "🪑", "action_type": "place_decor"},
	{"tool_id": "gift_satchel", "slot": 6, "name": "Favor & Gift Satchel", "short_label": "🎁 Gift/Favor", "icon": "🎁", "action_type": "gift_citizen"}
]

const MUSEUM_CATALOG: Array[Dictionary] = [
	{"specimen_id": "spec_geode_bismuth", "name": "Hopper-Crystal Bismuth Geode", "wing": "geodes", "wing_label": "⚡ Captured Geodes", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "💎", "rup_reward": 10, "lore": "Iridescent stepped bismuth-telluride nodule trapping a 40-ampere persistent atmospheric current."},
	{"specimen_id": "spec_geode_fulgurite", "name": "Bifurcated Ridge Fulgurite Tube", "wing": "geodes", "wing_label": "⚡ Captured Geodes", "epistemic_tier": "TIER_1_VERIFIED_EVENT", "icon": "⚡", "rup_reward": 10, "lore": "Vitrified ferro-silicate lightning glass fused during a Kp 7.2 storm on Stormbreaker Ridge."},
	{"specimen_id": "spec_geode_piezo", "name": "Singing Piezo-Quartz Cluster", "wing": "geodes", "wing_label": "⚡ Captured Geodes", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🔮", "rup_reward": 10, "lore": "Resonates at a pure 432 Hz harmonic whenever Luna Gamma passes perigee."},
	{"specimen_id": "spec_geode_lodestone", "name": "Octahedral Magnetite Lodestone", "wing": "geodes", "wing_label": "⚡ Captured Geodes", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🪨", "rup_reward": 10, "lore": "Naturally polarized core-ore used by Silas to calibrate compasses and Helmholtz rings."},
	{"specimen_id": "spec_critter_prism_moth", "name": "Aurora Prism-Moth", "wing": "critters", "wing_label": "🦋 Magneto-Critters", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🦋", "rup_reward": 10, "lore": "Diffracts twin-sun ultraviolet rays through chitinous wing-scales to orient along magnetic field lines."},
	{"specimen_id": "spec_critter_soliton_firefly", "name": "Mycelial Soliton Firefly", "wing": "critters", "wing_label": "🦋 Magneto-Critters", "epistemic_tier": "TIER_4_SPECULATIVE_HYPOTHESIS", "icon": "✨", "rup_reward": 10, "lore": "Flashes in synchronized 10 Hz wave-trains matching subterranean fungal telemetry."},
	{"specimen_id": "spec_critter_cave_beetle", "name": "Copper-Carapace Pollinator Beetle", "wing": "critters", "wing_label": "🦋 Magneto-Critters", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🪲", "rup_reward": 10, "lore": "Zara's favorite sanctuary helper; carries chelated pollen between Crystalline Iron-Wheat blossoms."},
	{"specimen_id": "spec_critter_bismuth_dragonfly", "name": "Rainbow Bismuth Skimmer", "wing": "critters", "wing_label": "🦋 Magneto-Critters", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🦋", "rup_reward": 10, "lore": "Hovers effortlessly over standing-wave crests in the ferrofluid river basin."},
	{"specimen_id": "spec_fish_ammonite", "name": "Coiled Magnetite Ammonite", "wing": "ferro_fish", "wing_label": "🐟 Ferro-Basin Fauna", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🐚", "rup_reward": 10, "lore": "Living logarithmic spiral shell plated in nanoscale iron-oxide that surfs lunar tidal surges."},
	{"specimen_id": "spec_fish_rosensweig_eel", "name": "Rosensweig Ribbon-Eel", "wing": "ferro_fish", "wing_label": "🐟 Ferro-Basin Fauna", "epistemic_tier": "TIER_4_SPECULATIVE_HYPOTHESIS", "icon": "🐍", "rup_reward": 10, "lore": "Camouflages among geometric ferrofluid spikes and emits gentle millivolt navigation hums."},
	{"specimen_id": "spec_fish_colloidal_pike", "name": "Silver-Scale Colloidal Darter", "wing": "ferro_fish", "wing_label": "🐟 Ferro-Basin Fauna", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🐟", "rup_reward": 10, "lore": "Fast-swimming river fish prized for studying non-toxic heavy-metal filtration membranes."},
	{"specimen_id": "spec_fish_fulgurite_crab", "name": "Vent-Warmth Fulgurite Crab", "wing": "ferro_fish", "wing_label": "🐟 Ferro-Basin Fauna", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🦀", "rup_reward": 10, "lore": "Gathers around geothermal bridge pilings and polishes copper pebbles with its claws."},
	{"specimen_id": "spec_flora_iron_wheat", "name": "Golden Crystalline Iron-Wheat Sheaf", "wing": "flora_relics", "wing_label": "🌿 Flora & Relics", "epistemic_tier": "TIER_1_VERIFIED_EVENT", "icon": "🌾", "rup_reward": 10, "lore": "Willow and Terra's signature hybrid crop—chelated roots yield sweet, mineral-rich grain for The Feast."},
	{"specimen_id": "spec_flora_spore_orchid", "name": "Bioluminescent Spore-Orchid", "wing": "flora_relics", "wing_label": "🌿 Flora & Relics", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🌺", "rup_reward": 10, "lore": "Blooms during Dusk Craft with soft cyan-violet petals that soothe cortical fatigue."},
	{"specimen_id": "spec_flora_cave_truffle", "name": "Mycelial Amber Cave-Truffle", "wing": "flora_relics", "wing_label": "🌿 Flora & Relics", "epistemic_tier": "TIER_2_EMPIRICAL_SPECIMEN", "icon": "🍄", "rup_reward": 10, "lore": "Aromatic subterranean fruiting body sought by Ryn for Feast gravies and by Willow for tonics."},
	{"specimen_id": "spec_flora_jade_pestle", "name": "Cloud-Forest Jade Mortar Inlay", "wing": "flora_relics", "wing_label": "🌿 Flora & Relics", "epistemic_tier": "TIER_3_ORAL_BALLAD", "icon": "🏺", "rup_reward": 25, "lore": "Commemorative botanical pressing honoring Old Earth alpine cloud-forest phytochemistry."}
]

const DIY_RECIPES: Array[Dictionary] = [
	{"recipe_id": "diy_herbal_liniment", "name": "Herbal Joint-Liniment Vial", "category": "alchemy_gift", "icon": "🧪", "placeable": false, "comfort_bonus": 2, "description": "Warming pine-resin and sulfur salve Willow slips beside Silas and Leo's plates at The Feast."},
	{"recipe_id": "diy_blackberry_cordial", "name": "Spiced Blackberry & Lichen Cordial", "category": "alchemy_gift", "icon": "🍷", "placeable": false, "comfort_bonus": 2, "description": "Kept in the green flask next to Willow's gourd; restores warmth after ridge shifts."},
	{"recipe_id": "diy_chelation_elixir", "name": "Organometallic Soil Chelation Elixir", "category": "alchemy_gift", "icon": "⚗️", "placeable": false, "comfort_bonus": 3, "description": "Detoxifies raw ferro-silicate soil so heirloom seedlings sprout without iron lockup."},
	{"recipe_id": "diy_bismuth_lantern", "name": "Bismuth-Glass Geode Streetlamp", "category": "voxel_decor", "icon": "🏮", "placeable": true, "comfort_bonus": 5, "description": "Hand-brazed copper lantern housing a softly glowing captured-lightning geode core."},
	{"recipe_id": "diy_cymatic_chime", "name": "Helmholtz Cymatic Wind-Chime", "category": "voxel_decor", "icon": "🎐", "placeable": true, "comfort_bonus": 6, "description": "Tuned brass tubes that ring in soothing fifth intervals during bifurcated valley breezes."},
	{"recipe_id": "diy_resonant_terrarium", "name": "Bioluminescent Wardian Terrarium", "category": "voxel_decor", "icon": "🪴", "placeable": true, "comfort_bonus": 6, "description": "Faceted glass case nurturing glowing mycelial moss and friendly soliton fireflies."},
	{"recipe_id": "diy_bismuth_bench", "name": "Tempered Bismuth-Bronze Garden Bench", "category": "voxel_decor", "icon": "🪑", "placeable": true, "comfort_bonus": 4, "description": "Ergonomic courtyard bench where Anchors and Prodigies swap stories over hot tea."},
	{"recipe_id": "diy_alembic_still", "name": "Fractional Copper Yard Alembic", "category": "voxel_decor", "icon": "🏺", "placeable": true, "comfort_bonus": 7, "description": "Outdoor distillation coil that perfumes Willow's homestead with crisp pine resin and ozone."},
	{"recipe_id": "diy_orchid_planter", "name": "Cedar & Copper Spore-Orchid Planter", "category": "voxel_decor", "icon": "🌷", "placeable": true, "comfort_bonus": 5, "description": "Raised chelated flower box bursting with pollinator-friendly exoplanet blooms."},
	{"recipe_id": "theme_enclave_first_forge", "name": "First Forge Bismuth Anvil Pedestal (SR-02)", "category": "voxel_decor", "icon": "⚒️", "placeable": true, "comfort_bonus": 8, "description": "Cross-capsule SR-02 craft item shared with lfs-tycoon (theme_enclave_first_forge)."},
	{"recipe_id": "theme_enclave_living_atlas", "name": "Living Atlas Concordance Globe (SR-02)", "category": "voxel_decor", "icon": "🧭", "placeable": true, "comfort_bonus": 8, "description": "Cross-capsule SR-02 craft item shared with lfs-tycoon (theme_enclave_living_atlas)."},
	{"recipe_id": "diy_feast_bread_basket", "name": "Warm Iron-Wheat Feast Basket", "category": "alchemy_gift", "icon": "🥖", "placeable": false, "comfort_bonus": 3, "description": "Freshly milled Crystalline Iron-Wheat loaves glazed with cave-truffle butter."}
]

var colony_sol: int = 1
var tick_id: int = 1
var day_phase: String = "DAWN_SHIFT"
var kp_exo: float = 3.8
var rupees: int = 60
var equipped_tool_index: int = 0
var homestead_comfort_score: int = 102

var theme_pack: String = "evergreen-dark"
var reduced_motion: bool = false
var audio_muted: bool = false
var haptics_enabled: bool = true

var inventory: Dictionary = {}
var donated_specimen_ids: Array[String] = []
var citizens: Dictionary = {}
var daily_favors: Array[Dictionary] = []
var story_feed: Array[Dictionary] = []
var placed_decorations: Array[Dictionary] = []


func _init() -> void:
	reset_to_defaults()


func reset_to_defaults() -> void:
	colony_sol = 1
	tick_id = 1
	day_phase = "DAWN_SHIFT"
	kp_exo = 3.8
	rupees = 60
	equipped_tool_index = 0
	homestead_comfort_score = 102

	inventory = {
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
		"theme_enclave_living_atlas": 1
	}

	donated_specimen_ids = [
		"spec_geode_lodestone",
		"spec_flora_iron_wheat"
	]

	_init_citizens()
	_init_daily_favors()
	_init_story_feed()
	_try_load_live_snapshot()


func _init_citizens() -> void:
	var roster: Array[Dictionary] = [
		{"id": "enclave_01_hector", "name": "Hector", "epithet": "The Spark", "squad": "The Forge", "mbti": "ESTP", "enneagram": "7w8", "project": "The Stormbreaker Spire", "quote": "Watch that copper busbar hum! When the twin-sun shear hits Kp 6, we harvest lightning for the whole valley!"},
		{"id": "enclave_02_jane", "name": "Jane", "epithet": "The Tactician", "squad": "The Forge", "mbti": "ENTJ", "enneagram": "8w9", "project": "The Stormbreaker Spire", "quote": "My Babbage fluid-loom has the storm fronts modeled to three decimal places. Stay grounded, Willow."},
		{"id": "enclave_03_silas", "name": "Silas", "epithet": "The Engineer", "squad": "The Forge", "mbti": "ISTJ", "enneagram": "1w9", "project": "The First Forge", "quote": "Morning, Willow! My knuckles are stiff from the morning frost on the busbars, but that Bismuth Geode fissure by your porch is ready for your Copper Trowel."},
		{"id": "enclave_04_leo", "name": "Leo", "epithet": "The Machinist", "squad": "The Forge", "mbti": "ISTP", "enneagram": "9w8", "project": "The First Forge", "quote": "Measure twice, braze once. If you find any octahedral lodestones on the caldera ledges, bring 'em by the foundry."},
		{"id": "enclave_05_kaio", "name": "Kaio", "epithet": "The Pathfinder", "squad": "The Wilds", "mbti": "ESFP", "enneagram": "7w6", "project": "The Sanctuary Paddock", "quote": "The Ferrofluid Basin is shimmering today! Cast your Dip-Rod off the Tide Pier to catch a Coiled Magnetite Ammonite."},
		{"id": "enclave_06_zara", "name": "Zara", "epithet": "The Naturalist", "squad": "The Wilds", "mbti": "ISFP", "enneagram": "9w1", "project": "The Sanctuary Paddock", "quote": "Look how gently the Aurora Prism-Moths orient along the valley magnetic lines. A soft sweep of your Bug Net won't startle them."},
		{"id": "enclave_07_willow", "name": "Willow", "epithet": "The Alchemist", "squad": "The Wilds", "mbti": "INFP", "enneagram": "4w5", "project": "Genesis Garden Conservatory", "quote": "With a bit of chelated sulfur, pine resin, and rainwater, even raw crater basalt blooms into a warm home."},
		{"id": "enclave_08_terra", "name": "Terra", "epithet": "The Gardener", "squad": "The Wilds", "mbti": "ISFJ", "enneagram": "2w1", "project": "Genesis Garden Conservatory", "quote": "Welcome out to the porch, Willow! Try equipping your Copper Trowel [1] on the glowing geode crack and your Watering Can [4] on our Golden Iron-Wheat beds!"},
		{"id": "enclave_09_orion", "name": "Orion", "epithet": "The Visionary", "squad": "The Mind", "mbti": "ENTP", "enneagram": "7w8", "project": "The Simulacrum Rotunda", "quote": "Thirty-two brass Helmholtz rings spinning in harmony! And wait till you see the cymatic chimes in Aegis Outfitters."},
		{"id": "enclave_10_isla", "name": "Isla", "epithet": "The Architect", "squad": "The Mind", "mbti": "INTJ", "enneagram": "5w6", "project": "The Simulacrum Rotunda", "quote": "Every bridge and pitched roof in our crater follows golden-ratio acoustic geometry."},
		{"id": "enclave_11_kenna", "name": "Kenna", "epithet": "The Empath", "squad": "The Mind", "mbti": "INFJ", "enneagram": "4w3", "project": "The Lyceum of the Mind", "quote": "Take a slow breath, Willow. If the screen ever feels busy, you can toggle Calm Theme or Reduced Motion in the START menu."},
		{"id": "enclave_12_elias", "name": "Elias", "epithet": "The Philosopher", "squad": "The Mind", "mbti": "INTP", "enneagram": "5w4", "project": "The Lyceum of the Mind", "quote": "Our sixteen-law constitution guarantees that every exchange in this valley is a gift of mutual care, never a debt."},
		{"id": "enclave_13_ryn", "name": "Ryn", "epithet": "The Chef", "squad": "The Hub", "mbti": "ESFJ", "enneagram": "2w3", "project": "The Hearth & Metabolic Galley", "quote": "Step inside the Hearth whenever you're ready! Ring the Nightly Feast Bell and all 16 of us will gather around the banquet table for warm Iron-Wheat bread!"},
		{"id": "enclave_14_vex", "name": "Vex", "epithet": "The Archivist", "squad": "The Hub", "mbti": "ESTJ", "enneagram": "6w5", "project": "The Living Atlas Museum", "quote": "Every specimen in our Living Atlas Museum is stamped with its SR-05 epistemic tier—from TIER_1 verified events to TIER_4 hypotheses."},
		{"id": "enclave_15_dorian", "name": "Dorian", "epithet": "The Chronicler", "squad": "The Hub", "mbti": "ENFP", "enneagram": "3w4", "project": "The Living Atlas Museum", "quote": "Bring any geodes, critters, ferro-fish, or relics into the Living Atlas Museum! Every donation enriches tonight's Evening Dispatch."},
		{"id": "enclave_16_elara", "name": "Elara", "epithet": "The Medic", "squad": "The Hub", "mbti": "ENFJ", "enneagram": "2w1", "project": "The Hearth & Metabolic Galley", "quote": "Your Herbal Joint-Liniment vials work wonders for Silas and Leo after a cold shift on the ridge."}
	]
	citizens.clear()
	for entry in roster:
		var cid := str(entry["id"])
		citizens[cid] = {
			"character_id": cid,
			"name": entry["name"],
			"epithet": entry["epithet"],
			"squad": entry["squad"],
			"mbti_type": entry["mbti"],
			"enneagram": entry["enneagram"],
			"grand_project": entry["project"],
			"quote": entry["quote"],
			"stress": 0.22,
			"fatigue": 0.18,
			"willow_bond": 1.0 if cid == "enclave_07_willow" else 0.80
		}


func _init_daily_favors() -> void:
	daily_favors = [
		{
			"favor_id": "favor_sol_001_silas_liniment",
			"requester_id": "enclave_03_silas",
			"requester_name": "Silas (The Engineer)",
			"title": "Warm Joint-Liniment for the Busbar Shift",
			"requested_item_id": "diy_herbal_liniment",
			"meta_rup_reward": 10,
			"completed": false
		},
		{
			"favor_id": "favor_sol_001_terra_chelation",
			"requester_id": "enclave_08_terra",
			"requester_name": "Terra (The Gardener)",
			"title": "Chelation Catalyst for Iron-Wheat Batch #14",
			"requested_item_id": "diy_chelation_elixir",
			"meta_rup_reward": 10,
			"completed": false
		},
		{
			"favor_id": "favor_sol_001_dorian_museum",
			"requester_id": "enclave_15_dorian",
			"requester_name": "Dorian & Vex (The Living Atlas)",
			"title": "Catalog a Fresh Crater Specimen",
			"requested_item_id": "ANY_SPECIMEN",
			"meta_rup_reward": 10,
			"completed": false
		}
	]


func _init_story_feed() -> void:
	story_feed = [
		{
			"sol": colony_sol,
			"day_phase": day_phase,
			"title": "Willow Steps Into the Hoenn-Style Crater Overworld",
			"summary": "Willow adjusted her horned bronze circlet in Homestead Grove as Terra and Silas waved from the garden porch."
		},
		{
			"sol": colony_sol,
			"day_phase": day_phase,
			"title": "Living Atlas Museum & Hearth Galley Open Doors",
			"summary": "Dorian and Vex polished the 16 epistemic specimen pedestals while Ryn fired the steam-ovens at Hearth Plaza."
		}
	]


func _try_load_live_snapshot() -> void:
	var candidate_paths: Array[String] = [
		ProjectSettings.globalize_path("res://../snapshots/latest.json").simplify_path(),
		ProjectSettings.globalize_path("res://").path_join("../snapshots/latest.json").simplify_path(),
		"res://snapshots/latest.json",
	]
	var snap_path := ""
	for cand in candidate_paths:
		if FileAccess.file_exists(cand):
			snap_path = cand
			break
	if snap_path == "":
		return
	var raw := FileAccess.get_file_as_string(snap_path)
	var parsed: Variant = JSON.parse_string(raw)
	if typeof(parsed) != TYPE_DICTIONARY:
		return
	var snap: Dictionary = parsed
	colony_sol = int(snap.get("colony_sol", colony_sol))
	tick_id = int(snap.get("tick_id", tick_id))
	day_phase = str(snap.get("day_phase", day_phase))
	var chars_dict: Variant = snap.get("characters", {})
	if typeof(chars_dict) == TYPE_DICTIONARY:
		for c_entry in characters:
			var cid := str(c_entry.get("id", ""))
			if chars_dict.has(cid) and typeof(chars_dict[cid]) == TYPE_DICTIONARY:
				var live_c: Dictionary = chars_dict[cid]
				c_entry["stress"] = float(live_c.get("stress", c_entry.get("stress", 0.2)))
				c_entry["morale"] = float(live_c.get("morale", c_entry.get("morale", 0.8)))
	var recent_segs: Variant = snap.get("recent_segments", [])
	if typeof(recent_segs) == TYPE_ARRAY and recent_segs.size() > 0:
		var live_highlights: Array[Dictionary] = []
		for seg in recent_segs:
			if typeof(seg) == TYPE_DICTIONARY:
				live_highlights.append({
					"sol": int(seg.get("colony_sol", colony_sol)),
					"day_phase": str(seg.get("day_phase", day_phase)),
					"title": "%s (%s -> %s)" % [
						str(seg.get("segment_id", "Live Segment")),
						str(seg.get("active_pov_id", "")),
						str(seg.get("next_pov_target", ""))
					],
					"summary": str(seg.get("excerpt", ""))
				})
		if live_highlights.size() > 0:
			dispatch_highlights = live_highlights



func get_equipped_tool() -> Dictionary:
	return TOOLS[posmod(equipped_tool_index, TOOLS.size())]


func select_tool_slot(slot_idx: int) -> Dictionary:
	equipped_tool_index = posmod(slot_idx, TOOLS.size())
	return get_equipped_tool()


func select_tool_by_id(tool_id: String) -> Dictionary:
	for idx in TOOLS.size():
		if str(TOOLS[idx]["tool_id"]) == tool_id:
			equipped_tool_index = idx
			return TOOLS[idx]
	return get_equipped_tool()


func cycle_tool(delta: int = 1) -> Dictionary:
	equipped_tool_index = posmod(equipped_tool_index + delta, TOOLS.size())
	return get_equipped_tool()


func perform_action(action_type: String, payload: Dictionary = {}) -> Dictionary:
	var rup_delta := 0
	var headline := ""
	var detail := ""

	match action_type:
		"forage_dig":
			var spec_id := str(payload.get("specimen_id", "spec_geode_bismuth"))
			inventory[spec_id] = int(inventory.get(spec_id, 0)) + 1
			inventory["spec_flora_cave_truffle"] = int(inventory.get("spec_flora_cave_truffle", 0)) + 1
			rup_delta = 5
			var sname := get_specimen_name(spec_id)
			headline = "Unearthed %s!" % sname
			detail = "Willow tapped the resonant fissure with her Copper Trowel and extracted a %s + Cave-Truffle (+5 RUP)!" % sname
		"catch_critter":
			var spec_id := str(payload.get("specimen_id", "spec_critter_prism_moth"))
			inventory[spec_id] = int(inventory.get(spec_id, 0)) + 1
			rup_delta = 5
			var sname := get_specimen_name(spec_id)
			headline = "Caught %s!" % sname
			detail = "With a gentle sweep of her Magnetotropic Bug Net, Willow cataloged a %s (+5 RUP)!" % sname
		"catch_fish":
			var spec_id := str(payload.get("specimen_id", "spec_fish_ammonite"))
			inventory[spec_id] = int(inventory.get(spec_id, 0)) + 1
			rup_delta = 5
			var sname := get_specimen_name(spec_id)
			headline = "Reeled in %s!" % sname
			detail = "Willow cast her Ferrofluid Dip-Rod into the shimmering basin and angled a %s (+5 RUP)!" % sname
		"water_crop":
			inventory["spec_flora_iron_wheat"] = int(inventory.get("spec_flora_iron_wheat", 0)) + 1
			inventory["spec_flora_spore_orchid"] = int(inventory.get("spec_flora_spore_orchid", 0)) + 1
			rup_delta = 5
			headline = "Irrigated Crystalline Iron-Wheat!"
			detail = "Willow sprinkled distilled rainwater over the Genesis Garden plots, harvesting fresh Iron-Wheat & Spore-Orchid (+5 RUP)!"
		"craft_diy":
			var rec_id := str(payload.get("recipe_id", "diy_herbal_liniment"))
			var rec := get_recipe(rec_id)
			inventory[rec_id] = int(inventory.get(rec_id, 0)) + 1
			homestead_comfort_score += int(rec.get("comfort_bonus", 3))
			rup_delta = 10
			headline = "Crafted %s!" % str(rec.get("name", rec_id))
			detail = "At her Copper Alembic Workbench, Willow synthesized %s (+%d Comfort, +10 RUP)!" % [str(rec.get("name", rec_id)), int(rec.get("comfort_bonus", 3))]
		"place_decor":
			var rec_id := str(payload.get("recipe_id", "diy_bismuth_lantern"))
			var rec := get_recipe(rec_id)
			placed_decorations.append({"recipe_id": rec_id, "name": rec.get("name", rec_id)})
			homestead_comfort_score += int(rec.get("comfort_bonus", 5))
			rup_delta = 5
			headline = "Placed %s!" % str(rec.get("name", rec_id))
			detail = "Willow arranged %s in the courtyard, raising Homestead Comfort to %d (+5 RUP)!" % [str(rec.get("name", rec_id)), homestead_comfort_score]
		"gift_citizen":
			var target_id := str(payload.get("target_id", "enclave_03_silas"))
			var cit: Dictionary = citizens.get(target_id, citizens["enclave_03_silas"])
			cit["willow_bond"] = clampf(float(cit.get("willow_bond", 0.8)) + 0.05, 0.35, 1.0)
			cit["stress"] = clampf(float(cit.get("stress", 0.2)) - 0.08, 0.05, 1.0)
			for fav in daily_favors:
				if str(fav.get("requester_id")) == target_id and not bool(fav.get("completed", false)):
					fav["completed"] = true
			rup_delta = 10
			headline = "Gifted Tonic to %s!" % str(cit.get("name", "Citizen"))
			detail = "Willow shared an alchemical gift with %s (%s). Bond rose to %.2f and shift stress eased (+10 RUP)!" % [
				str(cit.get("name", "Citizen")), str(cit.get("epithet", "")), float(cit["willow_bond"])
			]
		"donate_museum":
			var spec_id := str(payload.get("specimen_id", ""))
			if spec_id == "" or spec_id in donated_specimen_ids:
				for item in MUSEUM_CATALOG:
					var cand := str(item["specimen_id"])
					if cand not in donated_specimen_ids:
						spec_id = cand
						break
			if spec_id == "":
				spec_id = "spec_geode_bismuth"
			if spec_id not in donated_specimen_ids:
				donated_specimen_ids.append(spec_id)
			for fav in daily_favors:
				if str(fav.get("requester_id")) == "enclave_15_dorian":
					fav["completed"] = true
			var spec := get_specimen(spec_id)
			rup_delta = int(spec.get("rup_reward", 10))
			headline = "Donated %s to Living Atlas!" % str(spec.get("name", spec_id))
			detail = "Dorian & Vex cataloged %s (%s) in the %s Wing (%d/%d specimens, +%d RUP)!" % [
				str(spec.get("name", spec_id)), str(spec.get("epistemic_tier", "TIER_2")),
				str(spec.get("wing_label", "Museum")), donated_specimen_ids.size(), MUSEUM_CATALOG.size(), rup_delta
			]
		"trigger_feast":
			day_phase = "THE_FEAST"
			for cid in citizens.keys():
				var c: Dictionary = citizens[cid]
				c["stress"] = clampf(float(c.get("stress", 0.2)) - 0.15, 0.05, 1.0)
				c["fatigue"] = clampf(float(c.get("fatigue", 0.2)) - 0.15, 0.05, 1.0)
			rup_delta = 25
			headline = "Sol %d Nightly Feast Convergence (All 16 Citizens)!" % colony_sol
			detail = "All 16 Enclave specialists gathered around Ryn's Banquet Table in the Hearth Galley (Law L13, +25 RUP)!"
		"advance_tick":
			tick_id += 1
			var phase_idx := (tick_id - 1) % DAY_PHASES.size()
			day_phase = DAY_PHASES[phase_idx]
			if phase_idx == 0:
				colony_sol += 1
			rup_delta = 5
			headline = "Advanced to Sol %d — %s" % [colony_sol, day_phase]
			detail = "Chronosphere advanced by +6 hours to Sol %d (%s, Kp %.1f)." % [colony_sol, day_phase, kp_exo]
		_:
			headline = "Willow Explored the Valley"
			detail = "Willow inspected the Enclave surroundings."

	rupees += rup_delta
	story_feed.push_front({
		"sol": colony_sol,
		"day_phase": day_phase,
		"title": headline,
		"summary": detail
	})
	return {
		"ok": true,
		"action_type": action_type,
		"rup_earned": rup_delta,
		"headline": headline,
		"detail": detail,
		"rupees": rupees
	}


func get_specimen(specimen_id: String) -> Dictionary:
	for item in MUSEUM_CATALOG:
		if str(item["specimen_id"]) == specimen_id:
			return item
	return MUSEUM_CATALOG[0]


func get_specimen_name(specimen_id: String) -> String:
	return str(get_specimen(specimen_id).get("name", specimen_id))


func get_recipe(recipe_id: String) -> Dictionary:
	for item in DIY_RECIPES:
		if str(item["recipe_id"]) == recipe_id:
			return item
	return DIY_RECIPES[0]
