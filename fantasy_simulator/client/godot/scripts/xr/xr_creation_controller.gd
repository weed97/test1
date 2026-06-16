extends Node
class_name XRCreationController
## XR 창조 입력 — 손 추적 핀치 · 컨트롤러 폴백 · 데스크톱 시뮬레이터.

signal creation_requested(intent: Dictionary)
signal connect_requested(source_id: String, target_id: String, pose: Dictionary)
signal dual_pinch_connect(pose_a: Dictionary, pose_b: Dictionary, strength: float)

enum CreationMode { HEAT, MATERIAL }

@export var creation_mode: CreationMode = CreationMode.HEAT
@export var pinch_threshold: float = 0.75
@export var simulator_enabled: bool = true
@export var dual_hand_connect_enabled: bool = true

var _xr_active: bool = false
var _left_controller: XRController3D = null
var _right_controller: XRController3D = null
var _left_pinch: XRHandPinch = null
var _right_pinch: XRHandPinch = null
var _left_visual: XRHandPinchVisual = null
var _right_visual: XRHandPinchVisual = null
var _sim_camera: Camera3D = null
var _last_pinch_time: float = 0.0
const PINCH_COOLDOWN := 0.35

var _selected_object_id: String = ""
var _sim_pinching: bool = false
var _sim_pinch_strength: float = 0.0
var _sim_pinch_pos: Vector3 = Vector3.ZERO
var _sim_pinch_start: float = 0.0
var _left_release_pending: Dictionary = {}
var _right_release_pending: Dictionary = {}
var _resolve_scheduled: bool = false
const DUAL_PINCH_WINDOW := 0.35


func setup_xr(origin: XROrigin3D, visuals_root: Node3D) -> void:
	_left_controller = origin.get_node_or_null("LeftController") as XRController3D
	_right_controller = origin.get_node_or_null("RightController") as XRController3D
	_xr_active = XRServer.primary_interface != null and XRServer.primary_interface.is_initialized()

	_left_pinch = XRHandPinch.new()
	_left_pinch.name = "LeftHandPinch"
	_left_pinch.hand_side = XRHandPinch.HandSide.LEFT
	add_child(_left_pinch)

	_right_pinch = XRHandPinch.new()
	_right_pinch.name = "RightHandPinch"
	_right_pinch.hand_side = XRHandPinch.HandSide.RIGHT
	add_child(_right_pinch)

	if _left_controller:
		_left_pinch.setup(_left_controller, XRHandPinch.HandSide.LEFT)
		_left_pinch.pinch_updated.connect(_on_left_pinch_updated)
		_left_pinch.pinch_released.connect(_on_left_pinch_released)
	if _right_controller:
		_right_pinch.setup(_right_controller, XRHandPinch.HandSide.RIGHT)
		_right_pinch.pinch_updated.connect(_on_right_pinch_updated)
		_right_pinch.pinch_released.connect(_on_right_pinch_released)
		_right_controller.button_pressed.connect(_on_xr_button_pressed)

	_left_visual = XRHandPinchVisual.new()
	_left_visual.name = "LeftPinchVisual"
	visuals_root.add_child(_left_visual)
	_right_visual = XRHandPinchVisual.new()
	_right_visual.name = "RightPinchVisual"
	visuals_root.add_child(_right_visual)
	_sync_visual_mode()


func setup_simulator(camera: Camera3D) -> void:
	_sim_camera = camera
	_xr_active = false


func uses_hand_tracking() -> bool:
	if _right_pinch and _right_pinch.uses_hand_tracking():
		return true
	if _left_pinch and _left_pinch.uses_hand_tracking():
		return true
	return false


func _sync_visual_mode() -> void:
	var heat := creation_mode == CreationMode.HEAT
	if _left_visual:
		_left_visual.set_creation_mode(heat)
	if _right_visual:
		_right_visual.set_creation_mode(heat)


func _unhandled_input(event: InputEvent) -> void:
	if _xr_active:
		return
	if not simulator_enabled:
		return

	if event is InputEventMouseButton:
		var mb := event as InputEventMouseButton
		if mb.button_index == MOUSE_BUTTON_LEFT:
			if mb.pressed:
				_sim_begin_pinch(mb.position)
			else:
				_sim_end_pinch()
	elif event is InputEventMouseMotion:
		var mm := event as InputEventMouseMotion
		if _sim_pinching:
			_sim_pinch_drag(mm.position)
	elif event is InputEventKey:
		var key := event as InputEventKey
		if not key.pressed or key.echo:
			return
		match key.keycode:
			KEY_1:
				creation_mode = CreationMode.HEAT
				_sync_visual_mode()
			KEY_2:
				creation_mode = CreationMode.MATERIAL
				_sync_visual_mode()
			KEY_C:
				_selected_object_id = ""


func _sim_begin_pinch(screen_pos: Vector2) -> void:
	if _sim_camera == null:
		return
	var hit_pos := _raycast_screen(screen_pos)
	_sim_pinching = true
	_sim_pinch_pos = hit_pos
	_sim_pinch_strength = 0.0
	_sim_pinch_start = Time.get_ticks_msec() / 1000.0
	if _right_visual:
		_right_visual.show_pinch(hit_pos, 0.3)


