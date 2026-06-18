extends Node2D
## Terrain + projectiles layer for live siege (units are child nodes).

var battle_host: Node = null


func _draw() -> void:
	if battle_host != null and battle_host.has_method("paint_terrain"):
		battle_host.paint_terrain(self)
