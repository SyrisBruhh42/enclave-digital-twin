class_name ZoneManager
extends Node2D
## Manages the 5 Connected Hoenn Overworld Zones (30x20 metatiles = 960x640 px)
## and 3 Enterable Indoor Rooms (15x12 metatiles = 480x384 px) with 0.22s GBA warps.

const EnclaveStateBridgeScript = preload("res://engine/enclave_state_bridge.gd")
const EnclaveCitizenNPCScript = preload("res://engine/enclave_citizen_npc.gd")

signal zone_loaded(zone_id: String, zone_meta: Dictionary)
signal warp_triggered(target_zone_id: String, target_spawn_pos: Vector2)

const OUTDOOR_COLS: int = 30
const OUTDOOR_ROWS: int = 20
const INDOOR_COLS: int = 15
const INDOOR_ROWS: int = 12
const TILE_PX: int = 32

const ZONE_CATALOG: Dictionary = {
	"zone_01_homestead_grove": {
		"zone_id": "zone_01_homestead_grove",
		"title": "🌿 HOMESTEAD GROVE",
		"subtitle": "Willow's Alchemist Homestead & Genesis Garden",
		"biome_id": "genesis_terraces",
		"hearth_biome": "Rain Garden",
		"is_indoor": false,
		"cols": OUTDOOR_COLS,
		"rows": OUTDOOR_ROWS,
		"default_spawn": Vector2(480, 320),
		"exits": {
			"NORTH": {"target_zone": "zone_02_hearth_plaza", "spawn": Vector2(480, 576)},
			"EAST": {"target_zone": "zone_05_ferro_basin", "spawn": Vector2(64, 320)}
		}
	},
	"zone_02_hearth_plaza": {
		"zone_id": "zone_02_hearth_plaza",
		"title": "🔥 HEARTH PLAZA",
		"subtitle": "Central Main Bus, Sibling Post & Outfitters",
		"biome_id": "crater_valley",
		"hearth_biome": "Porch Hearth",
		"is_indoor": false,
		"cols": OUTDOOR_COLS,
		"rows": OUTDOOR_ROWS,
		"default_spawn": Vector2(480, 360),
		"exits": {
			"SOUTH": {"target_zone": "zone_01_homestead_grove", "spawn": Vector2(480, 64)},
			"EAST": {"target_zone": "zone_03_forge_caldera", "spawn": Vector2(64, 320)},
			"WEST": {"target_zone": "zone_04_simulacrum_crest", "spawn": Vector2(896, 320)},
			"NORTH": {"target_zone": "zone_05_ferro_basin", "spawn": Vector2(480, 576)}
		}
	},
	"zone_03_forge_caldera": {
		"zone_id": "zone_03_forge_caldera",
		"title": "⚒️ FORGE CALDERA",
		"subtitle": "The First Forge, Stormbreaker & Basalt Ledges",
		"biome_id": "forge_caldera",
		"hearth_biome": "Alchemist Crucible",
		"is_indoor": false,
		"cols": OUTDOOR_COLS,
		"rows": OUTDOOR_ROWS,
		"default_spawn": Vector2(128, 320),
		"exits": {
			"WEST": {"target_zone": "zone_02_hearth_plaza", "spawn": Vector2(896, 320)}
		}
	},
	"zone_04_simulacrum_crest": {
		"zone_id": "zone_04_simulacrum_crest",
		"title": "🔮 SIMULACRUM CREST",
		"subtitle": "Helmholtz Rotunda, Lyceum & Spore Glade",
		"biome_id": "spore_glade",
		"hearth_biome": "Flow Hourglass",
		"is_indoor": false,
		"cols": OUTDOOR_COLS,
		"rows": OUTDOOR_ROWS,
		"default_spawn": Vector2(832, 320),
		"exits": {
			"EAST": {"target_zone": "zone_02_hearth_plaza", "spawn": Vector2(64, 320)}
		}
	},
	"zone_05_ferro_basin": {
		"zone_id": "zone_05_ferro_basin",
		"title": "🏛️ FERROFLUID BASIN",
		"subtitle": "Living Atlas Museum, Tide Pier & Sanctuary",
		"biome_id": "storm_ridge",
		"hearth_biome": "Rain Garden",
		"is_indoor": false,
		"cols": OUTDOOR_COLS,
		"rows": OUTDOOR_ROWS,
		"default_spawn": Vector2(480, 352),
		"exits": {
			"SOUTH": {"target_zone": "zone_02_hearth_plaza", "spawn": Vector2(480, 64)},
			"WEST": {"target_zone": "zone_01_homestead_grove", "spawn": Vector2(896, 320)}
		}
	},
	"room_willow_home": {
		"zone_id": "room_willow_home",
		"title": "🏡 WILLOW'S HOMESTEAD",
		"subtitle": "Copper Alembic Lab, Wardrobe Mirror & Cozy Loft",
		"biome_id": "genesis_terraces",
		"hearth_biome": "Alchemist Crucible",
		"is_indoor": true,
		"cols": INDOOR_COLS,
		"rows": INDOOR_ROWS,
		"default_spawn": Vector2(240, 312),
		"exits": {
			"DOOR_EXIT": {"target_zone": "zone_01_homestead_grove", "spawn": Vector2(480, 312)}
		}
	},
	"room_hearth_galley": {
		"zone_id": "room_hearth_galley",
		"title": "🍲 HEARTH & METABOLIC GALLEY",
		"subtitle": "16-Seat Banquet Table, Steam-Oven & Nightly Feast Bell",
		"biome_id": "crater_valley",
		"hearth_biome": "Porch Hearth",
		"is_indoor": true,
		"cols": INDOOR_COLS,
		"rows": INDOOR_ROWS,
		"default_spawn": Vector2(240, 312),
		"exits": {
			"DOOR_EXIT": {"target_zone": "zone_02_hearth_plaza", "spawn": Vector2(480, 312)}
		}
	},
	"room_atlas_museum": {
		"zone_id": "room_atlas_museum",
		"title": "🏛️ LIVING ATLAS MUSEUM",
		"subtitle": "Dorian & Vex Curator Hall — 16 Specimens (TIER_1..TIER_4)",
		"biome_id": "storm_ridge",
		"hearth_biome": "Flow Hourglass",
		"is_indoor": true,
		"cols": INDOOR_COLS,
		"rows": INDOOR_ROWS,
		"default_spawn": Vector2(240, 312),
		"exits": {
			"DOOR_EXIT": {"target_zone": "zone_05_ferro_basin", "spawn": Vector2(480, 312)}
		}
	}
}

