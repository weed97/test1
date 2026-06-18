extends Control

var _session_busy: bool = false


func _ready() -> void:
	ApiClient.session_created.connect(_on_session_created)
	ApiClient.turn_completed.connect(_on_turn_completed)
	ApiClient.api_error.connect(_on_api_error)
	$VBox/ServerLabel.text = "API: %s" % ApiConfig.base_url()
	_check_server()


func _check_server() -> void:
	var ok: bool = await ApiClient.health_check()
	if ok:
		$VBox/ServerLabel.text = "API: %s (연결됨)" % ApiConfig.base_url()
	else:
		$VBox/ServerLabel.text = (
			"API: %s (연결 실패)\n"
			+ "원인: Python API 서버가 실행 중이 아닙니다.\n"
			+ "터미널: cd fantasy_simulator && pip install -r requirements-api.txt\n"
			+ "         uvicorn api.server:app --port 8765"
		) % ApiConfig.base_url()


func _on_new_game_pressed() -> void:
	if _session_busy:
		return
	_session_busy = true
	_set_play_buttons(false)
	$VBox/Narrative.clear()
	$VBox/Narrative.text = "세션 생성 중…\n"
	await ApiClient.new_game(42, "precision")
	_session_busy = false
	if ApiClient.session_id.is_empty():
		_set_play_buttons(true)


func _on_explore_pressed() -> void:
	if _session_busy or ApiClient.session_id.is_empty():
		$VBox/Narrative.text += "\n[오류] 세션이 없습니다. 새 게임을 먼저 시작하세요.\n"
		return
	$VBox/Narrative.text += "\n[탐험]\n"
	await ApiClient.run_turn("explore", "precision")


func _on_session_created(payload: Dictionary) -> void:
	$VBox/Narrative.text += "session_id: %s\n" % payload.get("session_id", "?")
	_set_play_buttons(true)
	await ApiClient.fetch_world_maps()


func _on_explore_2d_pressed() -> void:
	if _session_busy or ApiClient.session_id.is_empty():
		return
	get_tree().change_scene_to_file("res://scenes/exploration.tscn")


func _on_skill_tree_pressed() -> void:
	if _session_busy or ApiClient.session_id.is_empty():
		return
	get_tree().change_scene_to_file("res://scenes/skill_tree.tscn")


func _on_inventory_pressed() -> void:
	if _session_busy or ApiClient.session_id.is_empty():
		return
	get_tree().change_scene_to_file("res://scenes/inventory.tscn")


func _on_catalog_pressed() -> void:
	if _session_busy or ApiClient.session_id.is_empty():
		return
	get_tree().change_scene_to_file("res://scenes/item_catalog.tscn")


func _on_xr_world_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/xr/world_xr.tscn")


func _on_turn_completed(payload: Dictionary) -> void:
	for line in payload.get("lines", []):
		$VBox/Narrative.text += str(line) + "\n"
	var world: Dictionary = payload.get("world", {})
	$VBox/Hud.text = "Day %s · %s · 긴장 %s" % [
		world.get("day", "?"),
		payload.get("clock", world.get("time_of_day", "?")),
		world.get("tension", "?"),
	]


func _on_api_error(message: String) -> void:
	$VBox/Narrative.text += "\n[오류] %s\n" % message
	push_warning("API: %s" % message)
	_session_busy = false
	_set_play_buttons(true)


func _set_play_buttons(enabled: bool) -> void:
	$VBox/ExploreButton.disabled = not enabled
	$VBox/Explore2DButton.disabled = not enabled
	$VBox/SkillTreeButton.disabled = not enabled
	$VBox/InventoryButton.disabled = not enabled
	$VBox/CatalogButton.disabled = not enabled
