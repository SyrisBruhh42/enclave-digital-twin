class_name EmeraldOverworldMain
extends Node2D
## Root Orchestrator for The Enclave of the 16 — Pokémon Emerald (Gen-3 Hoenn) Overworld.
## Connects EmeraldSpriteFactory, WillowStudioLoader, ProceduralAudio, EnclaveStateBridge,
## TutorialDirector, ZoneManager, WillowPlayer, and EmeraldHUD.

const EmeraldSpriteFactoryScript = preload("res://engine/emerald_sprite_factory.gd")
const WillowStudioLoaderScript = preload("res://engine/willow_studio_loader.gd")
const ProceduralAudioScript = preload("res://engine/procedural_audio.gd")
const EnclaveStateBridgeScript = preload("res://engine/enclave_state_bridge.gd")
const TutorialDirectorScript = preload("res://engine/tutorial_director.gd")
const ZoneManagerScript = preload("res://engine/zone_manager.gd")
const WillowPlayerScript = preload("res://engine/willow_player.gd")
const EmeraldHUDScript = preload("res://engine/emerald_hud.gd")

var sprite_factory: RefCounted = null
var studio_loader: RefCounted = null
var procedural_audio: RefCounted = null
var state_bridge: RefCounted = null
var tutorial_director: RefCounted = null

var zone_manager: Node2D = null
var willow_player: CharacterBody2D = null
var hud: CanvasLayer = null
var sfx_player: AudioStreamPlayer = null

var _is_warping: bool = false
var _warp_cooldown: float = 0.0


func _ready() -> void:
	sprite_factory = EmeraldSpriteFactoryScript.new()
	studio_loader = WillowStudioLoaderScript.new()
	studio_loader.call("load_studio_bundle")
	procedural_audio = ProceduralAudioScript.new(20261025)
	state_bridge = EnclaveStateBridgeScript.new()
	tutorial_director = TutorialDirectorScript.new()

	sfx_player = AudioStreamPlayer.new()
	sfx_player.name = "SFXPlayer"
	add_child(sfx_player)

	zone_manager = ZoneManagerScript.new()
	zone_manager.name = "ZoneManager"
	zone_manager.call("setup", sprite_factory, state_bridge, tutorial_director)
	add_child(zone_manager)

	willow_player = WillowPlayerScript.new()
	willow_player.name = "WillowPlayer"
	willow_player.call("setup", sprite_factory, zone_manager)
	(zone_manager.get("object_layer") as Node2D).add_child(willow_player)

	hud = EmeraldHUDScript.new()
	hud.name = "EmeraldHUD"
	hud.call("setup", state_bridge, tutorial_director, studio_loader, sprite_factory)
	add_child(hud)

	# Wire signals
	willow_player.connect("request_interact", _on_player_interact)
	willow_player.connect("request_use_tool", _on_player_use_tool)
	willow_player.connect("request_cycle_tool", _on_player_cycle_tool)
	willow_player.connect("request_select_tool_slot", _on_player_select_tool_slot)
	willow_player.connect("ledge_hop_completed", _on_player_ledge_hop_completed)

	hud.connect("dialogue_choice_selected", _on_hud_dialogue_choice)
	hud.connect("dialogue_closed", func() -> void: willow_player.set("controls_locked", false))
	hud.connect("fast_travel_requested", func(zid: String) -> void: warp_to_zone(zid, Vector2(-1, -1), false))
	hud.connect("craft_recipe_requested", func(rid: String) -> void: execute_tool_or_world_action("craft_diy", {"recipe_id": rid}))
	hud.connect("donate_specimen_requested", func(sid: String) -> void: execute_tool_or_world_action("donate_museum", {"specimen_id": sid}))
	hud.connect("feast_requested", func() -> void: execute_tool_or_world_action("trigger_feast", {}))
	hud.connect("advance_tick_requested", func() -> void: execute_tool_or_world_action("advance_tick", {}))

	tutorial_director.connect("step_changed", func(_s: int, _d: Dictionary) -> void:
		hud.call("refresh_pills")
		zone_manager.call("_update_tutorial_arrow")
	)
	tutorial_director.connect("tutorial_completed", func() -> void:
		hud.call("refresh_pills")
		zone_manager.call("_update_tutorial_arrow")
	)

	warp_to_zone("zone_01_homestead_grove", Vector2(480, 320), true)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and not event.echo:
		var kev := event as InputEventKey
		if kev.keycode in [KEY_ENTER, KEY_KP_ENTER, KEY_ESCAPE, KEY_M]:
			var dlg_box: Panel = hud.get("dialogue_box")
			if dlg_box.visible:
				hud.call("hide_dialogue")
				willow_player.set("controls_locked", false)
			else:
				hud.call("toggle_start_menu")
				var start_panel: Panel = hud.get("start_menu_panel")
				willow_player.set("controls_locked", start_panel.visible)


