extends Node3D
## 3D area viewer — syncs /v1/areas/state and shows CreativeObjects.

@onready var _renderer: AreaObjectRenderer = $AreaObjects
@onready var _avatar: PlayerAvatar = $PlayerAvatar
@onready var _camera: Camera3D = $Camera3D
@onready var _hud: Label = $CanvasLayer/HUD
@onready var _log: RichTextLabel = $CanvasLayer/Log

var _orbit_yaw: float = 0.4
var _orbit_pitch: float = -0.35
var _orbit_dist: float = 8.0
var _busy: bool = false


func _ready() -> void:
	AreasClient.api_error.connect(_on_api_error)
	AreasClient.area_state_loaded.connect(_on_state_loaded)
	AreasClient.area_created.connect(_on_object_created)
	_update_hud()
	await _refresh_state()


func _process(_delta: float) -> void:
	_update_camera_orbit()


func _update_camera_orbit() -> void:
	var target := Vector3(3.5, 0.5, 2.0)
	var offset := Vector3(
		cos(_orbit_yaw) * cos(_orbit_pitch),
		sin(_orbit_pitch),
		sin(_orbit_yaw) * cos(_orbit_pitch),
	) * _orbit_dist
	_camera.global_position = target + offset
	_camera.look_at(target, Vector3.UP)


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseMotion and Input.is_mouse_button_pressed(MOUSE_BUTTON_RIGHT):
		var motion := event as InputEventMouseMotion
		_orbit_yaw -= motion.relative.x * 0.005
		_orbit_pitch = clamp(_orbit_pitch - motion.relative.y * 0.005, -1.2, 0.2)
	if event is InputEventMouseButton and event.pressed:
		var btn := event as InputEventMouseButton
		if btn.button_index == MOUSE_BUTTON_WHEEL_UP:
			_orbit_dist = max(3.0, _orbit_dist - 0.5)
		elif btn.button_index == MOUSE_BUTTON_WHEEL_DOWN:
			_orbit_dist = min(20.0, _orbit_dist + 0.5)


func _refresh_state() -> void:
	if AreasClient.current_area_id.is_empty():
		_log_append("[오류] area 미선택 — 메뉴로 돌아가세요")
		return
	await AreasClient.fetch_state()


func _on_state_loaded(payload: Dictionary) -> void:
	var state: Dictionary = payload.get("state", {})
	_renderer.sync_from_state(state)
	_avatar.sync_equipment_from_state(state)
	_update_hud()
	_log_append("오브젝트 %d개 동기화" % state.get("objects", {}).size())


func _on_object_created(payload: Dictionary) -> void:
	if payload.get("ok"):
		_log_append("창조: %s" % payload.get("object_id", "?"))
	await _refresh_state()


func _on_refresh_pressed() -> void:
	if _busy:
		return
	_busy = true
	await _refresh_state()
	_busy = false


func _on_create_heat_pressed() -> void:
	if _busy:
		return
	_busy = true
	await AreasClient.create_heat("열원", 75.0)
	_busy = false


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")


func _update_hud() -> void:
	var area: Dictionary = AreasClient.last_area
	_hud.text = "area: %s | %s | user: %s" % [
		AreasClient.current_area_id,
		area.get("label", ""),
		AreasClient.current_user_id,
	]


func _log_append(text: String) -> void:
	_log.append_text(text + "\n")


func _on_api_error(message: String) -> void:
	_log_append("[오류] %s" % message)
	_busy = false
