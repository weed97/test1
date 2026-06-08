extends Node
## HTTP bridge to fantasy_simulator/api/server.py (simulation authority).

signal turn_completed(payload: Dictionary)
signal session_created(payload: Dictionary)
signal position_synced(payload: Dictionary)
signal maps_loaded(payload: Dictionary)
signal agents_loaded(payload: Dictionary)
signal api_error(message: String)
signal sim_tick_completed(payload: Dictionary)

var session_id: String = ""
var sim_clock_enabled: bool = false
var sim_realtime_scale: float = 12.0
var world_maps: Dictionary = {}
var sim_map_id: String = "ashpoint_01"
var sim_tile: Vector2i = Vector2i(40, 48)
var sim_facing: String = "south"
var tile_pixels: int = 16

var _http_busy: bool = false


func new_game(seed: int = -1, temporal_mode: String = "precision", game_mode: String = "hybrid") -> void:
	var body := {
		"mode": "rule",
		"temporal_mode": temporal_mode,
		"game_mode": game_mode,
		"player_race": "human",
	}
	if seed >= 0:
		body["seed"] = seed
	var parsed: Variant = await _post_json("/v1/session/new", body)
	if parsed == null:
		api_error.emit("session create failed")
		return
	session_id = str(parsed.get("session_id", ""))
	if session_id.is_empty():
		api_error.emit("session_id missing in response")
		return
	await fetch_sim_status()
	session_created.emit(parsed)


func fetch_world_maps() -> void:
	var parsed: Variant = await _post_json("/v1/world/maps", {}, HTTPClient.METHOD_GET)
	if parsed == null:
		return
	world_maps = parsed.get("maps", {})
	tile_pixels = int(parsed.get("godot_pixel_per_tile", 16))
	maps_loaded.emit(parsed)


func sync_position(
	map_id: String,
	x: int,
	y: int,
	facing: String = "south",
	allow_transition: bool = true,
) -> bool:
	if session_id.is_empty():
		api_error.emit("no session")
		return false
	var body := {
		"session_id": session_id,
		"position": {
			"map_id": map_id,
			"x": x,
			"y": y,
			"facing": facing,
			"allow_map_transition": allow_transition,
		},
	}
	var parsed: Variant = await _post_json("/v1/world/position", body)
	if parsed == null:
		return false
	if not parsed.get("ok", true):
		api_error.emit("position sync rejected")
		return false
	var pos: Dictionary = parsed.get("position", {})
	sim_map_id = str(pos.get("map_id", map_id))
	sim_tile = Vector2i(int(pos.get("x", x)), int(pos.get("y", y)))
	sim_facing = str(pos.get("facing", facing))
	position_synced.emit(parsed)
	return true


func run_turn(
	action: String,
	temporal_mode: String = "precision",
	at_position: bool = true,
) -> bool:
	if session_id.is_empty():
		api_error.emit("no session — call new_game() first")
		return false
	var body := {
		"session_id": session_id,
		"action": action,
		"temporal_mode": temporal_mode,
	}
	if at_position:
		body["position"] = {
			"map_id": sim_map_id,
			"x": sim_tile.x,
			"y": sim_tile.y,
			"facing": sim_facing,
			"allow_map_transition": false,
		}
	var parsed: Variant = await _post_json("/v1/turn", body)
	if parsed == null:
		return false
	_apply_position_from_payload(parsed)
	turn_completed.emit(parsed)
	return true


func _apply_position_from_payload(parsed: Dictionary) -> void:
	var pos: Dictionary = parsed.get("position", {})
	if pos.is_empty():
		return
	sim_map_id = str(pos.get("map_id", sim_map_id))
	sim_tile = Vector2i(int(pos.get("x", sim_tile.x)), int(pos.get("y", sim_tile.y)))
	sim_facing = str(pos.get("facing", sim_facing))


func fetch_progression_status() -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/progression/status?session_id=%s" % session_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	return parsed if parsed != null else {}


func fetch_skill_tree(character_id: String) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {"error": "no session"}
	var parsed: Variant = await _post_json(
		"/v1/progression/skill_tree?session_id=%s&character_id=%s" % [
			session_id.uri_encode(),
			character_id.uri_encode(),
		],
		{},
		HTTPClient.METHOD_GET,
	)
	if parsed == null:
		return {"error": "request failed"}
	return parsed.get("skill_tree", {})