func _physics_process(delta: float) -> void:
	if _warp_cooldown > 0.0:
		_warp_cooldown -= delta
		return
	if _is_warping or bool(willow_player.get("controls_locked")) or bool(willow_player.get("is_hopping_ledge")):
		return

	var warp_info: Dictionary = zone_manager.call("check_warp_triggers", willow_player.position)
	if not warp_info.is_empty():
		var target_z := str(warp_info.get("target_zone", ""))
		var spawn_p: Vector2 = warp_info.get("spawn", Vector2(-1, -1))
		if target_z != "":
			warp_to_zone(target_z, spawn_p, false)


func warp_to_zone(target_zone_id: String, custom_spawn: Vector2 = Vector2(-1, -1), instant: bool = false) -> void:
	if not ZoneManagerScript.ZONE_CATALOG.has(target_zone_id):
		return
	_is_warping = true
	_warp_cooldown = 0.35
	_play_sfx(procedural_audio.call("get_sfx_door"))

	if instant or bool(state_bridge.get("reduced_motion")):
		_perform_zone_switch(target_zone_id, custom_spawn)
		_is_warping = false
		return

	willow_player.set("controls_locked", true)
	var curtain: ColorRect = hud.get("fade_curtain")
	var tw := create_tween()
	tw.tween_property(curtain, "color:a", 1.0, 0.11)
	tw.tween_callback(func() -> void: _perform_zone_switch(target_zone_id, custom_spawn))
	tw.tween_property(curtain, "color:a", 0.0, 0.11)
	tw.tween_callback(func() -> void:
		willow_player.set("controls_locked", false)
		_is_warping = false
	)


func _perform_zone_switch(target_zone_id: String, custom_spawn: Vector2) -> void:
	if willow_player.get_parent() != null:
		willow_player.get_parent().remove_child(willow_player)

	var meta: Dictionary = zone_manager.call("load_zone", target_zone_id)
	(zone_manager.get("object_layer") as Node2D).add_child(willow_player)

	var spawn := custom_spawn if custom_spawn.x >= 0.0 else (meta.get("default_spawn", Vector2(240, 240)) as Vector2)
	willow_player.position = spawn
	willow_player.call("configure_camera_limits", zone_manager.call("get_active_zone_pixel_size"), bool(meta.get("is_indoor", false)))
	hud.call("show_zone_banner", str(meta.get("title", target_zone_id)), str(meta.get("subtitle", "")))
	hud.call("refresh_pills")


func _on_player_cycle_tool(delta: int) -> void:
	var t: Dictionary = state_bridge.call("cycle_tool", delta)
	willow_player.set("equipped_tool_id", str(t["tool_id"]))
	willow_player.call("_refresh_sprite")
	hud.call("refresh_pills")


func _on_player_select_tool_slot(slot_idx: int) -> void:
	var t: Dictionary = state_bridge.call("select_tool_slot", slot_idx)
	willow_player.set("equipped_tool_id", str(t["tool_id"]))
	willow_player.call("_refresh_sprite")
	hud.call("refresh_pills")


func _on_player_ledge_hop_completed(_landed_pos: Vector2) -> void:
	_play_sfx(procedural_audio.call("get_sfx_ledge_jump"))