var active_zone_id: String = "zone_01_homestead_grove"
var sprite_factory: RefCounted = null
var state_bridge: RefCounted = null
var tutorial_director: RefCounted = null

var tile_layer: Node2D = null
var object_layer: Node2D = null
var tutorial_arrow_sprite: Sprite2D = null

var _tile_grid: Array = []
var _solid_rects: Array[Rect2] = []
var _door_warps: Array[Dictionary] = []
var _interactables: Array[Dictionary] = []
var _active_npcs: Array[Node2D] = []
var _anim_tick: int = 0
var _anim_timer: float = 0.0
var _arrow_bob_time: float = 0.0


func setup(factory: RefCounted, bridge: RefCounted, tut: RefCounted) -> void:
	sprite_factory = factory
	state_bridge = bridge
	tutorial_director = tut

	if tile_layer == null:
		tile_layer = Node2D.new()
		tile_layer.name = "TileLayer"
		add_child(tile_layer)

	if object_layer == null:
		object_layer = Node2D.new()
		object_layer.name = "ObjectLayer"
		object_layer.y_sort_enabled = true
		add_child(object_layer)

	if tutorial_arrow_sprite == null:
		tutorial_arrow_sprite = Sprite2D.new()
		tutorial_arrow_sprite.name = "TutorialArrow"
		tutorial_arrow_sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		tutorial_arrow_sprite.texture = sprite_factory.call("get_prop_texture", "tutorial_arrow", 0)
		tutorial_arrow_sprite.z_index = 25
		add_child(tutorial_arrow_sprite)


static func get_all_zone_ids() -> Array[String]:
	return [
		"zone_01_homestead_grove",
		"zone_02_hearth_plaza",
		"zone_03_forge_caldera",
		"zone_04_simulacrum_crest",
		"zone_05_ferro_basin",
		"room_willow_home",
		"room_hearth_galley",
		"room_atlas_museum"
	]


func get_active_zone_meta() -> Dictionary:
	return ZONE_CATALOG.get(active_zone_id, ZONE_CATALOG["zone_01_homestead_grove"])


