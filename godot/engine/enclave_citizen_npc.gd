class_name EnclaveCitizenNPC
extends Node2D
## Gen-3 Pokémon Emerald Overworld Citizen NPC.
## Displays the citizen's 32x48 pixel sprite, 2-frame breathing idle animation,
## turns to face Willow when spoken to, and shows a compact name tag when nearby.

var character_id: String = "enclave_03_silas"
var citizen_data: Dictionary = {}
var facing_dir: String = "DOWN"
var idle_frame: int = 0
var _anim_timer: float = 0.0
var _sprite_factory: RefCounted = null

var sprite: Sprite2D = null
var name_label: Label = null


func setup(cid: String, data: Dictionary, factory: RefCounted, start_pos: Vector2) -> void:
	character_id = cid
	citizen_data = data.duplicate(true)
	_sprite_factory = factory
	position = start_pos
	y_sort_enabled = true

	if sprite == null:
		sprite = Sprite2D.new()
		sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		sprite.position = Vector2(0, -16)
		add_child(sprite)

	if name_label == null:
		name_label = Label.new()
		name_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		name_label.position = Vector2(-44, -48)
		name_label.size = Vector2(88, 16)
		name_label.add_theme_font_size_override("font_size", 9)
		name_label.add_theme_color_override("font_color", Color("#f4ead5"))
		name_label.add_theme_color_override("font_outline_color", Color("#12161f"))
		name_label.add_theme_constant_override("outline_size", 3)
		add_child(name_label)

	name_label.text = str(citizen_data.get("name", cid))
	_refresh_sprite()


func _process(delta: float) -> void:
	_anim_timer += delta
	if _anim_timer >= 0.55:
		_anim_timer = 0.0
		idle_frame = (idle_frame + 1) % 2
		_refresh_sprite()


func turn_toward(target_world_pos: Vector2) -> void:
	var diff := target_world_pos - global_position
	if absf(diff.x) > absf(diff.y):
		facing_dir = "RIGHT" if diff.x >= 0.0 else "LEFT"
	else:
		facing_dir = "DOWN" if diff.y >= 0.0 else "UP"
	_refresh_sprite()


func _refresh_sprite() -> void:
	if _sprite_factory != null and sprite != null:
		sprite.texture = _sprite_factory.call("get_citizen_frame", character_id, facing_dir, idle_frame)
		sprite.flip_h = false
