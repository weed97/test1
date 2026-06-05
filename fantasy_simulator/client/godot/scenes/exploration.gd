extends Node2D


@onready var _player: CharacterBody2D = $Player
@onready var _hud: Label = $CanvasLayer/HUD
@onready var _narrative: RichTextLabel = $CanvasLayer/Narrative
@onready var _zone_label: Label = $CanvasLayer/ZoneLabel


func _ready() -> void:
	add_to_group("exploration_root")
	if ApiClient.session_id.is_empty():
		get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
		return
	ApiClient.turn_completed.connect(_on_turn_completed)
	ApiClient.position_synced.connect(_on_position_synced)
	ApiClient.api_error.connect(_on_api_error)
	await ApiClient.fetch_world_maps()
	_apply_map_theme(ApiClient.sim_map_id)
	_update_hud({})
	await ApiClient.sync_position(
		ApiClient.sim_map_id,
		ApiClient.sim_tile.x,
		ApiClient.sim_tile.y,
		ApiClient.sim_facing,
	)


func on_map_changed(_payload: Dictionary) -> void:
	_apply_map_theme(ApiClient.sim_map_id)
	_zone_label.text = "구역: %s" % ApiClient.sim_map_id


func _apply_map_theme(mid: String) -> void:
	var maps: Dictionary = ApiClient.world_maps
	var m: Dictionary = maps.get(mid, {})
	var zone: String = str(m.get("zone_id", mid))
	_zone_label.text = "%s (%s)" % [m.get("display_name", mid), zone]
	match zone:
		"forest":
			$Background.color = Color(0.12, 0.22, 0.14)
		"tower":
			$Background.color = Color(0.18, 0.18, 0.24)
		_:
			$Background.color = Color(0.2, 0.17, 0.14)


func _on_explore_pressed() -> void:
	_narrative.text += "\n[탐험]\n"
	await ApiClient.run_turn("explore", "precision", true)


func _on_position_synced(payload: Dictionary) -> void:
	var pois: Array = payload.get("pois", [])
	if not pois.is_empty():
		var p: Dictionary = pois[0]
		_narrative.text += "\n[근처] %s\n" % p.get("label", "")
	_update_hud(payload)


func _on_turn_completed(payload: Dictionary) -> void:
	for line in payload.get("lines", []):
		_narrative.text += str(line) + "\n"
	_update_hud(payload)


func _update_hud(payload: Dictionary) -> void:
	var world: Dictionary = payload.get("world", {})
	_hud.text = "맵 %s · 타일 (%d,%d) · 긴장 %s" % [
		ApiClient.sim_map_id,
		ApiClient.sim_tile.x,
		ApiClient.sim_tile.y,
		world.get("tension", "?"),
	]


func _on_api_error(message: String) -> void:
	_narrative.text += "\n[오류] %s\n" % message


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
