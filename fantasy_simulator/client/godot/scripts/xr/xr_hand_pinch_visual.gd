extends Node3D
class_name XRHandPinchVisual
## 핀치 지점 시각 피드백 — 강도에 따라 크기·밝기 변화.

@export var heat_color: Color = Color(1.0, 0.45, 0.1)
@export var material_color: Color = Color(0.55, 0.6, 0.7)
@export var connect_color: Color = Color(0.3, 0.85, 1.0)

var _sphere: MeshInstance3D
var _mat: StandardMaterial3D
var _visible_strength: float = 0.0
var _target_strength: float = 0.0
var _mode_heat: bool = true


func _ready() -> void:
	_build_sphere()
	visible = false


func _build_sphere() -> void:
	_sphere = MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = 0.04
	mesh.height = 0.08
	_sphere.mesh = mesh
	_mat = StandardMaterial3D.new()
	_mat.emission_enabled = true
	_sphere.material_override = _mat
	add_child(_sphere)


func set_creation_mode(heat: bool) -> void:
	_mode_heat = heat
	_update_color(0.0)


func show_pinch(world_pos: Vector3, strength: float) -> void:
	global_position = world_pos
	_target_strength = clampf(strength, 0.0, 1.0)
	visible = _target_strength > 0.05
	_update_color(_target_strength)


func hide_pinch() -> void:
	_target_strength = 0.0
	visible = false


func show_connect(from_pos: Vector3, to_pos: Vector3, strength: float) -> void:
	global_position = (from_pos + to_pos) * 0.5
	_target_strength = strength
	visible = true
	_mat.albedo_color = connect_color
	_mat.emission = connect_color * 0.8
	var dist := from_pos.distance_to(to_pos)
	if _sphere.mesh is SphereMesh:
		(_sphere.mesh as SphereMesh).radius = 0.03 + dist * 0.02
	_sphere.scale = Vector3.ONE * (0.5 + strength * 0.8)


func _process(delta: float) -> void:
	if not visible:
		return
	_visible_strength = lerpf(_visible_strength, _target_strength, delta * 12.0)
	_sphere.scale = Vector3.ONE * (0.4 + _visible_strength * 0.9)
	if _mat:
		_mat.emission_energy_multiplier = 0.5 + _visible_strength * 2.5


func _update_color(strength: float) -> void:
	if _mat == null:
		return
	var base := heat_color if _mode_heat else material_color
	_mat.albedo_color = base
	_mat.emission = base * (0.6 + strength * 0.4)
