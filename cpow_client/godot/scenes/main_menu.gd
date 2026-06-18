extends Control

var _busy: bool = false


func _ready() -> void:
	AreasClient.api_error.connect(_on_api_error)
	AreasClient.area_list_loaded.connect(_on_area_list_loaded)
	$VBox/ServerLabel.text = "API: %s" % AreasConfig.base_url()
	$VBox/UserEdit.text = AreasConfig.creator_id()
	_check_server()


func _check_server() -> void:
	var ok: bool = await AreasClient.health_check()
	if ok:
		$VBox/ServerLabel.text = "API: %s (연결됨)" % AreasConfig.base_url()
	else:
		$VBox/ServerLabel.text = (
			"API: %s (연결 실패)\n"
			+ "cd fantasy_simulator && uvicorn api.server:app --port 8765"
		) % AreasConfig.base_url()


func _on_refresh_pressed() -> void:
	if _busy:
		return
	_busy = true
	$VBox/Log.text += "\n[에리어 목록 조회]\n"
	await AreasClient.list_areas()
	_busy = false


func _on_found_pressed() -> void:
	if _busy:
		return
	_busy = true
	AreasClient.set_user_id($VBox/UserEdit.text.strip_edges())
	var label := $VBox/AreaNameEdit.text.strip_edges()
	if label.is_empty():
		label = "내 창조 에리어"
	$VBox/Log.text += "\n[에리어 개척] %s\n" % label
	var result := await AreasClient.found_area(label)
	if result.get("ok"):
		$VBox/Log.text += "area_id: %s\n" % AreasClient.current_area_id
	_busy = false


func _on_enter_pressed() -> void:
	if _busy:
		return
	AreasClient.set_user_id($VBox/UserEdit.text.strip_edges())
	var area_id := $VBox/AreaIdEdit.text.strip_edges()
	if area_id.is_empty():
		area_id = AreasClient.current_area_id
	if area_id.is_empty():
		$VBox/Log.text += "\n[오류] area_id 필요\n"
		return
	_busy = true
	var joined := await AreasClient.join_area(area_id)
	if joined.get("ok", false) or AreasClient.current_area_id == area_id:
		get_tree().change_scene_to_file("res://scenes/area/area_viewer.tscn")
	_busy = false


func _on_area_list_loaded(payload: Dictionary) -> void:
	var areas: Array = payload.get("areas", [])
	$VBox/Log.text += "총 %d개 에리어\n" % int(payload.get("count", areas.size()))
	for a in areas:
		if a is Dictionary:
			$VBox/Log.text += " · %s — %s\n" % [a.get("area_id", "?"), a.get("label", "")]


func _on_api_error(message: String) -> void:
	$VBox/Log.text += "\n[오류] %s\n" % message
	_busy = false


func _on_user_edit_text_submitted(_new_text: String) -> void:
	AreasClient.set_user_id($VBox/UserEdit.text.strip_edges())
