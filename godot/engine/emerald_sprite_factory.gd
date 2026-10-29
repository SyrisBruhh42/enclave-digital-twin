class_name EmeraldSpriteFactory
extends RefCounted
## Procedural Gen-3 Pokémon Emerald (Hoenn) Pixel Art Generator.
## Synthesizes crisp, multi-shaded, nearest-neighbor ImageTexture assets at startup
## so the overworld runs with zero external .import dependencies in both desktop and --headless modes.

const TILE_SIZE: int = 32
const CHAR_W: int = 32
const CHAR_H: int = 48

var _tile_cache: Dictionary = {}
var _bldg_cache: Dictionary = {}
var _willow_cache: Dictionary = {}
var _citizen_cache: Dictionary = {}
var _portrait_cache: Dictionary = {}
var _prop_cache: Dictionary = {}

const CITIZEN_STYLE: Dictionary = {
	"enclave_01_hector": {"shirt": "#d35400", "hair": "#5d4037", "squad": "#e67e22", "hat": "goggles", "skin": "#f0c8a0"},
	"enclave_02_jane": {"shirt": "#2980b9", "hair": "#2c3e50", "squad": "#e67e22", "hat": "visor", "skin": "#f4d0b8"},
	"enclave_03_silas": {"shirt": "#8c5220", "hair": "#bdc3c7", "squad": "#e67e22", "hat": "specs", "skin": "#e8b890"},
	"enclave_04_leo": {"shirt": "#c0392b", "hair": "#d5d8dc", "squad": "#e67e22", "hat": "apron", "skin": "#d8a078"},
	"enclave_05_kaio": {"shirt": "#27ae60", "hair": "#3e2723", "squad": "#2ecc71", "hat": "hood", "skin": "#d49c70"},
	"enclave_06_zara": {"shirt": "#16a085", "hair": "#4a235a", "squad": "#2ecc71", "hat": "antlers", "skin": "#c88c64"},
	"enclave_07_willow": {"shirt": "#1abc9c", "hair": "#b8523b", "squad": "#2ecc71", "hat": "circlet", "skin": "#f0c8a8"},
	"enclave_08_terra": {"shirt": "#2e8b57", "hair": "#d7ccc8", "squad": "#2ecc71", "hat": "sunhat", "skin": "#e0b088"},
	"enclave_09_orion": {"shirt": "#8e44ad", "hair": "#34495e", "squad": "#9b59b6", "hat": "beret", "skin": "#f0c8a8"},
	"enclave_10_isla": {"shirt": "#5b2c6f", "hair": "#1c2833", "squad": "#9b59b6", "hat": "calipers", "skin": "#f4d4b8"},
	"enclave_11_kenna": {"shirt": "#9b59b6", "hair": "#cfd8dc", "squad": "#9b59b6", "hat": "dove_band", "skin": "#f0c8a8"},
	"enclave_12_elias": {"shirt": "#6c3483", "hair": "#eaeded", "squad": "#9b59b6", "hat": "stole", "skin": "#e8bc98"},
	"enclave_13_ryn": {"shirt": "#e67e22", "hair": "#4e342e", "squad": "#f1c40f", "hat": "chef_toque", "skin": "#e8b488"},
	"enclave_14_vex": {"shirt": "#d4ac0d", "hair": "#212f3d", "squad": "#f1c40f", "hat": "monocle", "skin": "#f0c8a8"},
	"enclave_15_dorian": {"shirt": "#b7950b", "hair": "#d0d3d4", "squad": "#f1c40f", "hat": "plume", "skin": "#edd0b0"},
	"enclave_16_elara": {"shirt": "#f39c12", "hair": "#f2f4f4", "squad": "#f1c40f", "hat": "medic_band", "skin": "#f4d0b0"},
}


static func _fill_rect(img: Image, x: int, y: int, w: int, h: int, col: Color) -> void:
	var x0 := clampi(x, 0, img.get_width())
	var y0 := clampi(y, 0, img.get_height())
	var x1 := clampi(x + w, 0, img.get_width())
	var y1 := clampi(y + h, 0, img.get_height())
	if x1 > x0 and y1 > y0:
		img.fill_rect(Rect2i(x0, y0, x1 - x0, y1 - y0), col)


static func _set_px(img: Image, x: int, y: int, col: Color) -> void:
	if x >= 0 and x < img.get_width() and y >= 0 and y < img.get_height():
		img.set_pixel(x, y, col)


static func _draw_border(img: Image, x: int, y: int, w: int, h: int, col: Color, thickness: int = 1) -> void:
	_fill_rect(img, x, y, w, thickness, col)
	_fill_rect(img, x, y + h - thickness, w, thickness, col)
	_fill_rect(img, x, y, thickness, h, col)
	_fill_rect(img, x + w - thickness, y, thickness, h, col)


static func _draw_ellipse(img: Image, cx: int, cy: int, rx: int, ry: int, col: Color) -> void:
	if rx <= 0 or ry <= 0:
		return
	for dy in range(-ry, ry + 1):
		for dx in range(-rx, rx + 1):
			var norm := (float(dx * dx) / float(rx * rx)) + (float(dy * dy) / float(ry * ry))
			if norm <= 1.0:
				_set_px(img, cx + dx, cy + dy, col)


