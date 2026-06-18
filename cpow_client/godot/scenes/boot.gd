extends Node
## CPoW client boot — always routes to area hub (not Eldoria 2D).

const SCENE_MENU := "res://scenes/main_menu.tscn"


func _ready() -> void:
	get_tree().change_scene_to_file(SCENE_MENU)
