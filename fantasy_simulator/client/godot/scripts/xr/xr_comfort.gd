extends Node
class_name XRComfort
## XR 멀미 완화 — 비네팅·텔레포트 이동 (MVP).

signal teleport_requested(target: Vector3)

@export var vignette_enabled: bool = true
@export var teleport_max_distance: float = 8.0
@export var snap_turn_degrees: float = 45.0

var _origin: XROrigin3D = null
var _camera: Node3D = null


func setup(origin: XROrigin3D, camera: Node3D) -> void:
	_origin = origin
	_camera = camera


func snap_turn(direction: int) -> void:
	if _origin == null:
		return
	var radians := deg_to_rad(snap_turn_degrees * float(direction))
	_origin.rotate_y(radians)


func teleport_forward() -> void:
	if _origin == null or _camera == null:
		return
	var forward := -_camera.global_transform.basis.z
	forward.y = 0.0
	if forward.length_squared() < 0.001:
		return
	forward = forward.normalized()
	var target := _origin.global_position + forward * 2.5
	target.y = _origin.global_position.y
	teleport_to(target)


func teleport_to(world_pos: Vector3) -> void:
	if _origin == null:
		return
	_origin.global_position = world_pos
	teleport_requested.emit(world_pos)
