class_name EmeraldHUD
extends CanvasLayer
## Pokémon Emerald (Hoenn) Minimalist HUD, GBA Bottom Dialogue Box, PBR Willow Card,
## and Collapsible Right-Side START Menu. Leaves >95% of the 480x320 viewport unobstructed!

const EnclaveStateBridgeScript = preload("res://engine/enclave_state_bridge.gd")
const WillowStudioLoaderScript = preload("res://engine/willow_studio_loader.gd")
const ZoneManagerScript = preload("res://engine/zone_manager.gd")

signal dialogue_choice_selected(choice_id: String, context: Dictionary)
signal dialogue_closed()
signal fast_travel_requested(zone_id: String)
signal craft_recipe_requested(recipe_id: String)
signal donate_specimen_requested(specimen_id: String)
signal feast_requested()
signal advance_tick_requested()
signal theme_changed(theme_pack: String)

var state_bridge: RefCounted = null
var tutorial_director: RefCounted = null
var studio_loader: RefCounted = null
var sprite_factory: RefCounted = null
var pbr_shader: Shader = null
var pbr_material: ShaderMaterial = null

# HUD Nodes
var zone_banner_panel: PanelContainer = null
var zone_banner_title: Label = null
var zone_banner_sub: Label = null
var _banner_timer: float = 0.0

var tutorial_pill_panel: PanelContainer = null
var tutorial_pill_label: Label = null

var status_pill_panel: PanelContainer = null
var status_pill_label: Label = null

# GBA Bottom Dialogue Box
var dialogue_box: Panel = null
var portrait_rect: TextureRect = null
var speaker_label: Label = null
var dialogue_text_label: Label = null
var choice_box: VBoxContainer = null
var _dialogue_context: Dictionary = {}
var _full_dialogue_text: String = ""
var _visible_chars: float = 0.0

# Collapsible Right-Side Pokémon Emerald START Menu & Sub-Modal
var start_menu_panel: Panel = null
var sub_modal_panel: Panel = null
var sub_modal_title: Label = null
var sub_modal_body: Label = null
var sub_modal_actions: VBoxContainer = null
var willow_card_preview: TextureRect = null
var _willow_view_idx: int = 0

# 0.22s GBA Warp Fade Curtain
var fade_curtain: ColorRect = null


func setup(
	bridge: RefCounted,
	tut: RefCounted,
	loader: RefCounted,
	factory: RefCounted
) -> void:
	state_bridge = bridge
	tutorial_director = tut
	studio_loader = loader
	sprite_factory = factory

	pbr_shader = load("res://shaders/willow_2d_pbr.gdshader") as Shader
	if pbr_shader != null:
		pbr_material = ShaderMaterial.new()
		pbr_material.shader = pbr_shader
		if studio_loader != null and studio_loader.get("emissive_texture") != null:
			pbr_material.set_shader_parameter("emissive_texture", studio_loader.get("emissive_texture"))

	_build_hud_nodes()
	refresh_pills()


