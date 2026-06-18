extends Node3D
class_name PlayerAvatar
## Local avatar root — VRoid/glb skeleton hook + equipment slots.

@onready var _body: MeshInstance3D = $Body
@onready var _equip: EquipmentManager = $EquipmentManager

var _avatar_path: String = "res://assets/placeholders/avatar_stub.glb"


func _ready() -> void:
	_equip.setup(self)
	_build_placeholder_body()


func set_avatar_glb(path: String) -> void:
	if path.is_empty():
		return
	_avatar_path = path
	# Future: GLTFDocument load for .vrm / .glb avatar swap.


func sync_equipment_from_state(state: Dictionary) -> void:
	var objects: Dictionary = state.get("objects", {})
	for object_id in objects.keys():
		var data: Dictionary = objects[object_id]
		var visual := VisualObject.from_object_dict(data)
		if visual.is_equippable() and visual.owned_by(AreasClient.current_user_id):
			_equip.equip(visual)


func _build_placeholder_body() -> void:
	var capsule := CapsuleMesh.new()
	capsule.radius = 0.25
	capsule.height = 1.4
	_body.mesh = capsule
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.55, 0.65, 0.85)
	_body.material_override = mat
	_body.position = Vector3(-2.0, 0.9, 0.0)
