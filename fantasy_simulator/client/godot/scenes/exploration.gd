extends Node2D


@onready var _player: CharacterBody2D = $Player
@onready var _hud: Label = $CanvasLayer/HUD
@onready var _narrative: RichTextLabel = $CanvasLayer/Narrative
@onready var _zone_label: Label = $CanvasLayer/ZoneLabel
@onready var _agents_layer: Node2D = $AgentsLayer

var _siege_battle: PanelContainer
var _sim_tick_accum: float = 0.0
var _sim_tick_busy: bool = false
const SIM_TICK_INTERVAL := 1.0


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
	ApiClient.sim_tick_completed.connect(_on_sim_tick_completed)
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
	_setup_siege_overlay()
	await _refresh_live_siege()


func _process(delta: float) -> void:
	if not ApiClient.sim_clock_enabled or _sim_tick_busy:
		return
	_sim_tick_accum += delta
	if _sim_tick_accum < SIM_TICK_INTERVAL:
		return
	var ms := int(_sim_tick_accum * 1000.0)
	_sim_tick_accum = 0.0
	_poll_sim_tick(ms)


func _poll_sim_tick(dt_ms: int) -> void:
	_sim_tick_busy = true
	var payload: Dictionary = await ApiClient.sim_tick(dt_ms)
	_sim_tick_busy = false
	if payload.is_empty():
		return
	_on_sim_tick_completed(payload)


func _on_sim_tick_completed(payload: Dictionary) -> void:
	_update_hud(payload)
	_sync_live_siege(payload)


func _setup_siege_overlay() -> void:
	var scene: PackedScene = load("res://scenes/siege_battle.tscn")
	if scene == null:
		return
	_siege_battle = scene.instantiate() as PanelContainer
	_siege_battle.visible = false
	$CanvasLayer.add_child(_siege_battle)
	_siege_battle.set_anchors_preset(Control.PRESET_CENTER)


func _sync_live_siege(payload: Dictionary) -> void:
	if _siege_battle == null:
		return
	var live: Dictionary = payload.get("siege_live", {})
	if not live is Dictionary or live.is_empty():
		return
	if not _siege_battle.visible:
		_siege_battle.open_live(live)
	else:
		_siege_battle.sync_live(live)
	var events: Array = payload.get("new_siege_events", [])
	if not events.is_empty():
		_siege_battle.pulse_events(events)


func _refresh_live_siege() -> void:
	var wars: Dictionary = await ApiClient.fetch_kingdom_wars()
	var live: Dictionary = wars.get("siege_live", {})
	if live is Dictionary and not live.is_empty():
		_sync_live_siege({"siege_live": live, "new_siege_events": []})


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
	_sync_live_siege(payload)


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
	var clock: Dictionary = payload.get("sim_clock", {})
	var time_str := "?"
	if world.has("minute_of_day"):
		var mod := int(world["minute_of_day"])
		time_str = "%02d:%02d" % [mod / 60, mod % 60]
	elif payload.has("clock"):
		time_str = str(payload.get("clock", "?"))
	var scale := float(clock.get("realtime_scale", ApiClient.sim_realtime_scale))
	_hud.text = "맵 %s · (%d,%d) · D%s %s · 긴장 %s · 시뮬×%.0f" % [
		ApiClient.sim_map_id,
		ApiClient.sim_tile.x,
		ApiClient.sim_tile.y,
		world.get("day", "?"),
		time_str,
		world.get("tension", "?"),
		scale,
	]
	if bool(payload.get("ecology_beat", false)):
		await ApiClient.fetch_world_agents(ApiClient.sim_map_id)


func _on_api_error(message: String) -> void:
	_narrative.text += "\n[오류] %s\n" % message


func _on_inventory_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/inventory.tscn")


func _on_catalog_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/item_catalog.tscn")


func _on_kingdom_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/kingdom.tscn")


func _on_back_pressed() -> void:
	get_tree().change_scene_to_file("res://scenes/main_menu.tscn")
