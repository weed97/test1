extends Node
## CPoW areas API — separate from Eldoria fantasy_simulator /v1/turn.

const API_VERSION := 1
const DEV_BASE_URL := "http://127.0.0.1:8765"
const QUEST_API_URL_FILE := "user://cpow_api_url.txt"
const DEFAULT_CREATOR_ID := "cpow_player"


func base_url() -> String:
	var env := OS.get_environment("CPOW_API_URL")
	if env != "":
		return env.rstrip("/")
	if FileAccess.file_exists(QUEST_API_URL_FILE):
		var text := FileAccess.get_file_as_string(QUEST_API_URL_FILE).strip_edges()
		if text.begins_with("http"):
			return text.rstrip("/")
	return DEV_BASE_URL


func creator_id() -> String:
	var env := OS.get_environment("CPOW_CREATOR_ID")
	if env != "":
		return env
	return DEFAULT_CREATOR_ID
