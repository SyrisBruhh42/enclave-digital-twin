class_name WillowPlayer
extends CharacterBody2D
## Playable Willow Overworld Controller (CharacterBody2D + Centered Camera2D).
## Supports 4-direction GBA walking, Running Shoes (Shift/X = 1.6x speed + dust puffs),
## one-way GBA basalt ledge hopping with parabolic vertical arc, and all 6 Alchemist Tools.
## Strictly enforces CM-02 anatomical laterality (sprite.flip_h = false on all views).

signal request_interact(facing_point: Vector2)
signal request_use_tool(tool_id: String, facing_point: Vector2)
signal request_cycle_tool(delta: int)
signal request_select_tool_slot(slot_idx: int)
signal ledge_hop_completed(landed_pos: Vector2)

const WALK_SPEED: float = 115.0
const RUN_MULTIPLIER: float = 1.6
const LEDGE_HOP_DURATION: float = 0.28
const LEDGE_HOP_DISTANCE: float = 64.0
const LEDGE_PEAK_HEIGHT: float = 16.0

var facing_dir: String = "DOWN"
var walk_frame: int = 0
var is_running: bool = false
var is_using_tool: bool = false
var is_hopping_ledge: bool = false
var controls_locked: bool = false
var equipped_tool_id: String = "trowel"

var _walk_anim_timer: float = 0.0
var _tool_pose_timer: float = 0.0
var _hop_elapsed: float = 0.0
var _hop_start_pos: Vector2 = Vector2.ZERO
var _hop_target_pos: Vector2 = Vector2.ZERO
var _dust_timer: float = 0.0

var sprite: Sprite2D = null
var shadow_poly: Polygon2D = null
var camera: Camera2D = null
var sprite_factory: RefCounted = null
var zone_manager_ref: Node = null


func setup(factory: RefCounted, zm: Node) -> void:
	sprite_factory = factory
	zone_manager_ref = zm
	y_sort_enabled = true

	if shadow_poly == null:
		shadow_poly = Polygon2D.new()
		shadow_poly.color = Color(0, 0, 0, 0.35)
		shadow_poly.polygon = PackedVector2Array([
			Vector2(-9, -2), Vector2(0, -5), Vector2(9, -2), Vector2(0, 2)
		])
		add_child(shadow_poly)

	if sprite == null:
		sprite = Sprite2D.new()
		sprite.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
		sprite.position = Vector2(0, -16)
		sprite.flip_h = false # CM-02 Laterality Invariant
		add_child(sprite)

	if camera == null:
		camera = Camera2D.new()
		camera.enabled = true
		camera.position_smoothing_enabled = false
		add_child(camera)

	var col_shape := get_node_or_null("CollisionShape2D") as CollisionShape2D
	if col_shape == null:
		col_shape = CollisionShape2D.new()
		col_shape.name = "CollisionShape2D"
		var rect := RectangleShape2D.new()
		rect.size = Vector2(18, 14)
		col_shape.shape = rect
		col_shape.position = Vector2(0, -4)
		add_child(col_shape)

	_refresh_sprite()


func configure_camera_limits(zone_px_size: Vector2, is_indoor: bool = false) -> void:
	if camera == null:
		return
	if is_indoor:
		camera.limit_left = -64
		camera.limit_top = -32
		camera.limit_right = int(zone_px_size.x) + 64
		camera.limit_bottom = int(zone_px_size.y) + 48
	else:
		camera.limit_left = 0
		camera.limit_top = 0
		camera.limit_right = int(zone_px_size.x)
		camera.limit_bottom = int(zone_px_size.y)


func _unhandled_input(event: InputEvent) -> void:
	if controls_locked or is_hopping_ledge:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		var kev := event as InputEventKey
		match kev.keycode:
			KEY_Z, KEY_SPACE, KEY_E:
				request_interact.emit(get_interaction_point())
			KEY_F:
				trigger_tool_pose(equipped_tool_id)
				request_use_tool.emit(equipped_tool_id, get_interaction_point())
			KEY_Q, KEY_TAB:
				request_cycle_tool.emit(1)
			KEY_1:
				request_select_tool_slot.emit(0)
			KEY_2:
				request_select_tool_slot.emit(1)
			KEY_3:
				request_select_tool_slot.emit(2)
			KEY_4:
				request_select_tool_slot.emit(3)
			KEY_5:
				request_select_tool_slot.emit(4)
			KEY_6:
				request_select_tool_slot.emit(5)