# =============================================================================
# 1. 32x32 HOENN TERRAIN TILES
# =============================================================================
func get_terrain_tile(tile_type: String, anim_frame: int = 0) -> ImageTexture:
	var frame_mod := posmod(anim_frame, 4)
	var key := "%s_%d" % [tile_type, frame_mod]
	if _tile_cache.has(key):
		return _tile_cache[key]

	var img := Image.create(TILE_SIZE, TILE_SIZE, false, Image.FORMAT_RGBA8)
	var c_grass_base := Color("#389848")
	var c_grass_light := Color("#54c464")
	var c_grass_dark := Color("#267034")

	match tile_type:
		"grass":
			img.fill(c_grass_base)
			for ty in range(0, 32, 8):
				for tx in range(0, 32, 8):
					var ox := (ty / 8) % 2 * 3
					_set_px(img, tx + ox + 2, ty + 3, c_grass_dark)
					_set_px(img, tx + ox + 3, ty + 4, c_grass_dark)
					_set_px(img, tx + ox + 4, ty + 3, c_grass_dark)
					_set_px(img, tx + ox + 2, ty + 2, c_grass_light)
					_set_px(img, tx + ox + 4, ty + 2, c_grass_light)
					_set_px(img, tx + ox + 3, ty + 1, c_grass_light)
		"tall_grass":
			img.fill(Color("#226834"))
			var sway := (frame_mod % 2)
			for row in range(4, 30, 6):
				for col_x in range(2, 30, 5):
					_fill_rect(img, col_x, row, 2, 5, Color("#184e26"))
					_fill_rect(img, col_x + sway, row - 2, 2, 3, Color("#34a854"))
					_set_px(img, col_x + sway, row - 3, Color("#68f8a8"))
		"water":
			img.fill(Color("#186090"))
			var shift := frame_mod * 2
			for wy in range(2, 30, 8):
				for wx in range(0, 32, 8):
					var rx := (wx + shift + (wy / 4)) % 30
					_fill_rect(img, rx, wy, 4, 2, Color("#2c94c4"))
					_fill_rect(img, rx + 1, wy, 2, 1, Color("#88f0ff"))
			_fill_rect(img, 0, 0, 32, 2, Color("#b8f8ff"))
		"sand_path":
			img.fill(Color("#dfc484"))
			_draw_border(img, 0, 0, 32, 32, Color("#bf9c58"), 1)
			for py in range(4, 28, 7):
				for px in range(4, 28, 9):
					_set_px(img, px, py, Color("#f4e0a8"))
					_set_px(img, px + 3, py + 2, Color("#b08848"))
		"cobble_plaza":
			img.fill(Color("#8c9aa8"))
			for cy in range(0, 32, 8):
				var offset := 4 if (cy / 8) % 2 == 1 else 0
				_fill_rect(img, 0, cy, 32, 1, Color("#505c68"))
				for cx in range(offset, 32, 8):
					_fill_rect(img, cx, cy, 1, 8, Color("#505c68"))
					_fill_rect(img, cx + 1, cy + 1, 6, 2, Color("#b4c2d0"))
			# Glowing cyan Main Bus circuit inlay along center
			_fill_rect(img, 15, 0, 2, 32, Color("#24b8a0"))
			_set_px(img, 15, 8 + frame_mod * 4, Color("#68fff0"))
		"cliff_ledge":
			img.fill( c_grass_base)
			# Classic GBA 1-way jumpable basalt ledge with south drop shadow
			_fill_rect(img, 0, 8, 32, 4, Color("#8c7868"))
			_fill_rect(img, 0, 12, 32, 12, Color("#584840"))
			for lx in range(2, 30, 6):
				_fill_rect(img, lx, 14, 3, 8, Color("#42342e"))
				_fill_rect(img, lx + 1, 9, 2, 2, Color("#b09c88"))
			_fill_rect(img, 0, 24, 32, 5, Color("#14181e"))
			_fill_rect(img, 0, 29, 32, 3, Color("#245830"))
		"flowers":
			img.fill(c_grass_base)
			var f_shift := 1 if frame_mod % 2 == 1 else 0
			var flower_Verify: Array[Vector2i] = [Vector2i(6, 7), Vector2i(20, 9), Vector2i(10, 21), Vector2i(24, 23)]
			for idx in flower_Verify.size():
				var fp := flower_Verify[idx]
				var petal_col := Color("#ff6878") if idx % 2 == 0 else Color("#48f0e8")
				_fill_rect(img, fp.x + f_shift - 2, fp.y - 1, 5, 3, petal_col)
				_fill_rect(img, fp.x + f_shift - 1, fp.y - 2, 3, 5, petal_col)
				_set_px(img, fp.x + f_shift, fp.y, Color("#ffd848"))
		"wheat_plot":
			img.fill(Color("#4e3422"))
			_draw_border(img, 0, 0, 32, 32, Color("#362214"), 1)
			for furrow_y in range(4, 28, 6):
				_fill_rect(img, 2, furrow_y, 28, 2, Color("#3a2416"))
				for wx in range(5, 27, 5):
					_fill_rect(img, wx, furrow_y - 3, 2, 4, Color("#e8b838"))
					_set_px(img, wx, furrow_y - 4, Color("#ffe878"))
					_set_px(img, wx + 1, furrow_y - 4, Color("#58f8d8"))
		"wood_floor":
			img.fill(Color("#b07844"))
			for wy in range(0, 32, 8):
				_fill_rect(img, 0, wy, 32, 1, Color("#784c24"))
				_fill_rect(img, 0, wy + 1, 32, 2, Color("#c89058"))
				var seam_x := ((wy / 8) * 11 + 7) % 28 + 2
				_fill_rect(img, seam_x, wy, 1, 8, Color("#784c24"))
		"museum_marble":
			img.fill(Color("#dce6f2"))
			_draw_border(img, 0, 0, 32, 32, Color("#a8bcd4"), 1)
			_draw_border(img, 2, 2, 28, 28, Color("#eef4fc"), 1)
			_fill_rect(img, 14, 14, 4, 4, Color("#3878c8"))
		"pier_planks":
			img.fill(Color("#185888"))
			for py in range(1, 31, 6):
				_fill_rect(img, 0, py, 32, 5, Color("#8c6238"))
				_fill_rect(img, 0, py, 32, 1, Color("#ab7e4e"))
				_set_px(img, 3, py + 2, Color("#ffd866"))
				_set_px(img, 28, py + 2, Color("#ffd866"))
		"door_mat":
			img.fill(Color("#8c5834"))
			_fill_rect(img, 2, 4, 28, 24, Color("#c83830"))
			_draw_border(img, 2, 4, 28, 24, Color("#ffd858"), 2)
			_fill_rect(img, 13, 12, 6, 8, Color("#ffd858"))
		"tree_border":
			img.fill(Color("#226834"))
			_draw_ellipse(img, 16, 27, 10, 4, Color(0, 0, 0, 0.35))
			_fill_rect(img, 12, 20, 8, 9, Color("#5c3a22"))
			_draw_ellipse(img, 16, 15, 14, 12, Color("#184c28"))
			_draw_ellipse(img, 16, 13, 12, 10, Color("#2c8440"))
			_draw_ellipse(img, 15, 10, 9, 7, Color("#54c464"))
		_:
			img.fill(c_grass_base)

	var tex := ImageTexture.create_from_image(img)
	_tile_cache[key] = tex
	return tex


