# Eldoria — Godot 4 클라이언트 (Steam)

Python 시뮬레이션 API에 붙는 **그래픽 전용** 클라이언트입니다.  
규칙·RNG·스토리 진행은 서버가 처리합니다.

## 새 프로젝트

1. Godot 4.2+ → New Project → `eldoria-godot`
2. Autoload: `ApiClient` → `res://scripts/net/api_client.gd`
3. Main scene: `res://scenes/main_menu.tscn`

## API 주소

`scripts/net/api_config.gd`:

```gdscript
extends Node
class_name ApiConfig

const API_VERSION := 1
const DEV_BASE_URL := "http://127.0.0.1:8765"

static func base_url() -> String:
    # Steam 출시: OS.get_environment("ELDORIA_API_URL") 또는 번들 로컬 서버
    var env := OS.get_environment("ELDORIA_API_URL")
    if env != "":
        return env.rstrip("/")
    return DEV_BASE_URL
```

## api_client.gd (핵심)

```gdscript
extends Node
class_name ApiClient

signal turn_completed(payload: Dictionary)
signal api_error(message: String)

var session_id: String = ""

func new_game(seed: int = -1, temporal_mode: String = "precision") -> void:
    var body := {"mode": "rule", "temporal_mode": temporal_mode}
    if seed >= 0:
        body["seed"] = seed
    var err := await _post_json("/v1/session/new", body, _on_new_session)
    if err:
        api_error.emit(err)

func run_turn(action: String) -> void:
    if session_id == "":
        api_error.emit("no session")
        return
    var body := {
        "session_id": session_id,
        "action": action,
        "temporal_mode": "precision",
    }
    var err := await _post_json("/v1/turn", body, _on_turn)
    if err:
        api_error.emit(err)

func _on_new_session(data: Dictionary) -> void:
    session_id = data.get("session_id", "")

func _on_turn(data: Dictionary) -> void:
    turn_completed.emit(data)

func _post_json(path: String, body: Dictionary, callback: Callable) -> String:
    var url := ApiConfig.base_url() + path
    var http := HTTPRequest.new()
    add_child(http)
    var json := JSON.stringify(body)
    var headers := ["Content-Type: application/json"]
    var err := http.request(url, headers, HTTPClient.METHOD_POST, json)
    if err != OK:
        http.queue_free()
        return "request failed: %s" % err
    var args = await http.request_completed
    http.queue_free()
    var result: int = args[0]
    var code: int = args[1]
    var raw: PackedByteArray = args[3]
    if result != HTTPRequest.RESULT_SUCCESS or code < 200 or code >= 300:
        return "http %s" % code
    var parsed = JSON.parse_string(raw.get_string_from_utf8())
    if parsed == null:
        return "invalid json"
    callback.call(parsed)
    return ""
```

## exploration 씬 예시

```gdscript
func _on_explore_pressed() -> void:
    $ApiClient.run_turn("explore")

func _on_api_turn_completed(payload: Dictionary) -> void:
    for line in payload.get("lines", []):
        $NarrativeLog.append_text(line + "\n")
    var w: Dictionary = payload.get("world", {})
    $HUD/Tension.text = "긴장 %d" % int(w.get("tension", 0))
    if payload.has("clock"):
        $HUD/Clock.text = str(payload["clock"])
```

## 서버 실행 (개발)

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --reload --port 8765
```

## Steam 번들

Export된 게임 폴더에 `server/eldoria-server.exe` (PyInstaller) 포함 후,  
`main_menu.gd`에서 `OS.create_process()` 로 기동 → 2초 후 `new_game()`.

자세한 체크리스트: [../../docs/STEAM_GODOT.md](../../docs/STEAM_GODOT.md)
