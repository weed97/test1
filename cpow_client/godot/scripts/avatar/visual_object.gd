extends RefCounted
class_name VisualObject
## Parse CreativeObject visual metadata from CPoW API payloads.

const SLOTS := ["avatar", "weapon", "movement", "accessory", "world_prop"]

var object_id: String = ""
var creator_id: String = ""
var label: String = ""
var glb_url: String = ""
var slot: String = "world_prop"
var attach_bone: String = ""
var offset: Dictionary = {}


static func from_object_dict(data: Dictionary) -> VisualObject:
	var vo := VisualObject.new()
	vo.object_id = str(data.get("id", ""))
	vo.creator_id = str(data.get("creator_id", ""))
	vo.label = str(data.get("label", ""))

	var visual: Dictionary = data.get("visual", {})
	if not visual.is_empty():
		vo._apply_visual_dict(visual)
	else:
		vo._infer_from_properties(data.get("properties", []))
	return vo


func _apply_visual_dict(visual: Dictionary) -> void:
	glb_url = str(visual.get("glb_url", ""))
	slot = str(visual.get("slot", "world_prop"))
	if slot not in SLOTS:
		slot = "world_prop"
	attach_bone = str(visual.get("attach_bone", ""))
	offset = visual.get("offset", {})


func _infer_from_properties(properties: Array) -> void:
	for raw in properties:
		if raw is not Dictionary:
			continue
		var name := str(raw.get("name", "")).to_lower()
		var unit := str(raw.get("unit", ""))
		match name:
			"visual_glb_url":
				glb_url = unit
			"visual_slot":
				slot = unit if unit in SLOTS else "world_prop"
			"visual_attach_bone":
				attach_bone = unit


func has_glb() -> bool:
	return not glb_url.is_empty()


func is_equippable() -> bool:
	return slot in ["weapon", "movement", "accessory"]


func owned_by(user_id: String) -> bool:
	return not user_id.is_empty() and creator_id == user_id


func offset_position() -> Vector3:
	var pos: Variant = offset.get("position", [0.0, 0.0, 0.0])
	if pos is Array and pos.size() >= 3:
		return Vector3(float(pos[0]), float(pos[1]), float(pos[2]))
	return Vector3.ZERO


func offset_rotation_deg() -> Vector3:
	var rot: Variant = offset.get("rotation", [0.0, 0.0, 0.0])
	if rot is Array and rot.size() >= 3:
		return Vector3(float(rot[0]), float(rot[1]), float(rot[2]))
	return Vector3.ZERO


func offset_scale() -> Vector3:
	var scl: Variant = offset.get("scale", [1.0, 1.0, 1.0])
	if scl is Array and scl.size() >= 3:
		return Vector3(float(scl[0]), float(scl[1]), float(scl[2]))
	return Vector3.ONE
