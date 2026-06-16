extends Node
class_name XRCreationController
## XR 창조 입력 — OpenXR 컨트롤러 또는 데스크톱 시뮬레이터.

signal creation_requested(intent: Dictionary)
signal connect_requested(source_id: String, target_id: String, pose: Dictionary)

enum CreationMode { HEAT, MATERIAL }

@export var creation_mode: CreationMode = CreationMode.HEAT
@export var pinch_threshold: float = 0.75
@export var simulator_enabled: bool = true

var _xr_active: bool = false
var _left_controller: XRController3D = null
var _right_controller: XRController3D = null
var _sim_camera: Camera3D = null
var _last_pinch_time: float = 0.0
const PINCH_COOLDOWN := 0.35

var _selected_object_id: String = ""


func setup_xr(origin: XROrigin3D) -> void:
	_left_controller = origin.get_node_or_null("LeftController") as XRController3D
	_right_controller = origin.get_node_or_null("RightController") as XRController3D
	_xr_active = XRServer.primary_interface != null and XRServer.primary_interface.is_initialized()
	if _xr_active and _right_controller:
		_right_controller.button_pressed.connect(_on_xr_button_pressed)


func setup_simulator(camera: Camera3D) -> void:
	_sim_camera = camera
	_xr_active = false


func _unhandled_input(event: InputEvent) -> void:
	if _xr_active:
		return
	if not simulator_enabled:
		return

	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.pressed and mb.button_index == MOUSE_BUTTON_LEFT:
			_simulator_pinch_at_screen(mb.position)
	elif event is InputEventKey:
		var key := event as InputEventKey
		if not key.pressed or key.echo:
			return
		match key.keycode:
			KEY_1:
				creation_mode = CreationMode.HEAT
			KEY_2:
				creation_mode = CreationMode.MATERIAL
			KEY_C:
				if not _selected_object_id.is_empty():
					_selected_object_id = ""


func _on_xr_button_pressed(name: String) -> void:
	if name != "trigger_click" and name != "by_button_trigger":
		return
	if _right_controller == null:
		return
	_emit_creation_at(_right_controller.global_transform)


func _simulator_pinch_at_screen(screen_pos: Vector2) -> void:
	if _sim_camera == null:
		return
	var origin := _sim_camera.project_ray_origin(screen_pos)
	var direction := _sim_camera.project_ray_normal(screen_pos)
	var space := _sim_camera.get_world_3d().direct_space_state
	var query := PhysicsRayQueryParameters3D.create(origin, origin + direction * 50.0)
	var hit := space.intersect_ray(query)
	var point: Vector3
	if hit.is_empty():
		point = origin + direction * 3.0
	else:
		point = hit.position
	var t := Transform3D(Basis.IDENTITY, point)
	_emit_creation_at(t)


func _emit_creation_at(xform: Transform3D) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	if now - _last_pinch_time < PINCH_COOLDOWN:
		return
	_last_pinch_time = now

	var gesture := "heat_pinch" if creation_mode == CreationMode.HEAT else "material_sculpt"
	var hint := "heat_intensity" if creation_mode == CreationMode.HEAT else "material_type"
	var label := "XR 열원" if creation_mode == CreationMode.HEAT else "XR 재료"

	var intent := {
		"creator_id": ApiConfig.creator_id,
		"gesture": gesture,
		"property_hint": hint,
		"intensity": 1.0,
		"label": label,
		"pose": XRPoseSerializer.transform_to_pose(xform),
		"device": ApiConfig.xr_device_dict(),
	}
	creation_requested.emit(intent)


func try_connect(source_id: String, target_id: String, pose: Transform3D) -> void:
	if source_id.is_empty() or target_id.is_empty() or source_id == target_id:
		return
	connect_requested.emit(
		source_id,
		target_id,
		XRPoseSerializer.transform_to_pose(pose),
	)