func _build_hud_nodes() -> void:
	# 1. Top-Center 1-Line Tutorial Objective Pill
	tutorial_pill_panel = PanelContainer.new()
	tutorial_pill_panel.name = "TutorialObjectivePill"
	tutorial_pill_panel.position = Vector2(72, 4)
	tutorial_pill_panel.custom_minimum_size = Vector2(336, 18)
	var pill_style := StyleBoxFlat.new()
	pill_style.bg_color = Color(0.06, 0.11, 0.09, 0.84)
	pill_style.border_color = Color("#ffd866")
	pill_style.set_border_width_all(1)
	pill_style.set_corner_radius_all(4)
	pill_style.content_margin_left = 6
	pill_style.content_margin_right = 6
	pill_style.content_margin_top = 2
	pill_style.content_margin_bottom = 2
	tutorial_pill_panel.add_theme_stylebox_override("panel", pill_style)

	tutorial_pill_label = Label.new()
	tutorial_pill_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	tutorial_pill_label.add_theme_font_size_override("font_size", 8)
	tutorial_pill_label.add_theme_color_override("font_color", Color("#fff2b8"))
	tutorial_pill_panel.add_child(tutorial_pill_label)
	add_child(tutorial_pill_panel)

	# 2. Top-Left Hoenn Route Banner (slides down on zone entry, then retracts)
	zone_banner_panel = PanelContainer.new()
	zone_banner_panel.name = "ZoneBannerBox"
	zone_banner_panel.position = Vector2(8, 26)
	zone_banner_panel.custom_minimum_size = Vector2(184, 34)
	var banner_style := StyleBoxFlat.new()
	banner_style.bg_color = Color(0.08, 0.18, 0.14, 0.92)
	banner_style.border_color = Color("#32f5c8")
	banner_style.set_border_width_all(2)
	banner_style.set_corner_radius_all(4)
	banner_style.content_margin_left = 8
	banner_style.content_margin_right = 8
	banner_style.content_margin_top = 3
	banner_style.content_margin_bottom = 3
	zone_banner_panel.add_theme_stylebox_override("panel", banner_style)

	var banner_vbox := VBoxContainer.new()
	banner_vbox.add_theme_constant_override("separation", 1)
	zone_banner_title = Label.new()
	zone_banner_title.add_theme_font_size_override("font_size", 10)
	zone_banner_title.add_theme_color_override("font_color", Color("#32f5c8"))
	zone_banner_sub = Label.new()
	zone_banner_sub.add_theme_font_size_override("font_size", 7)
	zone_banner_sub.add_theme_color_override("font_color", Color("#e0f2ea"))
	banner_vbox.add_child(zone_banner_title)
	banner_vbox.add_child(zone_banner_sub)
	zone_banner_panel.add_child(banner_vbox)
	add_child(zone_banner_panel)

	# 3. Bottom-Left Compact Tool & Rupee Pill
	status_pill_panel = PanelContainer.new()
	status_pill_panel.name = "StatusToolRupeePill"
	status_pill_panel.position = Vector2(6, 296)
	status_pill_panel.custom_minimum_size = Vector2(240, 18)
	var status_style := pill_style.duplicate() as StyleBoxFlat
	status_style.border_color = Color("#32f5c8")
	status_pill_panel.add_theme_stylebox_override("panel", status_style)

	status_pill_label = Label.new()
	status_pill_label.add_theme_font_size_override("font_size", 8)
	status_pill_label.add_theme_color_override("font_color", Color("#e8fbf4"))
	status_pill_panel.add_child(status_pill_label)
	add_child(status_pill_panel)

	# 4. Classic GBA Bottom Dialogue Box (hidden during exploration)
	dialogue_box = Panel.new()
	dialogue_box.name = "GBADialogueBox"
	dialogue_box.position = Vector2(8, 212)
	dialogue_box.size = Vector2(464, 100)
	dialogue_box.visible = false
	var dlg_style := StyleBoxFlat.new()
	dlg_style.bg_color = Color(0.06, 0.11, 0.10, 0.96)
	dlg_style.border_color = Color("#ffd866")
	dlg_style.set_border_width_all(2)
	dlg_style.set_corner_radius_all(6)
	dialogue_box.add_theme_stylebox_override("panel", dlg_style)

	portrait_rect = TextureRect.new()
	portrait_rect.name = "SpeakerPortrait"
	portrait_rect.position = Vector2(8, 12)
	portrait_rect.size = Vector2(64, 76)
	portrait_rect.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	portrait_rect.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	portrait_rect.flip_h = false # CM-02 invariant
	dialogue_box.add_child(portrait_rect)

	speaker_label = Label.new()
	speaker_label.position = Vector2(80, 8)
	speaker_label.size = Vector2(256, 16)
	speaker_label.add_theme_font_size_override("font_size", 10)
	speaker_label.add_theme_color_override("font_color", Color("#ffd866"))
	dialogue_box.add_child(speaker_label)

	dialogue_text_label = Label.new()
	dialogue_text_label.position = Vector2(80, 26)
	dialogue_text_label.size = Vector2(260, 66)
	dialogue_text_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	dialogue_text_label.add_theme_font_size_override("font_size", 9)
	dialogue_text_label.add_theme_color_override("font_color", Color("#f2f8f5"))
	dialogue_box.add_child(dialogue_text_label)

	choice_box = VBoxContainer.new()
	choice_box.position = Vector2(348, 8)
	choice_box.size = Vector2(108, 84)
	choice_box.add_theme_constant_override("separation", 3)
	dialogue_box.add_child(choice_box)
	add_child(dialogue_box)

	# 5. Collapsible Right-Side Pokémon Emerald START Menu + Sub-Modal
	start_menu_panel = Panel.new()
	start_menu_panel.name = "EmeraldStartMenu"
	start_menu_panel.position = Vector2(320, 26)
	start_menu_panel.size = Vector2(152, 232)
	start_menu_panel.visible = false
	start_menu_panel.add_theme_stylebox_override("panel", dlg_style)

	var menu_vbox := VBoxContainer.new()
	menu_vbox.position = Vector2(6, 6)
	menu_vbox.size = Vector2(140, 220)
	menu_vbox.add_theme_constant_override("separation", 3)
	start_menu_panel.add_child(menu_vbox)

	var menu_entries: Array[Dictionary] = [
		{"id": "dex", "label": "📖 ENCLAVE DEX (16)"},
		{"id": "bag", "label": "🎒 BAG & 6 TOOLS"},
		{"id": "diy_museum", "label": "🔨 DIY & MUSEUM (16)"},
		{"id": "map", "label": "🗺️ TOWN MAP (WARP)"},
		{"id": "willow_card", "label": "🪪 WILLOW CARD (PBR)"},
		{"id": "dispatch", "label": "📰 DISPATCH & FEAST"},
		{"id": "options", "label": "⚙️ OPTIONS (THEMES)"},
		{"id": "close", "label": "❌ CLOSE [ESC]"}
	]
	for item in menu_entries:
		var btn := Button.new()
		btn.text = str(item["label"])
		btn.add_theme_font_size_override("font_size", 8)
		btn.custom_minimum_size = Vector2(138, 23)
		var mid := str(item["id"])
		btn.pressed.connect(func() -> void: _on_start_menu_item_pressed(mid))
		menu_vbox.add_child(btn)
	add_child(start_menu_panel)

	sub_modal_panel = Panel.new()
	sub_modal_panel.name = "StartSubModal"
	sub_modal_panel.position = Vector2(12, 26)
	sub_modal_panel.size = Vector2(300, 258)
	sub_modal_panel.visible = false
	sub_modal_panel.add_theme_stylebox_override("panel", dlg_style)

	sub_modal_title = Label.new()
	sub_modal_title.position = Vector2(10, 8)
	sub_modal_title.size = Vector2(280, 16)
	sub_modal_title.add_theme_font_size_override("font_size", 10)
	sub_modal_title.add_theme_color_override("font_color", Color("#32f5c8"))
	sub_modal_panel.add_child(sub_modal_title)

	sub_modal_body = Label.new()
	sub_modal_body.position = Vector2(10, 26)
	sub_modal_body.size = Vector2(176, 220)
	sub_modal_body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	sub_modal_body.add_theme_font_size_override("font_size", 8)
	sub_modal_body.add_theme_color_override("font_color", Color("#f2f8f5"))
	sub_modal_panel.add_child(sub_modal_body)

	willow_card_preview = TextureRect.new()
	willow_card_preview.name = "WillowPBRTurnaroundPreview"
	willow_card_preview.position = Vector2(190, 26)
	willow_card_preview.size = Vector2(100, 140)
	willow_card_preview.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	willow_card_preview.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	willow_card_preview.flip_h = false # CM-02 invariant
	willow_card_preview.visible = false
	if pbr_material != null:
		willow_card_preview.material = pbr_material
	sub_modal_panel.add_child(willow_card_preview)

	sub_modal_actions = VBoxContainer.new()
	sub_modal_actions.position = Vector2(186, 170)
	sub_modal_actions.size = Vector2(106, 80)
	sub_modal_actions.add_theme_constant_override("separation", 3)
	sub_modal_panel.add_child(sub_modal_actions)
	add_child(sub_modal_panel)

	# 6. Fullscreen Fade Curtain for 0.22s GBA Door/Zone Warps
	fade_curtain = ColorRect.new()
	fade_curtain.name = "GBAWarpCurtain"
	fade_curtain.position = Vector2.ZERO
	fade_curtain.size = Vector2(480, 320)
	fade_curtain.color = Color(0, 0, 0, 0)
	fade_curtain.mouse_filter = Control.MOUSE_FILTER_IGNORE
	add_child(fade_curtain)