func _physics_process(delta: float) -> void:
	if is_hopping_ledge:
		_update_ledge_hop(delta)
		return

	if _tool_pose_timer > 0.0:
		_tool_pose_timer -= delta
		if _tool_pose_timer <= 0.0:
			is_using_tool = false
			_refresh_sprite()

	if controls_locked:
		velocity = Vector2.ZERO
		return

	var input_vec := Vector2.ZERO
	if Input.is_key_pressed(KEY_LEFT) or Input.is_key_pressed(KEY_A):
		input_vec.x -= 1.0
	if Input.is_key_pressed(KEY_RIGHT) or Input.is_key_pressed(KEY_D):
		input_vec.x += 1.0
	if Input.is_key_pressed(KEY_UP) or Input.is_key_pressed(KEY_W):
		input_vec.y -= 1.0
	if Input.is_key_pressed(KEY_DOWN) or Input.is_key_pressed(KEY_S):
		input_vec.y += 1.0

	is_running = Input.is_key_pressed(KEY_SHIFT) or Input.is_key_pressed(KEY_X)

	if input_vec.length_squared() > 0.0:
		if absf(input_vec.x) >= absf(input_vec.y):
			facing_dir = "RIGHT" if input_vec.x > 0.0 else "LEFT"
		else:
			facing_dir = "DOWN" if input_vec.y > 0.0 else "UP"

		# Check for 1-way GBA south ledge hop
		if facing_dir == "DOWN" and input_vec.y > 0.0 and zone_manager_ref != null and zone_manager_ref.has_method("can_hop_ledge_south"):
			if bool(zone_manager_ref.call("can_hop_ledge_south", position)):
				start_ledge_hop()
				return

		var spd := WALK_SPEED * (RUN_MULTIPLIER if is_running else 1.0)
		velocity = input_vec.normalized() * spd

		var next_pos := position + velocity * delta
		if zone_manager_ref != null and zone_manager_ref.has_method("is_walkable_world_pos"):
			if bool(zone_manager_ref.call("is_walkable_world_pos", next_pos)):
				position = next_pos
			else:
				var slide_x := Vector2(position.x + velocity.x * delta, position.y)
				var slide_y := Vector2(position.x, position.y + velocity.y * delta)
				if bool(zone_manager_ref.call("is_walkable_world_pos", slide_x)):
					position = slide_x
				elif bool(zone_manager_ref.call("is_walkable_world_pos", slide_y)):
					position = slide_y

		var step_interval := 0.11 if is_running else 0.17
		_walk_anim_timer += delta
		if _walk_anim_timer >= step_interval:
			_walk_anim_timer = 0.0
			walk_frame = (walk_frame + 1) % 4
			_refresh_sprite()

		if is_running:
			_dust_timer += delta
			if _dust_timer >= 0.14:
				_dust_timer = 0.0
				_spawn_dust_puff()
	else:
		velocity = Vector2.ZERO
		if walk_frame != 0:
			walk_frame = 0
			_refresh_sprite()


func start_ledge_hop() -> void:
	if is_hopping_ledge:
		return
	is_hopping_ledge = true
	_hop_elapsed = 0.0
	_hop_start_pos = position
	_hop_target_pos = position + Vector2(0, LEDGE_HOP_DISTANCE)
	facing_dir = "DOWN"
	walk_frame = 1
	_refresh_sprite()


func _update_ledge_hop(delta: float) -> void:
	_hop_elapsed += delta
	var t := clampf(_hop_elapsed / LEDGE_HOP_DURATION, 0.0, 1.0)
	position = _hop_start_pos.lerp(_hop_target_pos, t)
	var arc_height := sin(t * PI) * LEDGE_PEAK_HEIGHT
	if sprite != null:
		sprite.position = Vector2(0, -16.0 - arc_height)
	if t >= 1.0:
		is_hopping_ledge = false
		walk_frame = 0
		if sprite != null:
			sprite.position = Vector2(0, -16.0)
		_refresh_sprite()
		_spawn_dust_puff()
		ledge_hop_completed.emit(position)


func trigger_tool_pose(tool_id: String) -> void:
	equipped_tool_id = tool_id
	is_using_tool = true
	_tool_pose_timer = 0.28
	_refresh_sprite()


func get_interaction_point() -> Vector2:
	var dir_vec := Vector2.DOWN
	match facing_dir:
		"UP":
			dir_vec = Vector2.UP
		"LEFT":
			dir_vec = Vector2.LEFT
		"RIGHT":
			dir_vec = Vector2.RIGHT
		_:
			dir_vec = Vector2.DOWN
	return position + dir_vec * 28.0


func _spawn_dust_puff() -> void:
	if get_parent() == null:
		return
	var puff := Polygon2D.new()
	puff.color = Color(0.92, 0.88, 0.76, 0.65)
	puff.polygon = PackedVector2Array([
		Vector2(-3, -3), Vector2(3, -3), Vector2(3, 3), Vector2(-3, 3)
	])
	puff.position = position + Vector2(0, 2)
	get_parent().add_child(puff)
	var tw := puff.create_tween()
	tw.tween_property(puff, "modulate:a", 0.0, 0.22)
	tw.parallel().tween_property(puff, "scale", Vector2(1.6, 1.6), 0.22)
	tw.tween_callback(puff.queue_free)


func _refresh_sprite() -> void:
	if sprite != null and sprite_factory != null:
		sprite.texture = sprite_factory.call("get_willow_frame", facing_dir, walk_frame, equipped_tool_id, is_using_tool)
		sprite.flip_h = false # CM-02 anatomical laterality invariant
