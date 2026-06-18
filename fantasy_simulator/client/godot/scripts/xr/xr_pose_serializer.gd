extends RefCounted
class_name XRPoseSerializer
## Transform3D / Vector3 → CPoW XRCreationIntent pose dict.


static func transform_to_pose(t: Transform3D) -> Dictionary:
	return {
		"x": t.origin.x,
		"y": t.origin.y,
		"z": t.origin.z,
		"rotation_x": t.basis.get_euler().x,
		"rotation_y": t.basis.get_euler().y,
		"rotation_z": t.basis.get_euler().z,
		"scale": t.basis.get_scale().x,
	}


static func vector_to_pose(v: Vector3, scale: float = 1.0) -> Dictionary:
	return {
		"x": v.x,
		"y": v.y,
		"z": v.z,
		"rotation_x": 0.0,
		"rotation_y": 0.0,
		"rotation_z": 0.0,
		"scale": scale,
	}