func get_active_zone_pixel_size() -> Vector2:
	var meta := get_active_zone_meta()
	return Vector2(float(int(meta["cols"]) * TILE_PX), float(int(meta["rows"]) * TILE_PX))


func load_zone(zone_id: String) -> Dictionary:
	if not ZONE_CATALOG.has(zone_id):
		zone_id = "zone_01_homestead_grove"
	active_zone_id = zone_id
	var meta: Dictionary = ZONE_CATALOG[zone_id]

	for child in tile_layer.get_children():
		tile_layer.remove_child(child)
		child.free()
	for child in object_layer.get_children():
		object_layer.remove_child(child)
		child.free()

	_tile_grid.clear()
	_solid_rects.clear()
	_door_warps.clear()
	_interactables.clear()
	_active_npcs.clear()

	var cols := int(meta["cols"])
	var rows := int(meta["rows"])
	var is_indoor := bool(meta["is_indoor"])

	for y in range(rows):
		var row_arr: Array[String] = []
		for x in range(cols):
			var default_tile := "grass"
			if is_indoor:
				default_tile = "museum_marble" if zone_id == "room_atlas_museum" else "wood_floor"
			elif x == 0 or x == cols - 1 or y == 0 or y == rows - 1:
				default_tile = "tree_border"
			row_arr.append(default_tile)
		_tile_grid.append(row_arr)

	match zone_id:
		"zone_01_homestead_grove":
			_build_zone_01_homestead_grove(cols, rows)
		"zone_02_hearth_plaza":
			_build_zone_02_hearth_plaza(cols, rows)
		"zone_03_forge_caldera":
			_build_zone_03_forge_caldera(cols, rows)
		"zone_04_simulacrum_crest":
			_build_zone_04_simulacrum_crest(cols, rows)
		"zone_05_ferro_basin":
			_build_zone_05_ferro_basin(cols, rows)
		"room_willow_home":
			_build_room_willow_home(cols, rows)
		"room_hearth_galley":
			_build_room_hearth_galley(cols, rows)
		"room_atlas_museum":
			_build_room_atlas_museum(cols, rows)

	_render_tile_grid(cols, rows)
	_update_tutorial_arrow()
	zone_loaded.emit(zone_id, meta)
	return meta


func _set_tile_rect(x0: int, y0: int, w: int, h: int, tile_type: String) -> void:
	for y in range(y0, y0 + h):
		if y >= 0 and y < _tile_grid.size():
			var row_arr: Array = _tile_grid[y]
			for x in range(x0, x0 + w):
				if x >= 0 and x < row_arr.size():
					row_arr[x] = tile_type


func _render_tile_grid(cols: int, rows: int) -> void:
	for y in range(rows):
		var row_arr: Array = _tile_grid[y]
		for x in range(cols):
			var ttype := str(row_arr[x])
			var sp := Sprite2D.new()
			sp.centered = false
			sp.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
			sp.texture = sprite_factory.call("get_terrain_tile", ttype, _anim_tick)
			sp.position = Vector2(float(x * TILE_PX), float(y * TILE_PX))
			sp.set_meta("tile_type", ttype)
			tile_layer.add_child(sp)


func _place_building(
	bldg_id: String,
	title: String,
	center_bottom_pos: Vector2,
	enter_room_id: String = "",
	desc: String = ""
) -> void:
	var tex: ImageTexture = sprite_factory.call("get_building_texture", bldg_id)
	var sp := Sprite2D.new()
	sp.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	sp.texture = tex
	sp.position = center_bottom_pos - Vector2(0, float(tex.get_height()) * 0.5)
	object_layer.add_child(sp)

	var bw := float(tex.get_width())
	var bh := float(tex.get_height())
	var solid := Rect2(center_bottom_pos.x - bw * 0.45, center_bottom_pos.y - bh * 0.72, bw * 0.9, bh * 0.62)
	_solid_rects.append(solid)

	var door_pos := center_bottom_pos + Vector2(0, 6)
	if enter_room_id != "":
		_door_warps.append({
			"rect": Rect2(center_bottom_pos.x - 20, center_bottom_pos.y - 14, 40, 26),
			"target_zone": enter_room_id,
			"spawn": ZONE_CATALOG[enter_room_id]["default_spawn"],
			"title": title
		})
	_interactables.append({
		"type": "building",
		"id": bldg_id,
		"title": title,
		"position": door_pos,
		"enter_room_id": enter_room_id,
		"description": desc if desc != "" else ("%s — An Enclave landmark in %s." % [title, active_zone_id])
	})


