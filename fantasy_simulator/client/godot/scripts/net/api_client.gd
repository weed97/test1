extends Node
## HTTP bridge to fantasy_simulator/api/server.py (simulation authority).

signal turn_completed(payload: Dictionary)
signal session_created(payload: Dictionary)
signal api_error(message: String)

var session_id: String = ""


func new_game(seed: int = -1, temporal_mode: String = "precision") -> void:
	var body := {"mode": "rule", "temporal_mode": temporal_mode}
	if seed >= 0:
		body["seed"] = seed
	var parsed := await _post_json("/v1/session/new", body)
	if parsed == null:
		return
	session_id = str(parsed.get("session_id", ""))
	session_created.emit(parsed)


func run_turn(action: String, temporal_mode: String = "precision") -> void:
	if session_id.is_empty():
		api_error.emit("no session — call new_game() first")
		return
	var body := {
		"session_id": session_id,
		"action": action,
		"temporal_mode": temporal_mode,
	}
	var parsed := await _post_json("/v1/turn", body)
	if parsed == null:
		return
	turn_completed.emit(parsed)


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
