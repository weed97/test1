extends Node3D
class_name EquipmentManager
## Attach creator-sold glb assets to avatar bones (VRoid / glTF skeleton).

const SLOT_BONES := {
	"weapon": "RightHand",
	"movement": "Hips",
	"accessory": "Head",
}

@export var default_weapon_bone: String = "RightHand"
@export var default_movement_bone: String = "Hips"
@export var default_accessory_bone: String = "Head"

var _avatar_root: Node3D
var _equipped: Dictionary = {}
var _pending: Dictionary = {}


func setup(avatar_root: Node3D) -> void:
	_avatar_root = avatar_root
	_equipped.clear()
	_pending.clear()


func equip(visual: VisualObject) -> void:
	if visual == null or not visual.has_glb():
		return
	if not visual.is_equippable():
		push_warning("EquipmentManager: slot %s is not equippable" % visual.slot)
		return
	unequip_slot(visual.slot)
	_pending[visual.slot] = visual
	_load_and_attach(visual)


func unequip_slot(slot: String) -> void:
	if _equipped.has(slot):
		var node: Node = _equipped[slot]
		if is_instance_valid(node):
			node.queue_free()
		_equipped.erase(slot)


func unequip_all() -> void:
	for slot in _equipped.keys():
		unequip_slot(slot)


func _bone_name_for(visual: VisualObject) -> String:
	if not visual.attach_bone.is_empty():
		return visual.attach_bone
	return str(SLOT_BONES.get(visual.slot, default_weapon_bone))


func _load_and_attach(visual: VisualObject) -> void:
	var path := visual.glb_url
	if path.begins_with("http://") or path.begins_with("https://"):
		push_warning("EquipmentManager: remote glb not cached yet — %s" % path)
		_attach_placeholder(visual)
		return

	if not ResourceLoader.exists(path):
		push_warning("EquipmentManager: missing glb — %s" % path)
		_attach_placeholder(visual)
		return

	var scene: PackedScene = load(path)
	if scene == null:
		_attach_placeholder(visual)
		return

	var instance := scene.instantiate()
	_apply_offset(instance, visual)
	_parent_to_bone(instance, _bone_name_for(visual), visual.slot)


func _attach_placeholder(visual: VisualObject) -> void:
	var mesh := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.08, 0.3, 0.04) if visual.slot == "weapon" else Vector3(0.12, 0.12, 0.12)
	mesh.mesh = box
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.9, 0.75, 0.2) if visual.slot == "weapon" else Color(0.4, 0.7, 1.0)
	mesh.material_override = mat
	mesh.name = "Placeholder_%s" % visual.slot
	_apply_offset(mesh, visual)
	_parent_to_bone(mesh, _bone_name_for(visual), visual.slot)


func _apply_offset(node: Node3D, visual: VisualObject) -> void:
	node.position = visual.offset_position()
	node.rotation_degrees = visual.offset_rotation_deg()
	node.scale = visual.offset_scale()


func _parent_to_bone(node: Node3D, bone_name: String, slot: String) -> void:
	var anchor := _find_bone(_avatar_root, bone_name)
	if anchor == null:
		anchor = Node3D.new()
		anchor.name = "EquipAnchor_%s" % bone_name
		_avatar_root.add_child(anchor)
	anchor.add_child(node)
	_equipped[slot] = node
	if _pending.has(slot):
		_pending.erase(slot)


func _find_bone(root: Node, bone_name: String) -> Node3D:
	if root is BoneAttachment3D and root.bone_name == bone_name:
		return root
	if root.name == bone_name and root is Node3D:
		return root as Node3D
	for child in root.get_children():
		var found := _find_bone(child, bone_name)
		if found != null:
			return found
	return null
