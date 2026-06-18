extends Node3D
class_name XRCreationObject
## CPoW 창조물 3D 표현 — 열원(주황) / 재료(회색).

@export var object_id: String = ""
@export var property_hint: String = "heat_intensity"
@export var energy_value: float = 0.0

var _mesh: MeshInstance3D
var _light: OmniLight3D
var _pulse: float = 0.0


func _ready() -> void:
	_build_visual()


func configure(data: Dictionary) -> void:
	object_id = str(data.get("object_id", object_id))
	property_hint = str(data.get("property_hint", property_hint))
	energy_value = float(data.get("energy", data.get("energy_value", 0.0)))
	_build_visual()


func _build_visual() -> void:
	for child in get_children():
		child.queue_free()

	_mesh = MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.12 if property_hint == "heat_intensity" else 0.15
	sphere.height = sphere.radius * 2.0
	_mesh.mesh = sphere

	var mat := StandardMaterial3D.new()
	if property_hint == "heat_intensity":
		mat.albedo_color = Color(1.0, 0.45, 0.1)
		mat.emission_enabled = true
		mat.emission = Color(1.0, 0.35, 0.05)
		mat.emission_energy_multiplier = 1.5 + energy_value * 0.01
	else:
		mat.albedo_color = Color(0.55, 0.58, 0.62)
		mat.metallic = 0.7
		mat.roughness = 0.35
	_mesh.material_override = mat
	add_child(_mesh)

	if property_hint == "heat_intensity":
		_light = OmniLight3D.new()
		_light.light_color = Color(1.0, 0.5, 0.15)
		_light.light_energy = 1.2 + energy_value * 0.005
		_light.omni_range = 2.5
		add_child(_light)


func _process(delta: float) -> void:
	if property_hint != "heat_intensity" or _mesh == null:
		return
	_pulse += delta * 3.0
	var s := 1.0 + sin(_pulse) * 0.06
	_mesh.scale = Vector3.ONE * s