func fetch_item_catalog(
	category: String = "",
	grade: String = "",
	search: String = "",
	limit: int = 200,
) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var path := "/v1/catalog/items?session_id=%s&limit=%d" % [session_id.uri_encode(), limit]
	if not category.is_empty():
		path += "&category=%s" % category.uri_encode()
	if not grade.is_empty():
		path += "&grade=%s" % grade.uri_encode()
	if not search.is_empty():
		path += "&q=%s" % search.uri_encode()
	var parsed: Variant = await _post_json(path, {}, HTTPClient.METHOD_GET)
	return parsed if parsed != null else {}


func equip_item(character_id: String, item_id: String) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/progression/equip",
		{
			"session_id": session_id,
			"character_id": character_id,
			"item_id": item_id,
		},
	)
	return parsed if parsed != null else {}


func grant_item(item_id: String, count: int = 1) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/progression/grant_item",
		{
			"session_id": session_id,
			"item_id": item_id,
			"count": count,
		},
	)
	return parsed if parsed != null else {}


func fetch_item_detail(item_id: String) -> Dictionary:
	var parsed: Variant = await _post_json(
		"/v1/catalog/items/%s" % item_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	if parsed == null:
		return {}
	return parsed.get("item", {})


func use_item(character_id: String, item_id: String) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/progression/use_item",
		{
			"session_id": session_id,
			"character_id": character_id,
			"item_id": item_id,
		},
	)
	return parsed if parsed != null else {}


func unlock_skill(character_id: String, skill_id: String) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/progression/unlock_skill",
		{
			"session_id": session_id,
			"character_id": character_id,
			"skill_id": skill_id,
		},
	)
	return parsed if parsed != null else {}


func cast_sovereign_wish(edict_type: String, extra: Dictionary = {}) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var body := {"session_id": session_id, "edict_type": edict_type}
	body.merge(extra, true)
	var parsed: Variant = await _post_json("/v1/sovereign/wish", body)
	return parsed if parsed != null else {}


func fetch_world_agents(map_id: String = "") -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var path := "/v1/world/agents?session_id=%s" % session_id.uri_encode()
	if not map_id.is_empty():
		path += "&map_id=%s" % map_id.uri_encode()
	var parsed: Variant = await _post_json(path, {}, HTTPClient.METHOD_GET)
	if parsed != null:
		agents_loaded.emit(parsed)
	return parsed if parsed != null else {}


func fetch_kingdom_status() -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/status?session_id=%s" % session_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	return parsed if parsed != null else {}


func fetch_kingdom_doctrines() -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/doctrines?session_id=%s" % session_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	return parsed if parsed != null else {}


func set_siege_command(
	war_id: String,
	doctrine: String,
	posture: String = "",
	side: String = "defender",
) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {"ok": false, "error": "no session"}
	var body := {
		"session_id": session_id,
		"war_id": war_id,
		"side": side,
		"doctrine": doctrine,
	}
	if not posture.is_empty():
		body["posture"] = posture
	var parsed: Variant = await _post_json("/v1/kingdom/war/command", body)
	return parsed if parsed != null else {"ok": false, "error": "request failed"}


func fetch_kingdom_commanders() -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/commanders?session_id=%s" % session_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	return parsed if parsed != null else {}


func fetch_kingdom_wars() -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/wars?session_id=%s" % session_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	return parsed if parsed != null else {}


func start_kingdom_founding(
	kingdom_name: String,
	doctrine_id: String,
	custom_decree: String = "",
	map_id: String = "",
	x: int = -1,
	y: int = -1,
) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var mid := map_id if not map_id.is_empty() else sim_map_id
	var tx := x if x >= 0 else sim_tile.x
	var ty := y if y >= 0 else sim_tile.y
	var parsed: Variant = await _post_json(
		"/v1/settlement/kingdom",
		{
			"session_id": session_id,
			"map_id": mid,
			"x": tx,
			"y": ty,
			"kingdom_name": kingdom_name,
			"doctrine_id": doctrine_id,
			"custom_decree": custom_decree,
		},
	)
	return parsed if parsed != null else {}