func _sim_end_pinch() -> void:
	if not _sim_pinching:
		return
	_sim_pinching = false
	var hold := Time.get_ticks_msec() / 1000.0 - _sim_pinch_start
	_sim_pinch_strength = clampf(hold * 1.8, 0.35, 1.0)
	if _right_visual:
		_right_visual.hide_pinch()
	_emit_creation_at(
		Transform3D(Basis.IDENTITY, _sim_pinch_pos),
		_sim_pinch_strength,
		"simulator_pinch",
	)


func _sim_pinch_drag(screen_pos: Vector2) -> void:
	if not _sim_pinching or _sim_camera == null:
		return
	_sim_pinch_pos = _raycast_screen(screen_pos)
	var hold := Time.get_ticks_msec() / 1000.0 - _sim_pinch_start
	_sim_pinch_strength = clampf(hold * 1.8, 0.2, 1.0)
	if _right_visual:
		_right_visual.show_pinch(_sim_pinch_pos, _sim_pinch_strength)


func _raycast_screen(screen_pos: Vector2) -> Vector3:
	var origin := _sim_camera.project_ray_origin(screen_pos)
	var direction := _sim_camera.project_ray_normal(screen_pos)
	var space := _sim_camera.get_world_3d().direct_space_state
	var query := PhysicsRayQueryParameters3D.create(origin, origin + direction * 50.0)
	var hit := space.intersect_ray(query)
	if hit.is_empty():
		return origin + direction * 3.0
	return hit.position


func _on_left_pinch_updated(strength: float, world_pos: Vector3) -> void:
	if _left_visual:
		_left_visual.show_pinch(world_pos, strength)


func _on_right_pinch_updated(strength: float, world_pos: Vector3) -> void:
	if _right_visual:
		_right_visual.show_pinch(world_pos, strength)


func _on_left_pinch_released(strength: float, world_pos: Vector3, hold: float) -> void:
	if _left_visual:
		_left_visual.hide_pinch()
	_handle_pinch_release("left", strength, world_pos, hold)


func _on_right_pinch_released(strength: float, world_pos: Vector3, hold: float) -> void:
	if _right_visual:
		_right_visual.hide_pinch()
	_handle_pinch_release("right", strength, world_pos, hold)


func _handle_pinch_release(hand: String, strength: float, world_pos: Vector3, hold: float) -> void:
	var pending := {
		"hand": hand,
		"strength": strength,
		"pos": world_pos,
		"hold": hold,
	}
	if hand == "left":
		_left_release_pending = pending
	else:
		_right_release_pending = pending

	if dual_hand_connect_enabled and not _left_release_pending.is_empty() and not _right_release_pending.is_empty():
		if _try_dual_hand_connect():
			_left_release_pending = {}
			_right_release_pending = {}
			return

	_schedule_pinch_resolve()


func _schedule_pinch_resolve() -> void:
	if _resolve_scheduled:
		return
	_resolve_scheduled = true
	get_tree().create_timer(DUAL_PINCH_WINDOW).timeout.connect(
		_resolve_pending_pinches, CONNECT_ONE_SHOT
	)


func _resolve_pending_pinches() -> void:
	_resolve_scheduled = false
	if dual_hand_connect_enabled and _try_dual_hand_connect():
		_left_release_pending = {}
		_right_release_pending = {}
		return
	for pending in [_left_release_pending, _right_release_pending]:
		if pending.is_empty():
			continue
		_emit_creation_at(
			Transform3D(Basis.IDENTITY, pending.pos),
			float(pending.strength),
			"hand_pinch",
		)
	_left_release_pending = {}
	_right_release_pending = {}


func _try_dual_hand_connect() -> bool:
	if _left_release_pending.is_empty() or _right_release_pending.is_empty():
		return false

	var la: Vector3 = _left_release_pending.pos
	var ra: Vector3 = _right_release_pending.pos
	var avg_strength := (
		float(_left_release_pending.strength) + float(_right_release_pending.strength)
	) * 0.5

	if _left_visual and _right_visual:
		_left_visual.show_connect(la, ra, avg_strength)
		_right_visual.hide_pinch()
		_left_visual.hide_pinch()

	var pose_a := XRPoseSerializer.vector_to_pose(la, avg_strength)
	var pose_b := XRPoseSerializer.vector_to_pose(ra, avg_strength)
	dual_pinch_connect.emit(pose_a, pose_b, avg_strength)
	return true


func _on_xr_button_pressed(name: String) -> void:
	if name != "trigger_click" and name != "by_button_trigger":
		return
	if _right_controller == null:
		return
	_emit_creation_at(_right_controller.global_transform, 1.0, "controller_trigger")


func _emit_creation_at(xform: Transform3D, strength: float, input_source: String) -> void:
	var now := Time.get_ticks_msec() / 1000.0
	if now - _last_pinch_time < PINCH_COOLDOWN:
		return
	_last_pinch_time = now

	var clamped := clampf(strength, 0.2, 1.0)
	var gesture := "heat_pinch" if creation_mode == CreationMode.HEAT else "material_sculpt"
	var hint := "heat_intensity" if creation_mode == CreationMode.HEAT else "material_type"
	var label := "XR 열원" if creation_mode == CreationMode.HEAT else "XR 재료"

	var device := ApiConfig.xr_device_dict()
	device["hand_tracking"] = uses_hand_tracking() or input_source == "hand_pinch"

	var intent := {
		"creator_id": ApiConfig.creator_id,
		"gesture": gesture,
		"property_hint": hint,
		"intensity": clamped,
		"pinch_strength": clamped,
		"label": label,
		"pose": XRPoseSerializer.transform_to_pose(xform),
		"device": device,
		"input_source": input_source,
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