func show_zone_banner(title: String, subtitle: String) -> void:
	zone_banner_title.text = title
	zone_banner_sub.text = subtitle
	zone_banner_panel.visible = true
	zone_banner_panel.position = Vector2(8, 26)
	_banner_timer = 2.5


func refresh_pills() -> void:
	if tutorial_director != null and tutorial_pill_label != null:
		tutorial_pill_label.text = str(tutorial_director.call("get_objective_pill_text"))
	if state_bridge != null and status_pill_label != null:
		var tool_info: Dictionary = state_bridge.call("get_equipped_tool")
		status_pill_label.text = "[Q/1-6] %s | 💎 %d RUP | Sol %d %s | [Enter] START" % [
			str(tool_info.get("short_label", "⚗️ Trowel")),
			int(state_bridge.get("rupees")),
			int(state_bridge.get("colony_sol")),
			str(state_bridge.get("day_phase"))
		]


func show_dialogue(
	speaker: String,
	text: String,
	choices: Array = [],
	context: Dictionary = {},
	use_willow_pbr_portrait: bool = true,
	citizen_id: String = ""
) -> void:
	_dialogue_context = context.duplicate(true)
	speaker_label.text = speaker
	_full_dialogue_text = text
	var rm := bool(state_bridge.get("reduced_motion"))
	_visible_chars = float(text.length()) if rm else 0.0
	dialogue_text_label.text = text
	dialogue_text_label.visible_characters = -1 if rm else 0

	portrait_rect.flip_h = false
	if not use_willow_pbr_portrait and citizen_id != "" and sprite_factory != null:
		portrait_rect.material = null
		portrait_rect.texture = sprite_factory.call("get_citizen_portrait", citizen_id)
	elif studio_loader != null and bool(studio_loader.get("is_loaded")):
		portrait_rect.material = pbr_material
		portrait_rect.texture = studio_loader.call("get_view_atlas_texture", "01_front_0deg")
	elif sprite_factory != null:
		portrait_rect.material = null
		portrait_rect.texture = sprite_factory.call("get_citizen_portrait", "enclave_07_willow")

	for child in choice_box.get_children():
		choice_box.remove_child(child)
		child.free()

	var effective_choices := choices
	if effective_choices.is_empty():
		effective_choices = [{"id": "bye", "label": "▶ Continue [Z]"}]

	for idx in range(effective_choices.size()):
		var cdict: Dictionary = effective_choices[idx]
		var btn := Button.new()
		btn.text = str(cdict.get("label", "Continue"))
		btn.add_theme_font_size_override("font_size", 8)
		btn.custom_minimum_size = Vector2(104, 18)
		var cid := str(cdict.get("id", "bye"))
		btn.pressed.connect(func() -> void: _on_dialogue_choice_pressed(cid))
		choice_box.add_child(btn)
		if idx == 0:
			btn.call_deferred("grab_focus")

	dialogue_box.visible = true


