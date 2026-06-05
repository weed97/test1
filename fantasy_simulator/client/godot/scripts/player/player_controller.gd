extends CharacterBody2D
## Godot movement — reports tile coords to simulation via ApiClient.

const MOVE_SPEED := 120.0

var map_id: String = "ashpoint_01"
var _last_reported := Vector2i(-9999, -9999)
var _syncing := false


func _ready() -> void:
	map_id = ApiClient.sim_map_id
	position = Vector2(ApiClient.sim_tile) * ApiClient.tile_pixels + Vector2(8, 8)
	_last_reported = ApiClient.sim_tile
	ApiClient.position_synced.connect(_on_position_synced)


func _physics_process(_delta: float) -> void:
	var input_dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if input_dir.length_squared() > 0:
		velocity = input_dir.normalized() * MOVE_SPEED
	else:
		velocity = Vector2.ZERO
	move_and_slide()
	_try_report_tile()


func _try_report_tile() -> void:
	if _syncing:
		return
	var tile := Vector2i(
		floori(position.x / ApiClient.tile_pixels),
		floori(position.y / ApiClient.tile_pixels),
	)
	if tile == _last_reported:
		return
	_last_reported = tile
	_syncing = true
	await ApiClient.sync_position(map_id, tile.x, tile.y)
	_syncing = false


func _on_position_synced(payload: Dictionary) -> void:
	if not payload.get("ok", false):
		return
	map_id = ApiClient.sim_map_id
	var pos: Dictionary = payload.get("position", {})
	if pos.is_empty():
		return
	position = Vector2(ApiClient.sim_tile) * ApiClient.tile_pixels + Vector2(8, 8)
	_last_reported = ApiClient.sim_tile
	if payload.get("map_changed", false):
		get_tree().call_group("exploration_root", "on_map_changed", payload)