func _on_player_interact(facing_point: Vector2) -> void:
	var dlg_box: Panel = hud.get("dialogue_box")
	if dlg_box.visible:
		hud.call("hide_dialogue")
		willow_player.set("controls_locked", false)
		return

	var target: Dictionary = zone_manager.call("find_nearest_interactable", facing_point, 56.0)
	if target.is_empty():
		target = zone_manager.call("find_nearest_interactable", willow_player.position, 56.0)
	if target.is_empty():
		return

	var itype := str(target.get("type", ""))
	match itype:
		"npc":
			_interact_with_npc(target)
		"resource_node":
			var req_tool := str(target.get("required_tool", "trowel"))
			state_bridge.call("select_tool_by_id", req_tool)
			willow_player.call("trigger_tool_pose", req_tool)
			execute_tool_or_world_action(str(target.get("action_type", "forage_dig")), {
				"specimen_id": str(target.get("specimen_id", "spec_geode_bismuth"))
			})
		"diy_workbench":
			_interact_with_workbench()
		"wardrobe_mirror":
			hud.call("open_willow_card_modal")
		"alchemist_bed":
			execute_tool_or_world_action("advance_tick", {})
		"feast_bell":
			execute_tool_or_world_action("trigger_feast", {})
		"curator_desk":
			_interact_with_curator_desk()
		"museum_pedestal":
			_interact_with_pedestal(target)
		"building":
			var enter_room := str(target.get("enter_room_id", ""))
			if enter_room != "":
				warp_to_zone(enter_room, Vector2(-1, -1), false)
			else:
				willow_player.set("controls_locked", true)
				hud.call(
					"show_dialogue",
					str(target.get("title", "Enclave Landmark")),
					str(target.get("description", "")),
					[{"id": "bye", "label": "▶ Close [Z]"}],
					{},
					true,
					""
				)
		"landmark_sign":
			willow_player.set("controls_locked", true)
			hud.call(
				"show_dialogue",
				str(target.get("title", "Signpost")),
				str(target.get("description", "")),
				[{"id": "bye", "label": "▶ Close [Z]"}],
				{},
				true,
				""
			)


func _on_player_use_tool(tool_id: String, facing_point: Vector2) -> void:
	var near: Dictionary = zone_manager.call("find_nearest_interactable", facing_point, 60.0)
	if near.is_empty():
		near = zone_manager.call("find_nearest_interactable", willow_player.position, 60.0)

	if not near.is_empty():
		var ntype := str(near.get("type", ""))
		if ntype == "resource_node":
			var req_tool := str(near.get("required_tool", tool_id))
			state_bridge.call("select_tool_by_id", req_tool)
			willow_player.call("trigger_tool_pose", req_tool)
			execute_tool_or_world_action(str(near.get("action_type", "forage_dig")), {
				"specimen_id": str(near.get("specimen_id", "spec_geode_bismuth"))
			})
			return
		elif ntype == "diy_workbench":
			execute_tool_or_world_action("craft_diy", {"recipe_id": "diy_herbal_liniment"})
			return
		elif ntype == "npc" and tool_id == "gift_satchel":
			execute_tool_or_world_action("gift_citizen", {"target_id": str(near.get("id", "enclave_03_silas"))})
			return

	var tool_info: Dictionary = state_bridge.call("select_tool_by_id", tool_id)
	var act := str(tool_info.get("action_type", "forage_dig"))
	var payload: Dictionary = {}
	if act == "place_decor":
		payload["recipe_id"] = "diy_bismuth_lantern"
	elif act == "gift_citizen":
		payload["target_id"] = "enclave_03_silas"
	execute_tool_or_world_action(act, payload)


func _interact_with_npc(target: Dictionary) -> void:
	var cid := str(target.get("id", "enclave_03_silas"))
	var npc_ref: Node2D = target.get("npc_ref", null)
	if npc_ref != null:
		npc_ref.call("turn_toward", willow_player.position)

	var citizens_dict: Dictionary = state_bridge.get("citizens")
	var cdata: Dictionary = citizens_dict.get(cid, {})
	var cname := str(cdata.get("name", cid))
	var epithet := str(cdata.get("epithet", "Specialist"))
	var quote := str(cdata.get("quote", "Welcome to the Enclave Crater Valley!"))

	var tut_msg := str(tutorial_director.call("notify_event", "talk_npc"))
	var full_text := quote
	if tut_msg != "":
		full_text = "%s\n\n✨ %s" % [quote, tut_msg]

	willow_player.set("controls_locked", true)
	_play_sfx(procedural_audio.call("get_sfx_pickup"))
	hud.call("refresh_pills")

	var choices: Array[Dictionary] = [
		{"id": "gift_npc", "label": "🎁 Gift / Favor"},
		{"id": "donate_or_craft", "label": "🏛️ Donate / Craft"},
		{"id": "bye", "label": "👋 Bye [Z]"}
	]
	hud.call(
		"show_dialogue",
		"%s — %s [%s]" % [cname, epithet, str(cdata.get("mbti_type", ""))],
		full_text,
		choices,
		{"citizen_id": cid},
		false,
		cid
	)


func _interact_with_workbench() -> void:
	willow_player.set("controls_locked", true)
	hud.call(
		"show_dialogue",
		"⚗️ Copper Alembic DIY Workbench",
		"Synthesize alchemical gifts or cross-capsule SR-02 Tycoon workshop items:",
		[
			{"id": "craft_liniment", "label": "🧪 Herbal Liniment"},
			{"id": "craft_elixir", "label": "⚗️ Chelation Elixir"},
			{"id": "craft_sr02", "label": "⚒️ SR-02 Anvil"},
			{"id": "bye", "label": "👋 Close"}
		],
		{},
		true,
		""
	)