# =============================================================================
# 2. 3/4 PERSPECTIVE PITCHED-ROOF HOENN BUILDINGS (128x96 to 160x128 px)
# =============================================================================
func get_building_texture(building_id: String) -> ImageTexture:
	if _bldg_cache.has(building_id):
		return _bldg_cache[building_id]

	var w := 144
	var h := 112
	var roof_main := Color("#26a678")
	var roof_dark := Color("#187452")
	var roof_trim := Color("#ffd866")
	var wall_main := Color("#f0e4cc")
	var wall_beam := Color("#6e473b")
	var door_col := Color("#5c3824")
	var has_double_door := false
	var accent_style := "homestead"

	match building_id:
		"bldg_willow_homestead":
			w = 144; h = 112
			roof_main = Color("#249e72"); roof_dark = Color("#16684a"); roof_trim = Color("#e6ac55")
			wall_main = Color("#f4ead5"); wall_beam = Color("#6e473b")
			accent_style = "homestead"
		"proj_08_hearth_metabolic_engine":
			w = 160; h = 128
			roof_main = Color("#d25228"); roof_dark = Color("#943216"); roof_trim = Color("#ffcf66")
			wall_main = Color("#f5e6d3"); wall_beam = Color("#7a4424")
			has_double_door = true
			accent_style = "hearth"
		"proj_07_living_atlas":
			w = 160; h = 128
			roof_main = Color("#2868b8"); roof_dark = Color("#1a4480"); roof_trim = Color("#ffd858")
			wall_main = Color("#eef2f8"); wall_beam = Color("#8fa4be")
			has_double_door = true
			accent_style = "museum"
		"proj_01_first_forge":
			w = 144; h = 112
			roof_main = Color("#c86428"); roof_dark = Color("#883c14"); roof_trim = Color("#e6ac55")
			wall_main = Color("#584842"); wall_beam = Color("#342824")
			accent_style = "forge"
		"proj_02_stormbreaker":
			w = 128; h = 128
			roof_main = Color("#2c98c8"); roof_dark = Color("#1c6488"); roof_trim = Color("#32f5c8")
			wall_main = Color("#546878"); wall_beam = Color("#344450")
			accent_style = "spire"
		"bldg_curio_pavilion":
			w = 128; h = 96
			roof_main = Color("#8e44ad"); roof_dark = Color("#5b2c6f"); roof_trim = Color("#ffd866")
			wall_main = Color("#f2e8f8"); wall_beam = Color("#64486e")
			accent_style = "mart"
		"bldg_sibling_post":
			w = 96; h = 80
			roof_main = Color("#cd853f"); roof_dark = Color("#8b5a2b"); roof_trim = Color("#32f5c8")
			wall_main = Color("#e8d8c0"); wall_beam = Color("#5c4430")
			accent_style = "post"
		"proj_05_simulacrum":
			w = 144; h = 112
			roof_main = Color("#6a5acd"); roof_dark = Color("#44388c"); roof_trim = Color("#32f5c8")
			wall_main = Color("#4c5270"); wall_beam = Color("#2e3248")
			accent_style = "simulacrum"
		"proj_06_lyceum_of_the_mind":
			w = 128; h = 104
			roof_main = Color("#8a6bbd"); roof_dark = Color("#5c4484"); roof_trim = Color("#f4ead5")
			wall_main = Color("#e8e2f4"); wall_beam = Color("#5d5370")
			accent_style = "lyceum"
		"proj_03_sanctuary", "proj_04_genesis_garden":
			w = 144; h = 104
			roof_main = Color("#38a868"); roof_dark = Color("#226e42"); roof_trim = Color("#e6ac55")
			wall_main = Color("#e2f0e6"); wall_beam = Color("#486844")
			accent_style = "greenhouse"
		_:
			w = 112; h = 88
			roof_main = Color("#b86834"); roof_dark = Color("#7c421e"); roof_trim = Color("#e6ac55")
			wall_main = Color("#eadbc4"); wall_beam = Color("#684c38")
			accent_style = "cottage"

	var img := Image.create(w, h, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var outline := Color("#141820")

	# Ground drop shadow
	_fill_rect(img, 6, h - 8, w - 12, 8, Color(0, 0, 0, 0.35))

	var roof_h := int(h * 0.52)
	var wall_y := roof_h - 6
	var wall_h := h - wall_y - 4

	# Front & side 3/4 walls
	_fill_rect(img, 8, wall_y, w - 16, wall_h, wall_main)
	_draw_border(img, 8, wall_y, w - 16, wall_h, outline, 2)
	# Timber / stone pilasters
	_fill_rect(img, 10, wall_y, 6, wall_h, wall_beam)
	_fill_rect(img, w - 16, wall_y, 6, wall_h, wall_beam)
	_fill_rect(img, 8, wall_y + wall_h - 6, w - 16, 4, wall_beam)

	# Pitched shingled roof with stepped 3/4 gable
	for ry in range(8, roof_h):
		var t := float(ry - 8) / float(max(1, roof_h - 8))
		var inset := int((1.0 - t) * 20.0)
		var rx := 4 + inset
		var rw := w - 8 - inset * 2
		var rcol := roof_main if (ry / 4) % 2 == 0 else roof_dark
		_fill_rect(img, rx, ry, rw, 1, rcol)
		_set_px(img, rx, ry, outline)
		_set_px(img, rx + rw - 1, ry, outline)
		if ry % 5 == 0:
			for sx in range(rx + 4, rx + rw - 4, 8):
				_set_px(img, sx, ry, roof_dark.darkened(0.2))

	# Roof ridge beam & eaves trim
	_fill_rect(img, 24, 6, w - 48, 4, roof_trim)
	_draw_border(img, 24, 6, w - 48, 4, outline, 1)
	_fill_rect(img, 4, roof_h - 4, w - 8, 5, roof_trim)
	_draw_border(img, 4, roof_h - 4, w - 8, 5, outline, 1)

	# Doorway at bottom center (32px wide for double door, 24px for single)
	var door_w := 32 if has_double_door else 24
	var door_h := 28
	var door_x := (w - door_w) / 2
	var door_y := h - door_h - 4
	_fill_rect(img, door_x - 2, door_y - 2, door_w + 4, door_h + 2, roof_trim)
	_fill_rect(img, door_x, door_y, door_w, door_h, door_col)
	_draw_border(img, door_x, door_y, door_w, door_h, outline, 1)
	if has_double_door:
		_fill_rect(img, w / 2 - 1, door_y, 2, door_h, outline)
		_fill_rect(img, door_x + 3, door_y + 4, door_w / 2 - 6, 12, Color("#88e8ff"))
		_fill_rect(img, w / 2 + 3, door_y + 4, door_w / 2 - 6, 12, Color("#88e8ff"))
	else:
		_fill_rect(img, door_x + 4, door_y + 4, door_w - 8, 10, Color("#ffe888"))
		_fill_rect(img, door_x + door_w - 5, door_y + 15, 2, 3, Color("#ffd866"))

	# Glowing framed windows on left and right of doorway
	var win_y := wall_y + 10
	for wx in [22, w - 42]:
		if wx + 18 < door_x - 4 or wx > door_x + door_w + 4:
			_fill_rect(img, wx - 2, win_y - 2, 20, 18, wall_beam)
			_fill_rect(img, wx, win_y, 16, 14, Color("#ffe680"))
			_fill_rect(img, wx + 2, win_y + 2, 5, 5, Color("#ffffff"))
			_fill_rect(img, wx + 7, win_y, 2, 14, wall_beam)
			_fill_rect(img, wx, win_y + 6, 16, 2, wall_beam)

	# Building-specific architectural details
	if accent_style == "homestead":
		# Stained-glass attic window + outdoor copper alembic still on right
		_draw_ellipse(img, w / 2, roof_h - 16, 10, 10, outline)
		_draw_ellipse(img, w / 2, roof_h - 16, 8, 8, Color("#32f5c8"))
		_draw_ellipse(img, w / 2, roof_h - 16, 4, 4, Color("#ffd866"))
		_fill_rect(img, w - 22, h - 28, 12, 20, Color("#d47a38"))
		_draw_border(img, w - 22, h - 28, 12, 20, outline, 1)
		_fill_rect(img, w - 18, h - 34, 4, 6, Color("#32f5c8"))
	elif accent_style == "hearth":
		# Twin chimneys + warm hearth emblem
		_fill_rect(img, 28, 0, 12, 14, Color("#7a4424"))
		_fill_rect(img, w - 40, 0, 12, 14, Color("#7a4424"))
		_draw_ellipse(img, w / 2, roof_h - 16, 11, 9, Color("#ffcf66"))
		_draw_ellipse(img, w / 2, roof_h - 16, 7, 6, Color("#ff5828"))
	elif accent_style == "museum":
		# White marble pilasters + gold astrolabe pediment
		for px in [16, 36, w - 44, w - 24]:
			_fill_rect(img, px, wall_y + 2, 6, wall_h - 6, Color("#ffffff"))
		_draw_ellipse(img, w / 2, roof_h - 16, 12, 12, Color("#ffd858"))
		_draw_ellipse(img, w / 2, roof_h - 16, 8, 8, Color("#1a4480"))
		_draw_ellipse(img, w / 2, roof_h - 16, 4, 4, Color("#32f5c8"))
	elif accent_style == "spire":
		# Lightning harvester rod at top center
		_fill_rect(img, w / 2 - 3, 0, 6, 18, Color("#e6ac55"))
		_draw_ellipse(img, w / 2, 4, 6, 6, Color("#32f5c8"))

	var tex := ImageTexture.create_from_image(img)
	_bldg_cache[building_id] = tex
	return tex


# =============================================================================
# 3. CENTERED PLAYABLE WILLOW OVERWORLD SPRITE (32x48 px per frame)
#    Enforces CM-02 anatomical laterality (flip_h = false on LEFT) and hides
#    the glowing #00FF66 emerald eyes on UP dorsal frames!
# =============================================================================
func get_willow_frame(
	direction: String = "DOWN",
	walk_frame: int = 0,
	tool_id: String = "",
	using_tool: bool = false
) -> ImageTexture:
	var dir_norm := direction.to_upper()
	if dir_norm not in ["DOWN", "UP", "LEFT", "RIGHT"]:
		dir_norm = "DOWN"
	var wf := posmod(walk_frame, 4)
	var key := "willow_%s_%d_%s_%d" % [dir_norm, wf, tool_id if using_tool else "", 1 if using_tool else 0]
	if _willow_cache.has(key):
		return _willow_cache[key]

	var img := _render_willow_frame_image(dir_norm, wf, tool_id, using_tool)
	var tex := ImageTexture.create_from_image(img)
	_willow_cache[key] = tex
	return tex


func get_willow_spritesheet() -> ImageTexture:
	var key := "willow_full_sheet"
	if _willow_cache.has(key):
		return _willow_cache[key]
	var dirs: Array[String] = ["DOWN", "UP", "LEFT", "RIGHT"]
	var sheet := Image.create(CHAR_W * 4, CHAR_H * 4, false, Image.FORMAT_RGBA8)
	sheet.fill(Color(0, 0, 0, 0))
	for row in range(dirs.size()):
		for col in range(4):
			var frame_img := _render_willow_frame_image(dirs[row], col, "", false)
			sheet.blit_rect(frame_img, Rect2i(0, 0, CHAR_W, CHAR_H), Vector2i(col * CHAR_W, row * CHAR_H))
	var tex := ImageTexture.create_from_image(sheet)
	_willow_cache[key] = tex
	return tex


func _render_willow_frame_image(
	dir_norm: String,
	wf: int,
	tool_id: String,
	using_tool: bool
) -> Image:
	var img := Image.create(CHAR_W, CHAR_H, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))

	var bob := -1 if (wf == 1 or wf == 3) else 0
	var left_leg_dy := -2 if wf == 1 else (1 if wf == 3 else 0)
	var right_leg_dy := -2 if wf == 3 else (1 if wf == 1 else 0)

	var c_outline := Color("#12161f")
	var c_hair_dark := Color("#6e2c1e")
	var c_hair_mid := Color("#a84630")
	var c_hair_hi := Color("#d87252")
	var c_bronze := Color("#e6ac55")
	var c_gold := Color("#ffd866")
	var c_coat_main := Color("#1abc9c")
	var c_coat_dark := Color("#117a65")
	var c_visor := Color("#18222c")
	var c_eye_glow := Color("#00ff66")
	var c_boot := Color("#4a3228")

	# 1. Elliptical ground shadow
	_draw_ellipse(img, 16, 44, 9, 3, Color(0, 0, 0, 0.38))

	# 2. Boots / Legs (y = 36..44)
	_fill_rect(img, 11, 37 + left_leg_dy, 4, 6, c_boot)
	_draw_border(img, 11, 37 + left_leg_dy, 4, 6, c_outline, 1)
	_fill_rect(img, 17, 37 + right_leg_dy, 4, 6, c_boot)
	_draw_border(img, 17, 37 + right_leg_dy, 4, 6, c_outline, 1)

	# 3. Teal-Bronze Alchemist Pleated Coat & Skirt (y = 23..38)
	_fill_rect(img, 9, 24 + bob, 14, 14, c_coat_main)
	_fill_rect(img, 9, 33 + bob, 14, 5, c_coat_dark)
	_draw_border(img, 9, 24 + bob, 14, 14, c_outline, 1)
	# Brushed-bronze alchemist belt & buckle
	_fill_rect(img, 9, 30 + bob, 14, 2, c_bronze)
	_fill_rect(img, 15, 29 + bob, 3, 3, c_gold)

	# 4. Arms & CM-02 Anatomical Laterality (Right wrist copper prop socket is never flipped!)
	var arm_swing := 1 if wf == 1 else (-1 if wf == 3 else 0)
	if dir_norm == "LEFT":
		# Facing LEFT: viewer sees her left arm in front; her right arm is behind
		_fill_rect(img, 12, 25 + bob + arm_swing, 5, 8, c_coat_dark)
		_fill_rect(img, 13, 31 + bob + arm_swing, 3, 2, Color("#f0c8a8"))
	elif dir_norm == "RIGHT":
		# Facing RIGHT: viewer sees her anatomical right arm + bronze wrist socket in front
		_fill_rect(img, 15, 25 + bob - arm_swing, 5, 8, c_coat_dark)
		_fill_rect(img, 15, 30 + bob - arm_swing, 4, 2, c_bronze) # WristPropSocket.R
		_fill_rect(img, 16, 32 + bob - arm_swing, 3, 2, Color("#f0c8a8"))
	else:
		# Left arm (viewer right on DOWN, viewer left on UP)
		_fill_rect(img, 6, 25 + bob + arm_swing, 3, 8, c_coat_dark)
		_fill_rect(img, 23, 25 + bob - arm_swing, 3, 8, c_coat_dark)
		# Anatomical right wrist socket (viewer left = x 6..8 when facing DOWN, viewer right = x 23..25 when facing UP)
		var r_wrist_x := 6 if dir_norm == "DOWN" else 23
		_fill_rect(img, r_wrist_x, 30 + bob, 3, 2, c_bronze)

	# 5. Head, Flowing Copper-Auburn Hair, Horned Bronze Circlet & Eyes (y = 6..24)
	_draw_ellipse(img, 16, 15 + bob, 9, 8, c_outline)
	_draw_ellipse(img, 16, 15 + bob, 8, 7, c_hair_mid)
	_fill_rect(img, 10, 9 + bob, 12, 4, c_hair_hi)

	# Horned brushed-bronze circlet (visible in all 4 directions)
	_fill_rect(img, 9, 10 + bob, 14, 2, c_bronze)
	_fill_rect(img, 9, 6 + bob, 2, 4, c_gold)
	_fill_rect(img, 21, 6 + bob, 2, 4, c_gold)
	_set_px(img, 16, 10 + bob, Color("#32f5c8"))

	if dir_norm == "UP":
		# Dorsal view: flowing copper-auburn hair covers the back of head & shoulders; ZERO eyes visible!
		_fill_rect(img, 9, 12 + bob, 14, 14, c_hair_mid)
		_fill_rect(img, 10, 14 + bob, 3, 12, c_hair_dark)
		_fill_rect(img, 15, 14 + bob, 3, 12, c_hair_dark)
		_fill_rect(img, 19, 14 + bob, 3, 12, c_hair_dark)
		_fill_rect(img, 11, 12 + bob, 10, 3, c_hair_hi)
	elif dir_norm == "DOWN":
		# Side hair locks + dark visor + glowing #00FF66 emerald eyes
		_fill_rect(img, 8, 13 + bob, 3, 12, c_hair_dark)
		_fill_rect(img, 21, 13 + bob, 3, 12, c_hair_dark)
		_fill_rect(img, 11, 14 + bob, 10, 7, c_visor)
		_fill_rect(img, 12, 16 + bob, 3, 3, c_eye_glow)
		_fill_rect(img, 17, 16 + bob, 3, 3, c_eye_glow)
		_set_px(img, 13, 16 + bob, Color("#b8ffda"))
		_set_px(img, 18, 16 + bob, Color("#b8ffda"))
	elif dir_norm == "LEFT":
		# Dedicated Left profile (CM-02): hair swept right, visor & single glowing eye on left
		_fill_rect(img, 15, 12 + bob, 8, 13, c_hair_dark)
		_fill_rect(img, 10, 14 + bob, 6, 7, c_visor)
		_fill_rect(img, 11, 16 + bob, 3, 3, c_eye_glow)
	elif dir_norm == "RIGHT":
		# Right profile: hair swept left, visor & single glowing eye on right
		_fill_rect(img, 9, 12 + bob, 8, 13, c_hair_dark)
		_fill_rect(img, 16, 14 + bob, 6, 7, c_visor)
		_fill_rect(img, 18, 16 + bob, 3, 3, c_eye_glow)

	# 6. Tool Action Pose Overlay when using_tool == true
	if using_tool:
		var tool_col := Color("#e6ac55")
		var tip_col := Color("#32f5c8")
		match tool_id:
			"trowel":
				tool_col = Color("#d47a38"); tip_col = Color("#32f5c8")
			"bug_net":
				tool_col = Color("#8c6238"); tip_col = Color("#78f5d4")
			"dip_rod":
				tool_col = Color("#d4ac0d"); tip_col = Color("#70e4ff")
			"watering_can":
				tool_col = Color("#32a8d4"); tip_col = Color("#a8f8ff")
			"tinker_wrench":
				tool_col = Color("#94a8b8"); tip_col = Color("#ffd866")
			"gift_satchel":
				tool_col = Color("#e74c3c"); tip_col = Color("#ffd866")
		_fill_rect(img, 22, 20, 8, 4, tool_col)
		_fill_rect(img, 26, 16, 5, 6, tip_col)
		_draw_border(img, 26, 16, 5, 6, c_outline, 1)

	return img


