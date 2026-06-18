extends Node3D
class_name AreaObjectRenderer
## Render CreativeObjects from /v1/areas/state in 3D space.

const GRID_SPACING := 1.4

var _nodes: Dictionary = {}


func clear_all() -> void:
	for id in _nodes.keys():
		var node: Node = _nodes[id]
		if is_instance_valid(node):
			node.queue_free()
	_nodes.clear()


func sync_from_state(state: Dictionary) -> void:
	var objects: Dictionary = state.get("objects", {})
	var seen: Dictionary = {}
	var index := 0
	for object_id in objects.keys():
		seen[object_id] = true
		var data: Dictionary = objects[object_id]
		var visual := VisualObject.from_object_dict(data)
		if _nodes.has(object_id):
			_update_node(_nodes[object_id], visual, index)
		else:
			_nodes[object_id] = _spawn_node(object_id, visual, index)
		index += 1

	for id in _nodes.keys():
		if not seen.has(id):
			var stale: Node = _nodes[id]
			if is_instance_valid(stale):
				stale.queue_free()
			_nodes.erase(id)


func _spawn_node(object_id: String, visual: VisualObject, index: int) -> Node3D:
	var node := Node3D.new()
	node.name = "Obj_%s" % object_id
	node.position = _grid_position(index)
	add_child(node)

	if visual.has_glb():
		var mesh_holder := MeshInstance3D.new()
		mesh_holder.name = "Visual"
		var sphere := SphereMesh.new()
		sphere.radius = 0.2
		mesh_holder.mesh = sphere
		var mat := StandardMaterial3D.new()
		mat.albedo_color = _color_for_slot(visual.slot)
		mat.emission_enabled = visual.slot == "world_prop"
		mat.emission = mat.albedo_color * 0.4
		mesh_holder.material_override = mat
		node.add_child(mesh_holder)
	else:
		node.add_child(_default_prop_mesh(visual))

	var label := Label3D.new()
	label.text = visual.label if not visual.label.is_empty() else object_id.substr(0, 6)
	label.font_size = 32
	label.position = Vector3(0, 0.35, 0)
	label.billboard = BaseMaterial3D.BILLBOARD_ENABLED
	node.add_child(label)
	return node


func _update_node(node: Node3D, visual: VisualObject, index: int) -> void:
	node.position = _grid_position(index)
	var label := node.get_node_or_null("Label3D") as Label3D
	if label and not visual.label.is_empty():
		label.text = visual.label


func _default_prop_mesh(visual: VisualObject) -> MeshInstance3D:
	var mesh := MeshInstance3D.new()
	var sphere := SphereMesh.new()
	sphere.radius = 0.15
	mesh.mesh = sphere
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(1.0, 0.45, 0.1)
	mat.emission_enabled = true
	mat.emission = Color(1.0, 0.35, 0.05)
	mesh.material_override = mat
	return mesh


func _grid_position(index: int) -> Vector3:
	var cols := 6
	var row := index / cols
	var col := index % cols
	return Vector3(col * GRID_SPACING, 0.0, row * GRID_SPACING)


func _color_for_slot(slot: String) -> Color:
	match slot:
		"weapon":
			return Color(0.85, 0.2, 0.2)
		"movement":
			return Color(0.2, 0.6, 0.95)
		"accessory":
			return Color(0.9, 0.75, 0.2)
		"avatar":
			return Color(0.6, 0.85, 0.5)
		_:
			return Color(0.55, 0.58, 0.62)