func _place_prop(
	prop_id: String,
	prop_type: String,
	world_pos: Vector2,
	interact_type: String,
	title: String,
	payload: Dictionary = {}
) -> void:
	var sp := Sprite2D.new()
	sp.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
	sp.texture = sprite_factory.call("get_prop_texture", prop_type, _anim_tick)
	sp.position = world_pos
	sp.set_meta("prop_type", prop_type)
	object_layer.add_child(sp)

	var entry := payload.duplicate(true)
	entry["type"] = interact_type
	entry["id"] = prop_id
	entry["prop_type"] = prop_type
	entry["title"] = title
	entry["position"] = world_pos
	entry["sprite"] = sp
	_interactables.append(entry)


func _place_citizen(cid: String, world_pos: Vector2, facing: String = "DOWN") -> Node2D:
	var cdata: Dictionary = state_bridge.get("citizens").get(cid, {})
	var npc: Node2D = EnclaveCitizenNPCScript.new()
	npc.call("setup", cid, cdata, sprite_factory, world_pos)
	npc.set("facing_dir", facing)
	npc.call("_refresh_sprite")
	object_layer.add_child(npc)
	_active_npcs.append(npc)

	_interactables.append({
		"type": "npc",
		"id": cid,
		"title": "%s (%s)" % [str(cdata.get("name", cid)), str(cdata.get("epithet", ""))],
		"position": world_pos,
		"npc_ref": npc
	})
	return npc


func _build_zone_01_homestead_grove(_cols: int, _rows: int) -> void:
	_set_tile_rect(13, 0, 4, 15, "sand_path")
	_set_tile_rect(8, 9, 22, 3, "sand_path")
	_set_tile_rect(4, 4, 4, 3, "flowers")
	_set_tile_rect(22, 4, 4, 3, "flowers")
	_set_tile_rect(5, 13, 6, 4, "tall_grass")
	_set_tile_rect(19, 11, 4, 3, "wheat_plot")

	_place_building(
		"bldg_willow_homestead",
		"Willow's Alchemist Homestead",
		Vector2(480, 272),
		"room_willow_home",
		"Willow's cozy pitched-roof cottage with her Copper Alembic DIY Workbench and high-res PBR Wardrobe Mirror inside!"
	)
	_place_building(
		"proj_04_genesis_garden",
		"Genesis Garden Conservatory",
		Vector2(736, 256),
		"",
		"Terra & Willow's chelated greenhouse nurturing Crystalline Iron-Wheat and Spore-Orchids."
	)
	_place_building(
		"bldg_wilds_nook",
		"Wilds Botanical Nook",
		Vector2(208, 256),
		"",
		"Moss-roofed timber cottage hung with heirloom seed braids."
	)

	_place_prop("node_geode_01", "geode_crack", Vector2(320, 416), "resource_node", "Bismuth Geode Fissure", {
		"required_tool": "trowel", "action_type": "forage_dig", "specimen_id": "spec_geode_bismuth"
	})
	_place_prop("node_crop_01", "geode_crack", Vector2(640, 384), "resource_node", "Golden Iron-Wheat Plot", {
		"required_tool": "watering_can", "action_type": "water_crop", "specimen_id": "spec_flora_iron_wheat"
	})
	_place_prop("node_critter_01", "critter_swarm", Vector2(224, 480), "resource_node", "Aurora Prism-Moth Swarm", {
		"required_tool": "bug_net", "action_type": "catch_critter", "specimen_id": "spec_critter_prism_moth"
	})

	_place_citizen("enclave_08_terra", Vector2(416, 336), "DOWN")
	_place_citizen("enclave_03_silas", Vector2(512, 336), "DOWN")