static func verify_willow_up_frame_hides_eyes(up_img: Image) -> bool:
	var glow := Color("#00ff66")
	for y in range(up_img.get_height()):
		for x in range(up_img.get_width()):
			var px := up_img.get_pixel(x, y)
			if px.a > 0.5 and absf(px.r - glow.r) < 0.05 and absf(px.g - glow.g) < 0.05 and absf(px.b - glow.b) < 0.05:
				return false
	return true


# =============================================================================
# 4. 15 ENCLAVE CITIZEN 32x48 OVERWORLD SPRITES & 64x64 DIALOGUE PORTRAITS
# =============================================================================
func get_citizen_frame(character_id: String, direction: String = "DOWN", idle_frame: int = 0) -> ImageTexture:
	var key := "%s_%s_%d" % [character_id, direction.to_upper(), posmod(idle_frame, 2)]
	if _citizen_cache.has(key):
		return _citizen_cache[key]

	var style: Dictionary = CITIZEN_STYLE.get(character_id, CITIZEN_STYLE["enclave_03_silas"])
	var c_shirt := Color(str(style.get("shirt", "#8c5220")))
	var c_hair := Color(str(style.get("hair", "#bdc3c7")))
	var c_squad := Color(str(style.get("squad", "#e67e22")))
	var c_skin := Color(str(style.get("skin", "#e8b890")))
	var hat_type := str(style.get("hat", "specs"))
	var outline := Color("#141820")
	var bob := -1 if posmod(idle_frame, 2) == 1 else 0

	var img := Image.create(CHAR_W, CHAR_H, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))

	# Shadow & boots
	_draw_ellipse(img, 16, 44, 9, 3, Color(0, 0, 0, 0.35))
	_fill_rect(img, 11, 37, 4, 6, Color("#3a2820"))
	_fill_rect(img, 17, 37, 4, 6, Color("#3a2820"))

	# Torso & squad trim
	_fill_rect(img, 9, 24 + bob, 14, 14, c_shirt)
	_fill_rect(img, 9, 35 + bob, 14, 3, c_squad)
	_draw_border(img, 9, 24 + bob, 14, 14, outline, 1)
	_fill_rect(img, 7, 25 + bob, 3, 9, c_shirt.darkened(0.18))
	_fill_rect(img, 22, 25 + bob, 3, 9, c_shirt.darkened(0.18))

	# Head & Hair
	_draw_ellipse(img, 16, 15 + bob, 8, 8, outline)
	_draw_ellipse(img, 16, 16 + bob, 7, 6, c_skin)
	_fill_rect(img, 9, 8 + bob, 14, 6, c_hair)
	_fill_rect(img, 8, 11 + bob, 3, 7, c_hair)
	_fill_rect(img, 21, 11 + bob, 3, 7, c_hair)

	if direction.to_upper() != "UP":
		_fill_rect(img, 12, 16 + bob, 2, 3, outline)
		_fill_rect(img, 18, 16 + bob, 2, 3, outline)
		_set_px(img, 12, 16 + bob, Color("#ffffff"))
		_set_px(img, 18, 16 + bob, Color("#ffffff"))
	else:
		_fill_rect(img, 9, 10 + bob, 14, 12, c_hair)

	# Distinct headgear / accessory per citizen
	match hat_type:
		"goggles":
			_fill_rect(img, 10, 10 + bob, 12, 3, Color("#32f5c8"))
		"visor":
			_fill_rect(img, 10, 13 + bob, 12, 3, Color("#70e4ff"))
		"specs":
			_draw_border(img, 11, 15 + bob, 4, 4, Color("#ffd866"), 1)
			_draw_border(img, 17, 15 + bob, 4, 4, Color("#ffd866"), 1)
		"chef_toque":
			_fill_rect(img, 10, 3 + bob, 12, 6, Color("#ffffff"))
			_draw_border(img, 10, 3 + bob, 12, 6, outline, 1)
		"sunhat":
			_fill_rect(img, 6, 8 + bob, 20, 3, Color("#dfc484"))
		"antlers":
			_fill_rect(img, 8, 4 + bob, 2, 5, Color("#d4ac0d"))
			_fill_rect(img, 22, 4 + bob, 2, 5, Color("#d4ac0d"))
		"plume":
			_fill_rect(img, 19, 3 + bob, 4, 6, Color("#32f5c8"))
		"medic_band":
			_fill_rect(img, 10, 9 + bob, 12, 3, Color("#ffffff"))
			_fill_rect(img, 15, 9 + bob, 2, 3, Color("#e74c3c"))
		_:
			_fill_rect(img, 10, 9 + bob, 12, 2, c_squad)

	var tex := ImageTexture.create_from_image(img)
	_citizen_cache[key] = tex
	return tex


