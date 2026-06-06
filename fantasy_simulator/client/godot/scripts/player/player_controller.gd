extends CharacterBody2D
## Godot movement — reports tile coords to simulation via ApiClient.

const MOVE_SPEED := 120.0

var map_id: String = "ashpoint_01"
var _last_reported := Vector2i(-9999, -9999)
var _syncing := false
var _map_pixel_w := 1280
var _map_pixel_h := 960


func _ready() -> void:
	map_id = ApiClient.sim_map_id
	_refresh_map_bounds()
	position = _tile_to_pixel(ApiClient.sim_tile)
	_last_reported = ApiClient.sim_tile
	ApiClient.position_synced.connect(_on_position_synced)
	ApiClient.maps_loaded.connect(_on_maps_loaded)


func _tile_to_pixel(tile: Vector2i) -> Vector2:
	return Vector2(tile) * ApiClient.tile_pixels + Vector2(8, 8)


func _refresh_map_bounds() -> void:
	var m: Dictionary = ApiClient.world_maps.get(map_id, {})
	_map_pixel_w = int(m.get("width", 80)) * ApiClient.tile_pixels
	_map_pixel_h = int(m.get("height", 60)) * ApiClient.tile_pixels


func _physics_process(_delta: float) -> void:
	var input_dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if input_dir.length_squared() > 0:
		velocity = input_dir.normalized() * MOVE_SPEED
	else:
		velocity = Vector2.ZERO
	move_and_slide()
	_clamp_inside_map()
	_try_report_tile()


func _clamp_inside_map() -> void:
	var margin := 8.0
	position.x = clampf(position.x, margin, float(_map_pixel_w) - margin)
	position.y = clampf(position.y, margin, float(_map_pixel_h) - margin)


func _try_report_tile() -> void:
	if _syncing:
		return
	var tile := Vector2i(
		floori(position.x / ApiClient.tile_pixels),
		floori(position.y / ApiClient.tile_pixels),
	)
	if tile == _last_reported:
		return
	var prev_tile := _last_reported
	_syncing = true
	var ok: bool = await ApiClient.sync_position(map_id, tile.x, tile.y)
	_syncing = false
	if ok:
		_last_reported = ApiClient.sim_tile
		position = _tile_to_pixel(ApiClient.sim_tile)
	else:
		_last_reported = prev_tile
		position = _tile_to_pixel(prev_tile)


func _on_position_synced(payload: Dictionary) -> void:
	if not payload.get("ok", false):
		return
	map_id = ApiClient.sim_map_id
	_refresh_map_bounds()
	position = _tile_to_pixel(ApiClient.sim_tile)
	_last_reported = ApiClient.sim_tile
	if payload.get("map_changed", false):
		get_tree().call_group("exploration_root", "on_map_changed", payload)


func _on_maps_loaded(_payload: Dictionary) -> void:
	_refresh_map_bounds()
	position = _tile_to_pixel(ApiClient.sim_tile)
	_last_reported = ApiClient.sim_tile