func hide_dialogue() -> void:
	if dialogue_box.visible:
		dialogue_box.visible = false
		dialogue_closed.emit()


func toggle_start_menu() -> void:
	start_menu_panel.visible = not start_menu_panel.visible
	if not start_menu_panel.visible:
		sub_modal_panel.visible = false


func open_willow_card_modal() -> void:
	start_menu_panel.visible = true
	_on_start_menu_item_pressed("willow_card")


func _on_dialogue_choice_pressed(choice_id: String) -> void:
	var ctx := _dialogue_context.duplicate(true)
	if choice_id == "bye":
		hide_dialogue()
		return
	dialogue_choice_selected.emit(choice_id, ctx)


func _on_start_menu_item_pressed(menu_id: String) -> void:
	if menu_id == "close":
		start_menu_panel.visible = false
		sub_modal_panel.visible = false
		return

	sub_modal_panel.visible = true
	willow_card_preview.visible = false
	for child in sub_modal_actions.get_children():
		sub_modal_actions.remove_child(child)
		child.free()

	var citizens_dict: Dictionary = state_bridge.get("citizens")
	var inventory_dict: Dictionary = state_bridge.get("inventory")
	var donated_arr: Array = state_bridge.get("donated_specimen_ids")
	var story_arr: Array = state_bridge.get("story_feed")

	match menu_id:
		"dex":
			sub_modal_title.text = "📖 ENCLAVE DEX — 16 CANONICAL SPECIALISTS"
			var lines: PackedStringArray = []
			for cid in EnclaveStateBridgeScript.CANONICAL_16_IDS:
				var c: Dictionary = citizens_dict.get(cid, {})
				lines.append("• %s (%s) [%s/%s] Bond %.2f" % [
					str(c.get("name", cid)), str(c.get("squad", "")),
					str(c.get("mbti_type", "")), str(c.get("enneagram", "")),
					float(c.get("willow_bond", 0.8))
				])
			sub_modal_body.text = "\n".join(lines)
		"bag":
			var eq_tool: Dictionary = state_bridge.call("get_equipped_tool")
			sub_modal_title.text = "🎒 WILLOW'S ALCHEMIST BAG & 6 TOOLS"
			var inv_lines: PackedStringArray = ["Equipped Tool: %s\n\nInventory:" % str(eq_tool.get("name", ""))]
			for k in inventory_dict.keys():
				if int(inventory_dict[k]) > 0:
					inv_lines.append("• %s ×%d" % [k, int(inventory_dict[k])])
			sub_modal_body.text = "\n".join(inv_lines)
			for t_idx in range(EnclaveStateBridgeScript.TOOLS.size()):
				var tinfo: Dictionary = EnclaveStateBridgeScript.TOOLS[t_idx]
				var b := Button.new()
				b.text = str(tinfo["short_label"])
				b.add_theme_font_size_override("font_size", 7)
				var slot_i := t_idx
				b.pressed.connect(func() -> void:
					state_bridge.call("select_tool_slot", slot_i)
					refresh_pills()
					_on_start_menu_item_pressed("bag")
				)
				sub_modal_actions.add_child(b)
		"diy_museum":
			sub_modal_title.text = "🔨 DIY ALCHEMY (12) & LIVING ATLAS (%d/16)" % donated_arr.size()
			sub_modal_body.text = "Donated Specimens: %d / 16 (SR-05 TIER_1..TIER_4)\nHomestead Comfort: %d\n\nCraft SR-02 & Alchemy Recipes or Donate Specimens:" % [
				donated_arr.size(),
				int(state_bridge.get("homestead_comfort_score"))
			]
			var craft_lin := Button.new()
			craft_lin.text = "🧪 Craft Liniment"
			craft_lin.add_theme_font_size_override("font_size", 7)
			craft_lin.pressed.connect(func() -> void: craft_recipe_requested.emit("diy_herbal_liniment"))
			sub_modal_actions.add_child(craft_lin)

			var craft_sr02 := Button.new()
			craft_sr02.text = "⚒️ Craft SR-02 Anvil"
			craft_sr02.add_theme_font_size_override("font_size", 7)
			craft_sr02.pressed.connect(func() -> void: craft_recipe_requested.emit("theme_enclave_first_forge"))
			sub_modal_actions.add_child(craft_sr02)

			var donate_btn := Button.new()
			donate_btn.text = "🏛️ Donate Specimen"
			donate_btn.add_theme_font_size_override("font_size", 7)
			donate_btn.pressed.connect(func() -> void: donate_specimen_requested.emit(""))
			sub_modal_actions.add_child(donate_btn)
		"map":
			sub_modal_title.text = "🗺️ HOENN CRATER VALLEY TOWN MAP (FAST TRAVEL)"
			sub_modal_body.text = "Select any of the 5 Outdoor Zones or 3 Indoor Rooms to warp with a 0.22s GBA transition:"
			for zid in ZoneManagerScript.get_all_zone_ids():
				var zmeta: Dictionary = ZoneManagerScript.ZONE_CATALOG[zid]
				var zbtn := Button.new()
				zbtn.text = str(zmeta.get("title", zid))
				zbtn.add_theme_font_size_override("font_size", 7)
				var target_z := zid
				zbtn.pressed.connect(func() -> void:
					start_menu_panel.visible = false
					sub_modal_panel.visible = false
					fast_travel_requested.emit(target_z)
				)
				sub_modal_actions.add_child(zbtn)
		"willow_card":
			sub_modal_title.text = "🪪 WILLOW ALCHEMIST CARD — 5-VIEW PBR STUDIO"
			willow_card_preview.visible = true
			_refresh_willow_card_view()
			var rot_btn := Button.new()
			rot_btn.text = "⟳ Rotate View (5)"
			rot_btn.add_theme_font_size_override("font_size", 8)
			rot_btn.pressed.connect(func() -> void:
				_willow_view_idx = (_willow_view_idx + 1) % WillowStudioLoaderScript.VIEW_ORDER.size()
				_refresh_willow_card_view()
			)
			sub_modal_actions.add_child(rot_btn)
		"dispatch":
			sub_modal_title.text = "📰 SOL %d EVENING DISPATCH & FEAST" % int(state_bridge.get("colony_sol"))
			var feed_lines: PackedStringArray = []
			for idx in range(min(4, story_arr.size())):
				var f: Dictionary = story_arr[idx]
				feed_lines.append("• [Sol %d] %s: %s" % [int(f.get("sol", 1)), str(f.get("title", "")), str(f.get("summary", ""))])
			sub_modal_body.text = "\n\n".join(feed_lines)
			var feast_btn := Button.new()
			feast_btn.text = "🍲 Ring Feast Bell"
			feast_btn.add_theme_font_size_override("font_size", 8)
			feast_btn.pressed.connect(func() -> void: feast_requested.emit())
			sub_modal_actions.add_child(feast_btn)

			var tick_btn := Button.new()
			tick_btn.text = "⏳ Advance +6h Tick"
			tick_btn.add_theme_font_size_override("font_size", 8)
			tick_btn.pressed.connect(func() -> void: advance_tick_requested.emit())
			sub_modal_actions.add_child(tick_btn)
		"options":
			var cur_pack := str(state_bridge.get("theme_pack"))
			var cur_rm := bool(state_bridge.get("reduced_motion"))
			var cur_mute := bool(state_bridge.get("audio_muted"))
			sub_modal_title.text = "⚙️ LDS THEME PACKS & ZT-9 COMFORT OVERRIDES"
			sub_modal_body.text = "Active LDS Theme: %s\nReduced Motion (ZT-9): %s\nAudio Muted (ZT-9): %s\nTutorial Step: %d/6" % [
				cur_pack,
				"ON" if cur_rm else "OFF",
				"ON" if cur_mute else "OFF",
				min(6, int(tutorial_director.get("current_step")))
			]
			var theme_btn := Button.new()
			theme_btn.text = "🎨 Cycle LDS Theme"
			theme_btn.add_theme_font_size_override("font_size", 7)
			theme_btn.pressed.connect(func() -> void:
				var cur_idx := EnclaveStateBridgeScript.LDS_THEME_PACKS.find(str(state_bridge.get("theme_pack")))
				var next_pack := EnclaveStateBridgeScript.LDS_THEME_PACKS[(cur_idx + 1) % EnclaveStateBridgeScript.LDS_THEME_PACKS.size()]
				apply_lds_theme_pack(next_pack)
				_on_start_menu_item_pressed("options")
			)
			sub_modal_actions.add_child(theme_btn)

			var rm_btn := Button.new()
			rm_btn.text = "🧘 Reduced Motion"
			rm_btn.add_theme_font_size_override("font_size", 7)
			rm_btn.pressed.connect(func() -> void:
				state_bridge.set("reduced_motion", not bool(state_bridge.get("reduced_motion")))
				_on_start_menu_item_pressed("options")
			)
			sub_modal_actions.add_child(rm_btn)

			var skip_btn := Button.new()
			skip_btn.text = "⏭️ Skip/Reset Tut"
			skip_btn.add_theme_font_size_override("font_size", 7)
			skip_btn.pressed.connect(func() -> void:
				if bool(tutorial_director.get("is_completed")):
					tutorial_director.call("restart_tutorial")
				else:
					tutorial_director.call("skip_tutorial")
				refresh_pills()
				_on_start_menu_item_pressed("options")
			)
			sub_modal_actions.add_child(skip_btn)