func _interact_with_curator_desk() -> void:
	var donated_arr: Array = state_bridge.get("donated_specimen_ids")
	willow_player.set("controls_locked", true)
	hud.call(
		"show_dialogue",
		"🏛️ Living Atlas Curator Desk (Dorian & Vex)",
		"Donated Specimens: %d / 16 across 4 SR-05 Epistemic Tiers (TIER_1..TIER_4). Would you like to donate a specimen?" % donated_arr.size(),
		[
			{"id": "donate_any", "label": "💎 Donate Specimen"},
			{"id": "bye", "label": "👋 Close"}
		],
		{},
		false,
		"enclave_15_dorian"
	)


func _interact_with_pedestal(target: Dictionary) -> void:
	var spec: Dictionary = target.get("specimen", {})
	var sid := str(target.get("specimen_id", "spec_geode_bismuth"))
	var donated_arr: Array = state_bridge.get("donated_specimen_ids")
	var is_donated := sid in donated_arr
	var status_tag := "✅ CATALOGED IN ATLAS" if is_donated else "⏳ UNDONATED — Press Donate!"
	var text := "[%s | %s]\n%s\n(%s)" % [
		str(spec.get("wing_label", "Museum")),
		str(spec.get("epistemic_tier", "TIER_2")),
		str(spec.get("lore", "")),
		status_tag
	]
	var choices: Array[Dictionary] = []
	if not is_donated:
		choices.append({"id": "donate_specific", "label": "💎 Donate Now"})
	choices.append({"id": "bye", "label": "▶ Close [Z]"})

	willow_player.set("controls_locked", true)
	hud.call(
		"show_dialogue",
		"%s %s" % [str(spec.get("icon", "💎")), str(spec.get("name", sid))],
		text,
		choices,
		{"specimen_id": sid},
		true,
		""
	)


func _on_hud_dialogue_choice(choice_id: String, context: Dictionary) -> void:
	match choice_id:
		"gift_npc":
			execute_tool_or_world_action("gift_citizen", {"target_id": str(context.get("citizen_id", "enclave_03_silas"))})
		"donate_or_craft":
			if str(context.get("citizen_id", "")) in ["enclave_14_vex", "enclave_15_dorian"]:
				execute_tool_or_world_action("donate_museum", {})
			else:
				execute_tool_or_world_action("craft_diy", {"recipe_id": "diy_herbal_liniment"})
		"craft_liniment":
			execute_tool_or_world_action("craft_diy", {"recipe_id": "diy_herbal_liniment"})
		"craft_elixir":
			execute_tool_or_world_action("craft_diy", {"recipe_id": "diy_chelation_elixir"})
		"craft_sr02":
			execute_tool_or_world_action("craft_diy", {"recipe_id": "theme_enclave_first_forge"})
		"donate_any":
			execute_tool_or_world_action("donate_museum", {})
		"donate_specific":
			execute_tool_or_world_action("donate_museum", {"specimen_id": str(context.get("specimen_id", ""))})


func execute_tool_or_world_action(action_type: String, payload: Dictionary = {}) -> Dictionary:
	var res: Dictionary = state_bridge.call("perform_action", action_type, payload)
	var tut_msg := str(tutorial_director.call("notify_event", action_type))
	var sfx: AudioStreamWAV = procedural_audio.call("get_sfx_secret") if tut_msg != "" else procedural_audio.call("get_sfx_pickup")
	_play_sfx(sfx)

	zone_manager.call("refresh_museum_pedestals")
	hud.call("refresh_pills")

	var body := str(res.get("detail", ""))
	if tut_msg != "":
		body = "%s\n\n✨ %s" % [body, tut_msg]

	willow_player.set("controls_locked", true)
	hud.call(
		"show_dialogue",
		str(res.get("headline", "Action Complete")),
		body,
		[{"id": "bye", "label": "▶ Continue [Z]"}],
		{},
		true,
		""
	)
	return res


func _play_sfx(stream: AudioStreamWAV) -> void:
	if state_bridge != null and bool(state_bridge.get("audio_muted")):
		return
	if DisplayServer.get_name() == "headless":
		return
	if sfx_player != null and stream != null:
		sfx_player.stop()
		sfx_player.stream = stream
		sfx_player.play()
