extends Node
class_name XRHandPinch
## OpenXR 손 추적 핀치 감지 — 엄지·검지 거리 기반.

signal pinch_started(strength: float, world_pos: Vector3)
signal pinch_updated(strength: float, world_pos: Vector3)
signal pinch_released(strength: float, world_pos: Vector3, hold_time: float)

enum HandSide { LEFT, RIGHT }

@export var hand_side: HandSide = HandSide.RIGHT
@export var pinch_on_distance: float = 0.038
@export var pinch_off_distance: float = 0.052
@export var min_release_strength: float = 0.45
@export var min_hold_time: float = 0.08

var is_pinching: bool = false
var pinch_strength: float = 0.0
var pinch_world_position: Vector3 = Vector3.ZERO

var _tracker_name: String = "right_hand"
var _controller: XRController3D = null
var _pinching: bool = false
var _pinch_start_time: float = 0.0
var _peak_strength: float = 0.0
var _hand_available: bool = false


func setup(controller: XRController3D, side: HandSide) -> void:
	hand_side = side
	_controller = controller
	_tracker_name = "left_hand" if side == HandSide.LEFT else "right_hand"


func _process(_delta: float) -> void:
	var sample := _sample_pinch()
	if not sample.get("ok", false):
		if _pinching:
			_end_pinch()
		return

	var strength: float = sample.strength
	var world_pos: Vector3 = sample.pos
	pinch_strength = strength
	pinch_world_position = world_pos

	if not _pinching:
		if strength >= min_release_strength:
			_begin_pinch(strength, world_pos)
	else:
		_peak_strength = maxf(_peak_strength, strength)
		pinch_updated.emit(strength, world_pos)
		if strength < min_release_strength * 0.65:
			_end_pinch()


func _sample_pinch() -> Dictionary:
	_hand_available = false
	var tracker := XRServer.get_tracker(_tracker_name)

	if tracker is XRHandTracker:
		var hand := tracker as XRHandTracker
		if hand.has_hand_data():
			var thumb := hand.get_hand_joint_transform(XRHandTracker.HAND_JOINT_THUMB_TIP)
			var index := hand.get_hand_joint_transform(XRHandTracker.HAND_JOINT_INDEX_TIP)
			var dist := thumb.origin.distance_to(index.origin)
			_hand_available = true
			return {
				"ok": true,
				"strength": _distance_to_strength(dist),
				"pos": (thumb.origin + index.origin) * 0.5,
			}

	if _controller != null and _controller.get_is_active():
		var strength := 0.0
		var trigger_val := _controller.get_float("trigger")
		var pinch_val := _controller.get_float("pinch")
		if pinch_val > 0.0:
			_hand_available = true
			strength = maxf(strength, pinch_val)
		if trigger_val > 0.5:
			strength = maxf(strength, trigger_val)
		if strength > 0.0:
			return {"ok": true, "strength": strength, "pos": _controller.global_position}

	return {"ok": false}


func _distance_to_strength(dist: float) -> float:
	if dist <= pinch_on_distance:
		return 1.0
	if dist >= pinch_off_distance:
		return 0.0
	var t := (dist - pinch_on_distance) / (pinch_off_distance - pinch_on_distance)
	return clampf(1.0 - t, 0.0, 1.0)


func _begin_pinch(strength: float, world_pos: Vector3) -> void:
	_pinching = true
	is_pinching = true
	_pinch_start_time = Time.get_ticks_msec() / 1000.0
	_peak_strength = strength
	pinch_started.emit(strength, world_pos)


func _end_pinch() -> void:
	var hold := Time.get_ticks_msec() / 1000.0 - _pinch_start_time
	var release_strength := _peak_strength
	var pos := pinch_world_position
	_pinching = false
	is_pinching = false
	pinch_strength = 0.0
	if hold >= min_hold_time and release_strength >= min_release_strength:
		pinch_released.emit(release_strength, pos, hold)
	_peak_strength = 0.0


func uses_hand_tracking() -> bool:
	return _hand_available