func get_citizen_portrait(character_id: String) -> ImageTexture:
	if _portrait_cache.has(character_id):
		return _portrait_cache[character_id]

	var style: Dictionary = CITIZEN_STYLE.get(character_id, CITIZEN_STYLE["enclave_03_silas"])
	var c_shirt := Color(str(style.get("shirt", "#8c5220")))
	var c_hair := Color(str(style.get("hair", "#bdc3c7")))
	var c_squad := Color(str(style.get("squad", "#e67e22")))
	var c_skin := Color(str(style.get("skin", "#e8b890")))
	var outline := Color("#141820")

	var img := Image.create(64, 64, false, Image.FORMAT_RGBA8)
	img.fill(Color("#122420"))
	_draw_border(img, 0, 0, 64, 64, c_squad, 3)
	_fill_rect(img, 14, 42, 36, 19, c_shirt)
	_draw_border(img, 14, 42, 36, 19, outline, 2)
	_draw_ellipse(img, 32, 28, 14, 14, outline)
	_draw_ellipse(img, 32, 29, 12, 12, c_skin)
	_fill_rect(img, 18, 12, 28, 10, c_hair)
	_fill_rect(img, 24, 27, 4, 5, outline)
	_fill_rect(img, 36, 27, 4, 5, outline)
	_set_px(img, 25, 28, Color("#ffffff"))
	_set_px(img, 37, 28, Color("#ffffff"))
	_fill_rect(img, 28, 36, 8, 2, Color("#8c4838"))

	var tex := ImageTexture.create_from_image(img)
	_portrait_cache[character_id] = tex
	return tex


