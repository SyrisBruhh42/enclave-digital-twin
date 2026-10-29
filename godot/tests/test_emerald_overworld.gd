extends SceneTree
## Headless Verification Suite for The Enclave of the 16 — Pokémon Emerald (Gen-3 Hoenn) Overworld.
## Run via:
##   godot --headless --path <path-to-godot-dir> -s res://tests/test_emerald_overworld.gd --quit

const WillowStudioLoaderScript = preload("res://engine/willow_studio_loader.gd")
const EmeraldSpriteFactoryScript = preload("res://engine/emerald_sprite_factory.gd")
const EnclaveStateBridgeScript = preload("res://engine/enclave_state_bridge.gd")
const ZoneManagerScript = preload("res://engine/zone_manager.gd")

var _failures: Array[String] = []
var _checks_passed: int = 0


func _assert_true(cond: bool, msg: String) -> void:
	if cond:
		_checks_passed += 1
	else:
		_failures.append(msg)
		push_error("ASSERT FAILED: " + msg)


var _ran: bool = false


func _process(_delta: float) -> bool:
	if _ran:
		return true
	_ran = true
	print("=== [CP-12 STAGE_2] Starting Enclave Pokémon Emerald Overworld Headless Verification ===")

	# 1. Verify project.godot settings & LDS Theme
	var vw := int(ProjectSettings.get_setting("display/window/size/viewport_width", 0))
	var vh := int(ProjectSettings.get_setting("display/window/size/viewport_height", 0))
	var tex_filter := int(ProjectSettings.get_setting("rendering/textures/canvas_textures/default_texture_filter", -1))
	_assert_true(vw == 480 and vh == 320, "Viewport must be 480x320 GBA 3:2 resolution (got %dx%d)" % [vw, vh])
	_assert_true(tex_filter == 0, "Default texture filter must be 0 (Nearest) for crisp pixel art")

	var lds_theme := load("res://aegis_lds_theme.tres") as Theme
	_assert_true(lds_theme != null, "res://aegis_lds_theme.tres must load cleanly")

	# 2. Verify all 6 reused suite shaders
	var shader_paths: Array[String] = [
		"res://shaders/willow_2d_pbr.gdshader",
		"res://shaders/god_ray_caustics.gdshader",
		"res://shaders/elevation_lut.gdshader",
		"res://shaders/rough_stone_bevel.gdshader",
		"res://shaders/oklab_colorblind_filter.gdshader",
		"res://shaders/sewer_flow_distortion.gdshader"
	]
	for spath in shader_paths:
		var sh := load(spath) as Shader
		_assert_true(sh != null, "Shader must load cleanly: " + spath)

	# 3. Verify WillowStudioLoader (5 PBR views & CM-02 flip_h == false invariant)
	var loader: RefCounted = WillowStudioLoaderScript.new()
	var loaded_ok: bool = loader.call("load_studio_bundle")
	_assert_true(loaded_ok and bool(loader.get("is_loaded")), "WillowStudioLoader must resolve and load the 5-view PBR studio bundle")
	_assert_true(loader.call("get_canvas_texture") != null, "WillowStudioLoader must build a CanvasTexture")
	for vid in WillowStudioLoaderScript.VIEW_ORDER:
		var atex: AtlasTexture = loader.call("get_view_atlas_texture", vid)
		var vmeta: Dictionary = loader.call("get_view_metadata", vid)
		_assert_true(atex != null and atex.get_width() == 720 and atex.get_height() == 1280, "View %s must be 720x1280" % vid)
		_assert_true(bool(vmeta.get("flip_h", true)) == false, "CM-02 Invariant: View %s must enforce flip_h == false" % vid)

	# 4. Verify EmeraldSpriteFactory (Terrain Tiles, Pitched-Roof Buildings, Willow Sprite, 16 Citizens)
	var factory: RefCounted = EmeraldSpriteFactoryScript.new()
	var tile_types: Array[String] = [
		"grass", "tall_grass", "water", "sand_path", "cobble_plaza",
		"cliff_ledge", "flowers", "wheat_plot", "wood_floor", "museum_marble",
		"pier_planks", "door_mat", "tree_border"
	]
	for ttype in tile_types:
		var ttex: ImageTexture = factory.call("get_terrain_tile", ttype, 0)
		_assert_true(ttex != null and ttex.get_width() == 32 and ttex.get_height() == 32, "Terrain tile %s must be 32x32" % ttype)

	var bldg_ids: Array[String] = [
		"bldg_willow_homestead", "proj_08_hearth_metabolic_engine", "proj_07_living_atlas",
		"proj_01_first_forge", "proj_02_stormbreaker", "bldg_curio_pavilion",
		"bldg_sibling_post", "proj_05_simulacrum", "proj_06_lyceum_of_the_mind",
		"proj_03_sanctuary", "proj_04_genesis_garden"
	]
	for bid in bldg_ids:
		var btex: ImageTexture = factory.call("get_building_texture", bid)
		_assert_true(btex != null and btex.get_width() >= 96 and btex.get_height() >= 80, "Building %s texture must generate" % bid)

	for dir_name in ["DOWN", "UP", "LEFT", "RIGHT"]:
		for wf in range(4):
			var wtex: ImageTexture = factory.call("get_willow_frame", dir_name, wf, "trowel", false)
			_assert_true(wtex != null and wtex.get_width() == 32 and wtex.get_height() == 48, "Willow frame %s_%d must be 32x48" % [dir_name, wf])

	var up_img: Image = factory.call("_render_willow_frame_image", "UP", 0, "", false)
	var down_img: Image = factory.call("_render_willow_frame_image", "DOWN", 0, "", false)
	_assert_true(EmeraldSpriteFactoryScript.verify_willow_up_frame_hides_eyes(up_img), "Willow UP dorsal frame must hide glowing emerald eyes")
	_assert_true(not EmeraldSpriteFactoryScript.verify_willow_up_frame_hides_eyes(down_img), "Willow DOWN frame must display glowing #00FF66 emerald eyes")

	for cid in EnclaveStateBridgeScript.CANONICAL_16_IDS:
		var ctex: ImageTexture = factory.call("get_citizen_frame", cid, "DOWN", 0)
		var ptex: ImageTexture = factory.call("get_citizen_portrait", cid)
		_assert_true(ctex != null and ctex.get_width() == 32 and ctex.get_height() == 48, "Citizen %s sprite must be 32x48" % cid)
		_assert_true(ptex != null and ptex.get_width() == 64 and ptex.get_height() == 64, "Citizen %s portrait must be 64x64" % cid)

	# 5. Instantiate Main Scene & Verify All 5 Outdoor Zones + 3 Indoor Rooms
	var main_packed := load("res://scenes/emerald_overworld.tscn") as PackedScene
	_assert_true(main_packed != null, "res://scenes/emerald_overworld.tscn must load as PackedScene")
	var overworld: Node2D = main_packed.instantiate()
	root.add_child(overworld)

	var wp: CharacterBody2D = overworld.get("willow_player")
	var zm: Node2D = overworld.get("zone_manager")
	var sb: RefCounted = overworld.get("state_bridge")
	var td: RefCounted = overworld.get("tutorial_director")
	var hud: CanvasLayer = overworld.get("hud")

	_assert_true(wp != null and wp.get("camera") != null, "WillowPlayer and centered Camera2D must initialize")
	_assert_true((wp.get("sprite") as Sprite2D).flip_h == false, "WillowPlayer sprite.flip_h must be false (CM-02)")

	# Test facing LEFT keeps flip_h == false
	wp.set("facing_dir", "LEFT")
	wp.call("_refresh_sprite")
	_assert_true((wp.get("sprite") as Sprite2D).flip_h == false, "WillowPlayer LEFT facing must keep flip_h == false (CM-02)")

	# Verify all 5 outdoor zones and 3 indoor rooms load cleanly
	var all_zones: Array[String] = ZoneManagerScript.get_all_zone_ids()
	_assert_true(all_zones.size() == 8, "ZoneManager must provide 5 outdoor zones + 3 indoor rooms (8 total)")
	for zid in all_zones:
		overworld.call("warp_to_zone", zid, Vector2(-1, -1), true)
		_assert_true(str(zm.get("active_zone_id")) == zid, "Zone %s must load as active zone" % zid)
		_assert_true((zm.get("tile_layer") as Node2D).get_child_count() > 0, "Zone %s must populate terrain tiles" % zid)

	# Verify 16 Museum Pedestals inside room_atlas_museum
	overworld.call("warp_to_zone", "room_atlas_museum", Vector2(-1, -1), true)
	var pedestal_count := 0
	var interactables: Array = zm.get("_interactables")
	for item in interactables:
		if str((item as Dictionary).get("type")) == "museum_pedestal":
			pedestal_count += 1
	_assert_true(pedestal_count == 16, "room_atlas_museum must contain all 16 specimen pedestals (got %d)" % pedestal_count)

	# Verify one-way GBA Ledge Hop in zone_03_forge_caldera
	overworld.call("warp_to_zone", "zone_03_forge_caldera", Vector2(320, 204), true)
	_assert_true(bool(zm.call("can_hop_ledge_south", Vector2(320, 204))), "zone_03_forge_caldera must allow hopping south over cliff_ledge at y=224")
	wp.position = Vector2(320, 204)
	wp.call("start_ledge_hop")
	_assert_true(bool(wp.get("is_hopping_ledge")), "WillowPlayer must enter ledge hop state")
	wp.call("_update_ledge_hop", 0.30)
	_assert_true(not bool(wp.get("is_hopping_ledge")) and wp.position.y > 260.0, "WillowPlayer must complete parabolic ledge hop south")

	# 6. Verify All 6 Tools & Complete All 6 Guided Tutorial Steps
	overworld.call("warp_to_zone", "zone_01_homestead_grove", Vector2(480, 320), true)
	td.call("restart_tutorial")
	var start_rup := int(sb.get("rupees"))

	# Step 1: Talk to Mentor Terra/Silas
	var step1_msg := str(td.call("notify_event", "talk_npc"))
	_assert_true(step1_msg != "" and int(td.get("current_step")) == 2, "Tutorial Step 1 (talk_npc) must advance to Step 2")

	# Step 2: Use Copper Trowel (forage_dig)
	overworld.call("execute_tool_or_world_action", "forage_dig", {"specimen_id": "spec_geode_bismuth"})
	_assert_true(int(td.get("current_step")) == 3, "Tutorial Step 2 (forage_dig) must advance to Step 3")

	# Step 3: Use Watering Can (water_crop)
	overworld.call("execute_tool_or_world_action", "water_crop", {})
	_assert_true(int(td.get("current_step")) == 4, "Tutorial Step 3 (water_crop) must advance to Step 4")

	# Step 4: Use Bug Net (catch_critter)
	overworld.call("execute_tool_or_world_action", "catch_critter", {"specimen_id": "spec_critter_prism_moth"})
	_assert_true(int(td.get("current_step")) == 5, "Tutorial Step 4 (catch_critter) must advance to Step 5")

	# Step 5: Enter Willow's Homestead & Craft at Copper Alembic Workbench (craft_diy)
	overworld.call("warp_to_zone", "room_willow_home", Vector2(-1, -1), true)
	overworld.call("execute_tool_or_world_action", "craft_diy", {"recipe_id": "diy_herbal_liniment"})
	_assert_true(int(td.get("current_step")) == 6, "Tutorial Step 5 (craft_diy) must advance to Step 6")

	# Step 6: Gift citizen or Donate to Museum (completes tutorial!)
	overworld.call("execute_tool_or_world_action", "gift_citizen", {"target_id": "enclave_03_silas"})
	_assert_true(bool(td.get("is_completed")), "Tutorial Step 6 (gift_citizen) must mark tutorial completed")

	# Also test Dip-Rod fishing, Tinker Wrench decor, Museum donation, and Nightly Feast
	overworld.call("execute_tool_or_world_action", "catch_fish", {"specimen_id": "spec_fish_ammonite"})
	overworld.call("execute_tool_or_world_action", "place_decor", {"recipe_id": "diy_bismuth_lantern"})
	overworld.call("execute_tool_or_world_action", "donate_museum", {"specimen_id": "spec_geode_bismuth"})
	overworld.call("execute_tool_or_world_action", "trigger_feast", {})
	_assert_true(int(sb.get("rupees")) > start_rup + 50, "Rupee balance must increase after completing actions and feast")

	# Verify all 4 LDS Theme Packs apply cleanly
	for pack in EnclaveStateBridgeScript.LDS_THEME_PACKS:
		hud.call("apply_lds_theme_pack", pack)
		_assert_true(str(sb.get("theme_pack")) == pack, "LDS Theme pack %s must apply" % pack)

	overworld.free()

	if _failures.is_empty():
		print("=== PASS: All %d Enclave Pokémon Emerald Overworld checks succeeded with 0 errors! ===" % _checks_passed)
		quit(0)
	else:
		print("=== FAIL: %d errors encountered ===" % _failures.size())
		quit(1)
	return true
