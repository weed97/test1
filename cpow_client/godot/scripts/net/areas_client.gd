extends Node
## HTTP bridge to /v1/areas/* — CPoW collaborative worlds (not Eldoria turn loop).

signal area_list_loaded(payload: Dictionary)
signal area_state_loaded(payload: Dictionary)
signal area_created(payload: Dictionary)
signal area_joined(payload: Dictionary)
signal area_found(payload: Dictionary)
signal api_error(message: String)

var current_area_id: String = ""
var current_user_id: String = ""
var last_area: Dictionary = {}
var last_state: Dictionary = {}

var _http_busy: bool = false


func _ready() -> void:
	current_user_id = AreasConfig.creator_id()


func set_user_id(user_id: String) -> void:
	current_user_id = user_id if not user_id.is_empty() else AreasConfig.creator_id()


func health_check() -> bool:
	var parsed := await _request("/v1/health", {}, HTTPClient.METHOD_GET)
	return parsed != null and parsed.get("status") == "ok"


func list_areas() -> Dictionary:
	var parsed := await _request("/v1/areas/list", {}, HTTPClient.METHOD_GET)
	if parsed != null:
		area_list_loaded.emit(parsed)
	return parsed if parsed != null else {}


func found_area(label: String, mode: String = "creation_adventure", template: String = "") -> Dictionary:
	var body := {
		"founder_id": current_user_id,
		"label": label,
		"mode": mode,
	}
	if not template.is_empty():
		body["template"] = template
	var parsed := await _request("/v1/areas/found", body)
	if parsed != null and parsed.get("ok"):
		var area: Dictionary = parsed.get("area", {})
		current_area_id = str(area.get("area_id", ""))
		last_area = area
		area_found.emit(parsed)
	return parsed if parsed != null else {}


func join_area(area_id: String, role: String = "") -> Dictionary:
	var body := {
		"area_id": area_id,
		"creator_id": current_user_id,
	}
	if not role.is_empty():
		body["role"] = role
	var parsed := await _request("/v1/areas/join", body)
	if parsed != null and parsed.get("ok"):
		current_area_id = area_id
		last_area = parsed.get("area", {})
		area_joined.emit(parsed)
	return parsed if parsed != null else {}


func fetch_state(area_id: String = "") -> Dictionary:
	var aid := area_id if not area_id.is_empty() else current_area_id
	if aid.is_empty():
		api_error.emit("no area selected")
		return {}
	var parsed := await _request(
		"/v1/areas/state?area_id=%s" % aid.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)
	if parsed != null and parsed.get("ok"):
		last_area = parsed.get("area", last_area)
		last_state = parsed.get("state", {})
		area_state_loaded.emit(parsed)
	return parsed if parsed != null else {}


func create_object(
	payload: Dictionary,
	area_id: String = "",
) -> Dictionary:
	var aid := area_id if not area_id.is_empty() else current_area_id
	if aid.is_empty():
		api_error.emit("no area selected")
		return {}
	var body := payload.duplicate(true)
	body["area_id"] = aid
	body["creator_id"] = current_user_id
	var parsed := await _request("/v1/areas/create", body)
	if parsed != null:
		if parsed.get("area"):
			last_area = parsed.get("area", last_area)
		area_created.emit(parsed)
	return parsed if parsed != null else {}


func create_heat(label: String = "열원", heat: float = 80.0) -> Dictionary:
	return await create_object({
		"type": "heat",
		"label": label,
		"heat_intensity": heat,
	})


func create_with_visual(
	label: String,
	glb_url: String,
	slot: String = "world_prop",
	attach_bone: String = "",
	extra_props: Array = [],
) -> Dictionary:
	var properties: Array = extra_props.duplicate()
	properties.append({"name": "visual_glb_url", "value": 1.0, "unit": glb_url})
	if not slot.is_empty():
		properties.append({"name": "visual_slot", "value": 1.0, "unit": slot})
	if not attach_bone.is_empty():
		properties.append({"name": "visual_attach_bone", "value": 1.0, "unit": attach_bone})
	return await create_object({
		"object": {
			"creator_id": current_user_id,
			"label": label,
			"properties": properties,
			"visual": {
				"glb_url": glb_url,
				"slot": slot,
				"attach_bone": attach_bone,
			},
		},
	})


func fetch_siege(attacker_area_id: String, defender_area_id: String) -> Dictionary:
	return await _request(
		"/v1/areas/siege?attacker_area_id=%s&defender_area_id=%s" % [
			attacker_area_id.uri_encode(),
			defender_area_id.uri_encode(),
		],
		{},
		HTTPClient.METHOD_GET,
	)


func fetch_active_sieges(area_id: String = "") -> Dictionary:
	var aid := area_id if not area_id.is_empty() else current_area_id
	return await _request(
		"/v1/areas/siege/active?area_id=%s" % aid.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)


func repulse_siege(
	attacker_area_id: String,
	defender_area_id: String,
	power_spend: float = 15.0,
) -> Dictionary:
	return await _request("/v1/areas/siege/repulse", {
		"attacker_area_id": attacker_area_id,
		"defender_area_id": defender_area_id,
		"actor_id": current_user_id,
		"power_spend": power_spend,
	})


func cross_destroy(
	target_area_id: String,
	object_id: String,
	home_area_id: String = "",
) -> Dictionary:
	var aid := home_area_id if not home_area_id.is_empty() else current_area_id
	return await _request("/v1/areas/cross_destroy", {
		"attacker_area_id": aid,
		"target_area_id": target_area_id,
		"actor_id": current_user_id,
		"object_id": object_id,
	})


func register_identity(person_key: String) -> Dictionary:
	return await _request("/v1/identity/register", {
		"user_id": current_user_id,
		"person_key": person_key,
	})


func identity_status() -> Dictionary:
	return await _request(
		"/v1/identity/status?user_id=%s" % current_user_id.uri_encode(),
		{},
		HTTPClient.METHOD_GET,
	)


func _request(path: String, body: Dictionary, method: int = HTTPClient.METHOD_POST) -> Variant:
	while _http_busy:
		await get_tree().process_frame
	_http_busy = true
	var result: Variant = await _request_impl(path, body, method)
	_http_busy = false
	return result


func _request_impl(path: String, body: Dictionary, method: int) -> Variant:
	var url := AreasConfig.base_url() + path
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

	var req_result: int = args[0]
	var code: int = args[1]
	var raw: PackedByteArray = args[3]
	if req_result != HTTPRequest.RESULT_SUCCESS:
		api_error.emit("network error: %s" % req_result)
		return null
	if code < 200 or code >= 300:
		var err_text := raw.get_string_from_utf8()
		api_error.emit("HTTP %s: %s" % [code, err_text])
		return null

	var text := raw.get_string_from_utf8()
	if text.is_empty() and method == HTTPClient.METHOD_GET:
		return {}
	var parsed = JSON.parse_string(text)
	if parsed == null:
		api_error.emit("invalid JSON from server")
		return null
	return parsed