func _build_zone_02_hearth_plaza(cols: int, rows: int) -> void:
	_set_tile_rect(13, 0, 4, rows, "sand_path")
	_set_tile_rect(0, 9, cols, 3, "sand_path")
	_set_tile_rect(9, 6, 12, 9, "cobble_plaza")
	_set_tile_rect(4, 14, 4, 3, "flowers")
	_set_tile_rect(22, 14, 4, 3, "flowers")

	_place_building(
		"proj_08_hearth_metabolic_engine",
		"The Hearth & Metabolic Galley",
		Vector2(480, 240),
		"room_hearth_galley",
		"Central Main Bus dining hall where all 16 citizens gather nightly for The Feast! Step in to ring the Feast Bell."
	)
	_place_building(
		"bldg_curio_pavilion",
		"Aegis Outfitters & Curio Mart",
		Vector2(224, 256),
		"",
		"Steampunk-botanical wardrobe showcase & DIY furniture counter synced with window.ArcadeAssetBridge."
	)
	_place_building(
		"bldg_sibling_post",
		"Sibling Grid Notice Board & Post",
		Vector2(736, 256),
		"",
		"Daily Villager Favor Bulletin Board & friendly 3-Sol Shadow Economy prank dispatch."
	)

	_place_prop("prop_obelisk", "lightning_obelisk", Vector2(480, 384), "landmark_sign", "Central Main Bus Obelisk", {
		"description": "Channels clean geothermal & captured-lightning power across all 4 Enclave squads."
	})
	_place_prop("node_critter_02", "critter_swarm", Vector2(736, 448), "resource_node", "Mycelial Soliton Firefly", {
		"required_tool": "bug_net", "action_type": "catch_critter", "specimen_id": "spec_critter_soliton_firefly"
	})

	_place_citizen("enclave_13_ryn", Vector2(416, 320), "DOWN")
	_place_citizen("enclave_16_elara", Vector2(544, 320), "DOWN")
	_place_citizen("enclave_15_dorian", Vector2(688, 336), "LEFT")


func _build_zone_03_forge_caldera(_cols: int, _rows: int) -> void:
	_set_tile_rect(0, 9, 26, 3, "sand_path")
	_set_tile_rect(6, 7, 20, 1, "cliff_ledge")
	_set_tile_rect(6, 13, 20, 1, "cliff_ledge")

	_place_building("proj_01_first_forge", "The First Forge", Vector2(384, 192), "", "Induction smelter & bismuth-bronze busbar foundry anchored by Silas and Leo.")
	_place_building("proj_02_stormbreaker", "The Stormbreaker Spire", Vector2(672, 192), "", "High-ridge copper lightning harvester & Babbage fluid-loom weather tower.")
	_place_building("bldg_forge_lodge", "Forge Anchor Lodge", Vector2(288, 520), "")
	_place_building("bldg_prodigy_east", "Prodigy Quarters East", Vector2(672, 520), "")

	_place_prop("node_geode_02", "geode_crack", Vector2(528, 352), "resource_node", "Ridge Fulgurite Fissure", {
		"required_tool": "trowel", "action_type": "forage_dig", "specimen_id": "spec_geode_fulgurite"
	})
	_place_prop("node_geode_04", "geode_crack", Vector2(784, 352), "resource_node", "Octahedral Lodestone Outcrop", {
		"required_tool": "trowel", "action_type": "forage_dig", "specimen_id": "spec_geode_lodestone"
	})

	_place_citizen("enclave_04_leo", Vector2(384, 304), "DOWN")
	_place_citizen("enclave_01_hector", Vector2(640, 304), "DOWN")
	_place_citizen("enclave_02_jane", Vector2(720, 304), "DOWN")


