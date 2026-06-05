extends Node
## HTTP bridge to fantasy_simulator/api/server.py (simulation authority).

signal turn_completed(payload: Dictionary)
signal session_created(payload: Dictionary)
signal position_synced(payload: Dictionary)
signal maps_loaded(payload: Dictionary)
signal api_error(message: String)

var session_id: String = ""
var world_maps: Dictionary = {}
var sim_map_id: String = "ashpoint_01"
var sim_tile: Vector2i = Vector2i(40, 48)
var sim_facing: String = "south"
var tile_pixels: int = 16


func new_game(seed: int = -1, temporal_mode: String = "precision") -> void:
	var body := {"mode": "rule", "temporal_mode": temporal_mode}
	if seed >= 0:
		body["seed"] = seed
	var parsed := await _post_json("/v1/session/new", body)
	if parsed == null:
		return
	session_id = str(parsed.get("session_id", ""))
	session_created.emit(parsed)


func fetch_world_maps() -> void:
	var parsed := await _post_json("/v1/world/maps", {}, HTTPClient.METHOD_GET)
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
) -> void:
	if session_id.is_empty():
		api_error.emit("no session")
		return
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
	var parsed := await _post_json("/v1/world/position", body)
	if parsed == null:
		return
	var pos: Dictionary = parsed.get("position", {})
	sim_map_id = str(pos.get("map_id", map_id))
	sim_tile = Vector2i(int(pos.get("x", x)), int(pos.get("y", y)))
	sim_facing = str(pos.get("facing", facing))
	position_synced.emit(parsed)


func run_turn(
	action: String,
	temporal_mode: String = "precision",
	at_position: bool = true,
) -> void:
	if session_id.is_empty():
		api_error.emit("no session — call new_game() first")
		return
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
	var parsed := await _post_json("/v1/turn", body)
	if parsed == null:
		return
	_apply_position_from_payload(parsed)
	turn_completed.emit(parsed)


func _apply_position_from_payload(parsed: Dictionary) -> void:
	var pos: Dictionary = parsed.get("position", {})
	if pos.is_empty():
		return
	sim_map_id = str(pos.get("map_id", sim_map_id))
	sim_tile = Vector2i(int(pos.get("x", sim_tile.x)), int(pos.get("y", sim_tile.y)))
	sim_facing = str(pos.get("facing", sim_facing))


func health_check() -> bool:
	var parsed := await _post_json("/v1/health", {}, HTTPClient.METHOD_GET)
	return parsed != null and parsed.get("status") == "ok"


func _post_json(path: String, body: Dictionary, method: int = HTTPClient.METHOD_POST) -> Variant:
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

	var args: Array = await http.request_completed
	http.queue_free()

	var result: int = args[0]
	var code: int = args[1]
	var raw: PackedByteArray = args[3]
	if result != HTTPRequest.RESULT_SUCCESS:
		api_error.emit("network error: %s" % result)
		return null
	if code < 200 or code >= 300:
		api_error.emit("HTTP %s: %s" % [code, raw.get_string_from_utf8()])
		return null

	var text := raw.get_string_from_utf8()
	if text.is_empty() and method == HTTPClient.METHOD_GET:
		return {}
	var parsed = JSON.parse_string(text)
	if parsed == null:
		api_error.emit("invalid JSON from server")
		return null
	return parsed
