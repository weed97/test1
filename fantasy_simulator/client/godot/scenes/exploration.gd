extends Node2D


@onready var _player: CharacterBody2D = $Player
@onready var _hud: Label = $CanvasLayer/HUD
@onready var _narrative: RichTextLabel = $CanvasLayer/Narrative
@onready var _zone_label: Label = $CanvasLayer/ZoneLabel
@onready var _agents_layer: Node2D = $AgentsLayer


func _ready() -> void:
	add_to_group("exploration_root")
	if ApiClient.session_id.is_empty():
		get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
		return
	_setup_collision()
	_setup_camera()
	ApiClient.turn_completed.connect(_on_turn_completed)
	ApiClient.position_synced.connect(_on_position_synced)
	ApiClient.api_error.connect(_on_api_error)
	ApiClient.agents_loaded.connect(_on_agents_loaded)
	await ApiClient.fetch_world_maps()
	_apply_map_bounds(ApiClient.sim_map_id)
	_apply_map_theme(ApiClient.sim_map_id)
	_player.position = Vector2(ApiClient.sim_tile) * ApiClient.tile_pixels + Vector2(8, 8)
	_update_hud({})
	var ok: bool = await ApiClient.sync_position(
		ApiClient.sim_map_id,
		ApiClient.sim_tile.x,
		ApiClient.sim_tile.y,
		ApiClient.sim_facing,
	)
	if ok:
		await ApiClient.fetch_world_agents(ApiClient.sim_map_id)


func _setup_camera() -> void:
	var cam: Camera2D = _player.get_node_or_null("Camera2D") as Camera2D
	if cam == null:
		cam = Camera2D.new()
		cam.name = "Camera2D"
		_player.add_child(cam)
	cam.make_current()


func _setup_collision() -> void:
	var player_shape := RectangleShape2D.new()
	player_shape.size = Vector2(14, 14)
	_player.get_node("CollisionShape2D").shape = player_shape


func _apply_map_bounds(mid: String) -> void:
	var m: Dictionary = ApiClient.world_maps.get(mid, {})
	var tw := int(m.get("width", 80)) * ApiClient.tile_pixels
	var th := int(m.get("height", 60)) * ApiClient.tile_pixels
	$Background.size = Vector2(tw, th)
	var wall_w := RectangleShape2D.new()
	wall_w.size = Vector2(tw, 16)
	var wall_h := RectangleShape2D.new()
	wall_h.size = Vector2(16, th)
	$Bounds/WallTop.position = Vector2(tw * 0.5, -8)
	$Bounds/WallBottom.position = Vector2(tw * 0.5, th + 8)
	$Bounds/WallTop.shape = wall_w
	$Bounds/WallBottom.shape = wall_w
	if not $Bounds.has_node("WallLeft"):
		var wl := CollisionShape2D.new()
		wl.name = "WallLeft"
		$Bounds.add_child(wl)
	if not $Bounds.has_node("WallRight"):
		var wr := CollisionShape2D.new()
		wr.name = "WallRight"
		$Bounds.add_child(wr)
	$Bounds/WallLeft.position = Vector2(-8, th * 0.5)
	$Bounds/WallRight.position = Vector2(tw + 8, th * 0.5)
	$Bounds/WallLeft.shape = wall_h
	$Bounds/WallRight.shape = wall_h


func on_map_changed(_payload: Dictionary) -> void:
	_apply_map_bounds(ApiClient.sim_map_id)
	_apply_map_theme(ApiClient.sim_map_id)
	_zone_label.text = "구역: %s" % ApiClient.sim_map_id
	await ApiClient.fetch_world_agents(ApiClient.sim_map_id)


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
	var ok: bool = await ApiClient.run_turn("explore", "precision", true)
	if ok:
		await ApiClient.fetch_world_agents(ApiClient.sim_map_id)


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


func _on_agents_loaded(payload: Dictionary) -> void:
	for child in _agents_layer.get_children():
		child.queue_free()
	var agents: Array = payload.get("agents", [])
	for agent in agents:
		if not agent is Dictionary:
			continue
		var marker := Polygon2D.new()
		var kind: String = str(agent.get("kind", "monster"))
		marker.color = Color(1.0, 0.35, 0.3) if kind == "monster" else Color(0.9, 0.85, 0.4)
		marker.polygon = PackedVector2Array([
			Vector2(-6, -6), Vector2(6, -6), Vector2(6, 6), Vector2(-6, 6)
		])
		var tx := int(agent.get("x", 0))
		var ty := int(agent.get("y", 0))
		marker.position = Vector2(tx, ty) * ApiClient.tile_pixels + Vector2(8, 8)
		marker.tooltip_text = str(agent.get("label", agent.get("instance_id", "")))
		_agents_layer.add_child(marker)


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


func _on_inventory_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/inventory.tscn")


func _on_catalog_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/item_catalog.tscn")


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