func _build_zone_04_simulacrum_crest(_cols: int, _rows: int) -> void:
	_set_tile_rect(4, 9, 26, 3, "sand_path")
	_set_tile_rect(6, 13, 8, 4, "tall_grass")
	_set_tile_rect(18, 13, 6, 4, "flowers")

	_place_building("proj_05_simulacrum", "The Simulacrum Rotunda", Vector2(320, 224), "", "Thirty-two-ring brass Helmholtz ferrofluid phase-space observatory.")
	_place_building("proj_06_lyceum_of_the_mind", "The Lyceum of the Mind", Vector2(640, 224), "", "Acoustic-somatic grounding sanctuary & circadian neuro-harmonics hall.")
	_place_building("bldg_mind_loft", "Mind Contemplative Loft", Vector2(320, 520), "")
	_place_building("bldg_prodigy_west", "Prodigy Quarters West", Vector2(640, 520), "")

	_place_prop("node_geode_03", "geode_crack", Vector2(480, 288), "resource_node", "Singing Piezo-Quartz Cluster", {
		"required_tool": "trowel", "action_type": "forage_dig", "specimen_id": "spec_geode_piezo"
	})
	_place_prop("node_truffle_05", "geode_crack", Vector2(208, 384), "resource_node", "Mycelial Amber Cave-Truffle", {
		"required_tool": "trowel", "action_type": "forage_dig", "specimen_id": "spec_flora_cave_truffle"
	})
	_place_prop("node_critter_03", "critter_swarm", Vector2(256, 464), "resource_node", "Copper-Carapace Pollinator Beetle", {
		"required_tool": "bug_net", "action_type": "catch_critter", "specimen_id": "spec_critter_cave_beetle"
	})

	_place_citizen("enclave_09_orion", Vector2(288, 320), "DOWN")
	_place_citizen("enclave_10_isla", Vector2(368, 320), "DOWN")
	_place_citizen("enclave_11_kenna", Vector2(608, 320), "DOWN")
	_place_citizen("enclave_12_elias", Vector2(688, 320), "DOWN")


func _build_zone_05_ferro_basin(_cols: int, _rows: int) -> void:
	_set_tile_rect(0, 9, 20, 3, "sand_path")
	_set_tile_rect(13, 9, 4, 11, "sand_path")
	_set_tile_rect(18, 11, 10, 7, "water")
	_set_tile_rect(18, 12, 5, 2, "pier_planks")

	_place_building(
		"proj_07_living_atlas",
		"The Living Atlas Colony Museum",
		Vector2(480, 240),
		"room_atlas_museum",
		"Colony Museum of Geodes, Critters, Ferro-Fish & Relics across all 4 SR-05 Epistemic Tiers! Step inside to inspect or donate."
	)
	_place_building("proj_03_sanctuary", "The Sanctuary Paddock", Vector2(208, 240), "", "Mutualistic magnetotropic fauna refuge & acoustic-shielded grove.")
	_place_building("bldg_hub_gables", "Hub Chronicler Gables", Vector2(752, 240), "")

	_place_prop("node_fish_01", "ferro_fish_shadow", Vector2(672, 416), "resource_node", "Coiled Magnetite Ammonite Shadow", {
		"required_tool": "dip_rod", "action_type": "catch_fish", "specimen_id": "spec_fish_ammonite"
	})
	_place_prop("node_fish_02", "ferro_fish_shadow", Vector2(768, 448), "resource_node", "Rosensweig Ribbon-Eel Shadow", {
		"required_tool": "dip_rod", "action_type": "catch_fish", "specimen_id": "spec_fish_rosensweig_eel"
	})
	_place_prop("node_fish_03", "ferro_fish_shadow", Vector2(640, 496), "resource_node", "Silver-Scale Colloidal Darter Shadow", {
		"required_tool": "dip_rod", "action_type": "catch_fish", "specimen_id": "spec_fish_colloidal_pike"
	})
	_place_prop("node_fish_04", "ferro_fish_shadow", Vector2(816, 512), "resource_node", "Vent-Warmth Fulgurite Crab Shadow", {
		"required_tool": "dip_rod", "action_type": "catch_fish", "specimen_id": "spec_fish_fulgurite_crab"
	})
	_place_prop("node_critter_04", "critter_swarm", Vector2(288, 448), "resource_node", "Rainbow Bismuth Skimmer", {
		"required_tool": "bug_net", "action_type": "catch_critter", "specimen_id": "spec_critter_bismuth_dragonfly"
	})

	_place_citizen("enclave_05_kaio", Vector2(560, 384), "RIGHT")
	_place_citizen("enclave_06_zara", Vector2(224, 336), "DOWN")
	_place_citizen("enclave_14_vex", Vector2(416, 304), "DOWN")