func set_kingdom_doctrine(doctrine_id: String, custom_decree: String = "") -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/doctrine",
		{
			"session_id": session_id,
			"doctrine_id": doctrine_id,
			"custom_decree": custom_decree,
		},
	)
	return parsed if parsed != null else {}


func fortify_kingdom(upgrade_type: String) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/fortify",
		{"session_id": session_id, "upgrade_type": upgrade_type},
	)
	return parsed if parsed != null else {}


func build_kingdom_interior(build_type: String) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/build_interior",
		{"session_id": session_id, "build_type": build_type},
	)
	return parsed if parsed != null else {}


func recruit_kingdom_military(unit_type: String, count: int = 1) -> Dictionary:
	if session_id.is_empty():
		api_error.emit("no session")
		return {}
	var parsed: Variant = await _post_json(
		"/v1/kingdom/recruit",
		{
			"session_id": session_id,
			"unit_type": unit_type,
			"count": count,
		},
	)
	return parsed if parsed != null else {}


func fetch_sim_status() -> Dictionary:
	if session_id.is_empty():
		return {}
	var parsed: Variant = await _post_json(
		"/v1/sim/status?session_id=%s" % session_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	if parsed == null:
		return {}
	var clock: Dictionary = parsed.get("sim_clock", {})
	sim_clock_enabled = bool(clock.get("enabled", false))
	sim_realtime_scale = float(clock.get("realtime_scale", 12.0))
	return parsed


func sim_tick(dt_real_ms: int) -> Dictionary:
	if session_id.is_empty():
		return {}
	if not sim_clock_enabled:
		return {}
	var parsed: Variant = await _post_json(
		"/v1/sim/tick",
		{
			"session_id": session_id,
			"dt_real_ms": clampi(dt_real_ms, 0, 30000),
		},
	)
	if parsed == null:
		return {}
	var clock: Dictionary = parsed.get("sim_clock", {})
	sim_clock_enabled = bool(clock.get("enabled", sim_clock_enabled))
	sim_realtime_scale = float(clock.get("realtime_scale", sim_realtime_scale))
	sim_tick_completed.emit(parsed)
	return parsed


func health_check() -> bool:
	var parsed: Variant = await _post_json("/v1/health", {}, HTTPClient.METHOD_GET)
	return parsed != null and parsed.get("status") == "ok"


func _post_json(path: String, body: Dictionary, method: int = HTTPClient.METHOD_POST) -> Variant:
	while _http_busy:
		await get_tree().process_frame
	_http_busy = true
	var result: Variant = await _post_json_impl(path, body, method)
	_http_busy = false
	return result


func _post_json_impl(path: String, body: Dictionary, method: int) -> Variant:
	var url := ApiConfig.base_url() + path
	var http := HTTPRequest.new()
	add_child(http)
	var body_text := "" if method == HTTPClient.METHOD_GET else JSON.stringify(body)
	var headers := PackedStringArray(["Content-Type: application/json"])
	var err := http.request(url, headers, method, body_text)
	if err != OK:
		http.queue_free()
		api_error.emit("request failed: %s" % error_string(err))
		return null

	var completed: Variant = await http.request_completed
	http.queue_free()
	if completed is not Array:
		api_error.emit("network error: invalid response")
		return null
	var args: Array = completed

	var req_result: int = int(args[0])
	var code: int = int(args[1])
	var raw: PackedByteArray = args[3]
	if req_result != HTTPRequest.RESULT_SUCCESS:
		api_error.emit("network error: %s" % req_result)
		return null
	if code < 200 or code >= 300:
		var err_text := raw.get_string_from_utf8()
		var detail := err_text
		var parsed_err = JSON.parse_string(err_text)
		if parsed_err is Dictionary and parsed_err.get("detail"):
			detail = str(parsed_err.get("detail"))
		api_error.emit("HTTP %s: %s" % [code, detail])
		return null

	var text := raw.get_string_from_utf8()
	if text.is_empty() and method == HTTPClient.METHOD_GET:
		return {}
	var parsed = JSON.parse_string(text)
	if parsed == null:
		api_error.emit("invalid JSON from server")
		return null
	return parsed
