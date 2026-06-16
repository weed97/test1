extends Node
## 앱 부팅 라우터 — Quest(Android)는 XR 월드로, 데스크톱은 메인 메뉴.

const SCENE_MENU := "res://scenes/main_menu.tscn"
const SCENE_XR := "res://scenes/xr/world_xr.tscn"


func _ready() -> void:
	var scene := SCENE_XR if _should_auto_launch_xr() else SCENE_MENU
	get_tree().change_scene_to_file(scene)


func _should_auto_launch_xr() -> bool:
	if OS.get_environment("CPOW_FORCE_XR") == "1":
		return true
	if OS.get_environment("CPOW_FORCE_MENU") == "1":
		return false
	if OS.get_name() == "Android":
		return true
	return false