func _build_room_willow_home(_cols: int, _rows: int) -> void:
	_set_tile_rect(6, 11, 3, 1, "door_mat")
	_door_warps.append({
		"rect": Rect2(6 * TILE_PX, 11 * TILE_PX - 6, 3 * TILE_PX, TILE_PX + 12),
		"target_zone": "zone_01_homestead_grove",
		"spawn": Vector2(480, 316),
		"title": "Exit to Homestead Grove"
	})

	_place_prop("prop_alembic_workbench", "alembic_workbench", Vector2(160, 160), "diy_workbench", "Copper Alembic DIY Workbench", {
		"recipe_id": "diy_herbal_liniment",
		"description": "Synthesize alchemical tonics (Herbal Joint-Liniment, Chelation Elixir) & SR-02 Tycoon furniture!"
	})
	_place_prop("prop_wardrobe_mirror", "wardrobe_mirror", Vector2(240, 128), "wardrobe_mirror", "Full-Length PBR Wardrobe Mirror", {
		"description": "Inspect Willow's 5-view 3600x1280 PBR Studio Turnaround (WillowStudioLoader + willow_2d_pbr.gdshader)!"
	})
	_place_prop("prop_alchemist_bed", "alchemist_bed", Vector2(336, 160), "alchemist_bed", "Willow's Alchemist Bed", {
		"description": "Rest until the next 6-hour Sol phase and restore calm."
	})


func _build_room_hearth_galley(_cols: int, _rows: int) -> void:
	_set_tile_rect(6, 11, 3, 1, "door_mat")
	_door_warps.append({
		"rect": Rect2(6 * TILE_PX, 11 * TILE_PX - 6, 3 * TILE_PX, TILE_PX + 12),
		"target_zone": "zone_02_hearth_plaza",
		"spawn": Vector2(480, 296),
		"title": "Exit to Hearth Plaza"
	})

	_place_prop("prop_feast_banquet_table", "feast_banquet_table", Vector2(240, 192), "feast_bell", "16-Seat Main Bus Banquet Table", {
		"description": "Where all 16 citizens converge every evening for The Feast (Law L13)."
	})
	_place_prop("prop_feast_bell", "feast_bell", Vector2(336, 128), "feast_bell", "Nightly Feast Convergence Bell", {
		"description": "Ring the brass bell to summon all 16 Enclave citizens for The Feast (+25 RUP)!"
	})
	_place_citizen("enclave_13_ryn", Vector2(160, 160), "DOWN")
	_place_citizen("enclave_16_elara", Vector2(320, 224), "LEFT")


func _build_room_atlas_museum(_cols: int, _rows: int) -> void:
	_set_tile_rect(6, 11, 3, 1, "door_mat")
	_door_warps.append({
		"rect": Rect2(6 * TILE_PX, 11 * TILE_PX - 6, 3 * TILE_PX, TILE_PX + 12),
		"target_zone": "zone_05_ferro_basin",
		"spawn": Vector2(480, 296),
		"title": "Exit to Ferrofluid Basin"
	})

	_place_prop("prop_curator_desk", "curator_desk", Vector2(240, 96), "curator_desk", "Dorian & Vex Curator Desk", {
		"description": "Donate any geode, critter, ferro-fish, or relic to the Living Atlas Concordance!"
	})

	var catalog: Array = EnclaveStateBridgeScript.MUSEUM_CATALOG
	var donated: Array = state_bridge.get("donated_specimen_ids")
	for idx in range(catalog.size()):
		var spec: Dictionary = catalog[idx]
		var sid := str(spec["specimen_id"])
		var col_idx := idx % 4
		var row_idx := idx / 4
		var px := 96.0 + float(col_idx) * 96.0
		var py := 148.0 + float(row_idx) * 46.0
		var is_donated := sid in donated
		var ptype := "museum_pedestal_donated" if is_donated else "museum_pedestal_empty"
		_place_prop(
			"pedestal_" + sid,
			ptype,
			Vector2(px, py),
			"museum_pedestal",
			"%s (%s)" % [str(spec["name"]), str(spec["epistemic_tier"])],
			{"specimen_id": sid, "specimen": spec}
		)

	_place_citizen("enclave_15_dorian", Vector2(192, 96), "DOWN")
	_place_citizen("enclave_14_vex", Vector2(288, 96), "DOWN")


func get_tile_type_at(world_pos: Vector2) -> String:
	var tx := int(floor(world_pos.x / float(TILE_PX)))
	var ty := int(floor(world_pos.y / float(TILE_PX)))
	if ty < 0 or ty >= _tile_grid.size():
		return "tree_border"
	var row_arr: Array = _tile_grid[ty]
	if tx < 0 or tx >= row_arr.size():
		return "tree_border"
	return str(row_arr[tx])


