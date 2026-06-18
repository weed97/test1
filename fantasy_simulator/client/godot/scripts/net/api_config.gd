extends Node
## API base URL — dev: local uvicorn; Steam: bundled server or ELDORIA_API_URL.

const API_VERSION := 1
const DEV_BASE_URL := "http://127.0.0.1:8765"
const QUEST_DEFAULT_LAN_API := "http://192.168.1.100:8765"
const CREATOR_ID := "godot_xr_player"
const XR_AUTO_SESSION := true
const QUEST_API_URL_FILE := "user://api_url.txt"


func base_url() -> String:
	var env := OS.get_environment("ELDORIA_API_URL")
	if env != "":
		return env.rstrip("/")
	if _load_quest_api_url() != "":
		return _load_quest_api_url()
	if OS.get_name() == "Android":
		return QUEST_DEFAULT_LAN_API
	return DEV_BASE_URL


func _load_quest_api_url() -> String:
	if not FileAccess.file_exists(QUEST_API_URL_FILE):
		return ""
	var text := FileAccess.get_file_as_string(QUEST_API_URL_FILE).strip_edges()
	if text.is_empty() or not text.begins_with("http"):
		return ""
	return text.rstrip("/")


func creator_id() -> String:
	var env := OS.get_environment("CPOW_CREATOR_ID")
	if env != "":
		return env
	return CREATOR_ID


func xr_device_type() -> String:
	if OS.get_environment("XR_DEVICE_TYPE") != "":
		return OS.get_environment("XR_DEVICE_TYPE")
	if OS.get_name() == "Android":
		return "quest3"
	if OS.has_feature("xr"):
		return "pcvr"
	return "simulator"


func xr_device_dict() -> Dictionary:
	return {
		"device_type": xr_device_type(),
		"tracking": "6dof",
		"hand_tracking": true,
		"session_id": "",
	}


var xr_auto_session: bool:
	get:
		return XR_AUTO_SESSION
