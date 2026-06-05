extends Control


func _ready() -> void:
	ApiClient.session_created.connect(_on_session_created)
	ApiClient.turn_completed.connect(_on_turn_completed)
	ApiClient.api_error.connect(_on_api_error)
	$VBox/ServerLabel.text = "API: %s" % ApiConfig.base_url()
	_check_server()


func _check_server() -> void:
	var ok: bool = await ApiClient.health_check()
	$VBox/ServerLabel.text = "API: %s (%s)" % [
		ApiConfig.base_url(),
		"연결됨" if ok else "서버 꺼짐 — uvicorn 실행 필요",
	]


func _on_new_game_pressed() -> void:
	$VBox/ExploreButton.disabled = true
	$VBox/SkillTreeButton.disabled = true
	$VBox/Narrative.clear()
	$VBox/Narrative.text = "세션 생성 중…\n"
	await ApiClient.new_game(42, "precision")


func _on_explore_pressed() -> void:
	$VBox/Narrative.text += "\n[탐험]\n"
	await ApiClient.run_turn("explore", "precision")


func _on_session_created(payload: Dictionary) -> void:
	$VBox/Narrative.text += "session_id: %s\n" % payload.get("session_id", "?")
	$VBox/ExploreButton.disabled = false
	$VBox/Explore2DButton.disabled = false
	$VBox/SkillTreeButton.disabled = false
	await ApiClient.fetch_world_maps()


func _on_explore_2d_pressed() -> void:
	if ApiClient.session_id.is_empty():
		return
	get_tree().change_scene_to_file("res://scenes/exploration.tscn")


func _on_skill_tree_pressed() -> void:
	if ApiClient.session_id.is_empty():
		return
	get_tree().change_scene_to_file("res://scenes/skill_tree.tscn")


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
