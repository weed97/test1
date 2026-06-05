extends Node
## API base URL — dev: local uvicorn; Steam: bundled server or ELDORIA_API_URL.

const API_VERSION := 1
const DEV_BASE_URL := "http://127.0.0.1:8765"


func base_url() -> String:
	var env := OS.get_environment("ELDORIA_API_URL")
	if env != "":
		return env.rstrip("/")
	return DEV_BASE_URL