func _refresh_willow_card_view() -> void:
	var vid := WillowStudioLoaderScript.VIEW_ORDER[_willow_view_idx]
	var vmeta: Dictionary = studio_loader.call("get_view_metadata", vid) if studio_loader != null else {}
	willow_card_preview.flip_h = false # CM-02 invariant
	if studio_loader != null and bool(studio_loader.get("is_loaded")):
		willow_card_preview.texture = studio_loader.call("get_view_atlas_texture", vid)
	var donated_arr: Array = state_bridge.get("donated_specimen_ids")
	sub_modal_body.text = (
		"Willow — The Alchemist (enclave_07_willow)\n"
		+ "PBR Studio View: %s\n" % vid
		+ "Angle: %d° | Facing: %s\n" % [int(vmeta.get("angleDeg", 0)), str(vmeta.get("viewerFacing", "front"))]
		+ "CM-02 Laterality: flip_h = %s\n" % str(vmeta.get("flip_h", false))
		+ "Rupees: %d RUP | Comfort: %d\n" % [int(state_bridge.get("rupees")), int(state_bridge.get("homestead_comfort_score"))]
		+ "Museum Donated: %d / 16" % donated_arr.size()
	)


func apply_lds_theme_pack(pack_id: String) -> void:
	if pack_id not in EnclaveStateBridgeScript.LDS_THEME_PACKS:
		pack_id = "evergreen-dark"
	state_bridge.set("theme_pack", pack_id)
	var bg := Color(0.06, 0.11, 0.10, 0.96)
	var border := Color("#ffd866")
	match pack_id:
		"evergreen-light":
			bg = Color(0.88, 0.94, 0.90, 0.96)
			border = Color("#1e6848")
		"high-contrast":
			bg = Color(0.02, 0.02, 0.02, 0.98)
			border = Color("#ffff00")
		"calm":
			bg = Color(0.10, 0.15, 0.18, 0.94)
			border = Color("#78c8c0")
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.set_border_width_all(2)
	style.set_corner_radius_all(6)
	dialogue_box.add_theme_stylebox_override("panel", style)
	start_menu_panel.add_theme_stylebox_override("panel", style)
	sub_modal_panel.add_theme_stylebox_override("panel", style)
	theme_changed.emit(pack_id)


func _process(delta: float) -> void:
	if _banner_timer > 0.0:
		_banner_timer -= delta
		if _banner_timer <= 0.4:
			var t := clampf(_banner_timer / 0.4, 0.0, 1.0)
			zone_banner_panel.position.y = lerpf(-48.0, 26.0, t)
		if _banner_timer <= 0.0:
			zone_banner_panel.visible = false

	if dialogue_box.visible and dialogue_text_label.visible_characters >= 0:
		_visible_chars += delta * 48.0
		if int(_visible_chars) >= _full_dialogue_text.length():
			dialogue_text_label.visible_characters = -1
		else:
			dialogue_text_label.visible_characters = int(_visible_chars)