func is_walkable_world_pos(world_pos: Vector2) -> bool:
	var meta := get_active_zone_meta()
	var max_w := float(int(meta["cols"]) * TILE_PX)
	var max_h := float(int(meta["rows"]) * TILE_PX)
	if world_pos.x < 12.0 or world_pos.x > max_w - 12.0 or world_pos.y < 12.0 or world_pos.y > max_h - 8.0:
		return false

	var ttype := get_tile_type_at(world_pos)
	if ttype in ["water", "cliff_ledge", "tree_border"]:
		return false

	for r in _solid_rects:
		if r.has_point(world_pos):
			return false
	return true


func can_hop_ledge_south(player_pos: Vector2) -> bool:
	var below_pos := player_pos + Vector2(0, 24)
	var land_pos := player_pos + Vector2(0, 64)
	if get_tile_type_at(below_pos) == "cliff_ledge" and is_walkable_world_pos(land_pos):
		return true
	return false


func check_warp_triggers(player_pos: Vector2) -> Dictionary:
	for dw in _door_warps:
		var r: Rect2 = dw["rect"]
		if r.has_point(player_pos):
			return dw

	var meta := get_active_zone_meta()
	if bool(meta.get("is_indoor", false)):
		return {}
	var exits: Dictionary = meta.get("exits", {})
	var max_w := float(int(meta["cols"]) * TILE_PX)
	var max_h := float(int(meta["rows"]) * TILE_PX)

	if player_pos.y <= 26.0 and exits.has("NORTH"):
		return exits["NORTH"]
	if player_pos.y >= max_h - 26.0 and exits.has("SOUTH"):
		return exits["SOUTH"]
	if player_pos.x >= max_w - 26.0 and exits.has("EAST"):
		return exits["EAST"]
	if player_pos.x <= 26.0 and exits.has("WEST"):
		return exits["WEST"]
	return {}


func find_nearest_interactable(world_pos: Vector2, max_dist: float = 48.0) -> Dictionary:
	var best: Dictionary = {}
	var best_d := max_dist
	for item in _interactables:
		var ipos: Vector2 = item.get("position", Vector2.ZERO)
		var d := world_pos.distance_to(ipos)
		if d <= best_d:
			best_d = d
			best = item
	return best


func refresh_museum_pedestals() -> void:
	if active_zone_id != "room_atlas_museum":
		return
	var donated: Array = state_bridge.get("donated_specimen_ids")
	for item in _interactables:
		if str(item.get("type")) == "museum_pedestal":
			var sid := str(item.get("specimen_id", ""))
			var sp: Sprite2D = item.get("sprite", null)
			if sp != null:
				var ptype := "museum_pedestal_donated" if sid in donated else "museum_pedestal_empty"
				sp.texture = sprite_factory.call("get_prop_texture", ptype, _anim_tick)


func _process(delta: float) -> void:
	_anim_timer += delta
	if _anim_timer >= 0.45:
		_anim_timer = 0.0
		_anim_tick = (_anim_tick + 1) % 4
		for child in tile_layer.get_children():
			if child is Sprite2D and child.has_meta("tile_type"):
				var ttype := str(child.get_meta("tile_type"))
				if ttype in ["water", "flowers", "tall_grass", "cobble_plaza"]:
					(child as Sprite2D).texture = sprite_factory.call("get_terrain_tile", ttype, _anim_tick)
		for item in _interactables:
			var sp: Sprite2D = item.get("sprite", null)
			if sp != null and sp.has_meta("prop_type"):
				var ptype := str(sp.get_meta("prop_type"))
				if ptype in ["critter_swarm", "ferro_fish_shadow"]:
					sp.texture = sprite_factory.call("get_prop_texture", ptype, _anim_tick)

	_arrow_bob_time += delta * 5.0
	_update_tutorial_arrow()


func _update_tutorial_arrow() -> void:
	if tutorial_arrow_sprite == null or tutorial_director == null:
		return
	var target: Vector2 = tutorial_director.call("get_arrow_world_position", active_zone_id)
	if target.x < -100.0:
		tutorial_arrow_sprite.visible = false
	else:
		tutorial_arrow_sprite.visible = true
		var bob := sin(_arrow_bob_time) * 5.0 if not bool(state_bridge.get("reduced_motion")) else 0.0
		tutorial_arrow_sprite.position = target + Vector2(0, -48.0 + bob)