# =============================================================================
# 5. INTERACTIVE PROPS, RESOURCE NODES, & TUTORIAL ARROW
# =============================================================================
func get_prop_texture(prop_type: String, anim_frame: int = 0) -> ImageTexture:
	var fm := posmod(anim_frame, 4)
	var key := "%s_%d" % [prop_type, fm]
	if _prop_cache.has(key):
		return _prop_cache[key]

	var img := Image.create(32, 32, false, Image.FORMAT_RGBA8)
	img.fill(Color(0, 0, 0, 0))
	var outline := Color("#141820")

	match prop_type:
		"geode_crack":
			_draw_ellipse(img, 16, 18, 11, 7, Color("#3a2e2a"))
			_fill_rect(img, 10, 12, 5, 9, Color("#32f5c8"))
			_fill_rect(img, 16, 9, 6, 12, Color("#b066ff"))
			_fill_rect(img, 21, 14, 4, 7, Color("#ffd866"))
			_draw_border(img, 16, 9, 6, 12, outline, 1)
		"critter_swarm":
			var dy := -2 if fm % 2 == 1 else 1
			_draw_ellipse(img, 16, 26, 6, 2, Color(0, 0, 0, 0.28))
			_fill_rect(img, 9, 11 + dy, 6, 8, Color("#58f8e8"))
			_fill_rect(img, 17, 11 + dy, 6, 8, Color("#ff78d8"))
			_fill_rect(img, 15, 10 + dy, 2, 10, Color("#ffd866"))
		"ferro_fish_shadow":
			var dx := 1 if fm % 2 == 1 else -1
			_draw_ellipse(img, 16 + dx, 16, 9, 5, Color("#0c2840"))
			_fill_rect(img, 24 + dx, 13, 4, 6, Color("#0c2840"))
			_draw_border(img, 6 + dx, 10, 20, 12, Color("#70e4ff"), 1)
		"alembic_workbench":
			_fill_rect(img, 2, 12, 28, 16, Color("#6e473b"))
			_draw_border(img, 2, 12, 28, 16, outline, 1)
			_fill_rect(img, 8, 5, 7, 9, Color("#d47a38"))
			_fill_rect(img, 18, 6, 6, 8, Color("#32f5c8"))
		"wardrobe_mirror":
			_fill_rect(img, 7, 2, 18, 28, Color("#d4ac0d"))
			_draw_border(img, 7, 2, 18, 28, outline, 1)
			_fill_rect(img, 10, 5, 12, 22, Color("#9be0ff"))
			_fill_rect(img, 12, 7, 3, 16, Color("#ffffff"))
		"alchemist_bed":
			_fill_rect(img, 4, 4, 24, 26, Color("#5c3824"))
			_fill_rect(img, 6, 6, 20, 7, Color("#f4ead5"))
			_fill_rect(img, 6, 13, 20, 15, Color("#249e72"))
			_draw_border(img, 4, 4, 24, 26, outline, 1)
		"feast_banquet_table":
			_fill_rect(img, 1, 6, 30, 20, Color("#8c5220"))
			_draw_border(img, 1, 6, 30, 20, outline, 1)
			_fill_rect(img, 6, 10, 6, 5, Color("#ffd866"))
			_fill_rect(img, 16, 10, 8, 6, Color("#32f5c8"))
		"feast_bell":
			_fill_rect(img, 8, 4, 16, 24, Color("#5c3824"))
			_draw_ellipse(img, 16, 14, 7, 7, Color("#ffd858"))
			_draw_border(img, 8, 4, 16, 24, outline, 1)
		"curator_desk":
			_fill_rect(img, 2, 10, 28, 16, Color("#5c3824"))
			_fill_rect(img, 6, 12, 20, 4, Color("#ffd858"))
			_draw_border(img, 2, 10, 28, 16, outline, 1)
		"museum_pedestal_donated":
			_fill_rect(img, 6, 12, 20, 18, Color("#dce6f2"))
			_draw_border(img, 6, 12, 20, 18, outline, 1)
			_draw_ellipse(img, 16, 9, 6, 6, Color("#32f5c8"))
			_fill_rect(img, 10, 18, 12, 5, Color("#ffd858"))
		"museum_pedestal_empty":
			_fill_rect(img, 6, 12, 20, 18, Color("#98a4b0"))
			_draw_border(img, 6, 12, 20, 18, outline, 1)
			_fill_rect(img, 10, 18, 12, 5, Color("#505c68"))
		"lightning_obelisk":
			_fill_rect(img, 8, 2, 16, 28, Color("#4f6272"))
			_draw_border(img, 8, 2, 16, 28, outline, 1)
			_fill_rect(img, 13, 5, 6, 22, Color("#32f5c8"))
		"tutorial_arrow":
			# Crisp golden bouncing arrow pointing down
			_fill_rect(img, 12, 4, 8, 12, Color("#ffd848"))
			for row in range(8):
				_fill_rect(img, 6 + row, 16 + row, 20 - row * 2, 1, Color("#ffd848"))
			_draw_border(img, 12, 4, 8, 12, outline, 1)
		_:
			_fill_rect(img, 4, 4, 24, 24, Color("#ffd858"))
			_draw_border(img, 4, 4, 24, 24, outline, 1)

	var tex := ImageTexture.create_from_image(img)
	_prop_cache[key] = tex
	return tex
