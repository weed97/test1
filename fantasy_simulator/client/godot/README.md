# CPoW XR — Godot 4.6+ 클라이언트

OpenXR(Meta Quest) + 데스크톱 시뮬레이터. Python CPoW API = 물리·가치 산정 권위.

## 빠른 시작 (데스크톱)

1. **API 서버**:

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --reload --port 8765
```

2. **Godot 4.6+** → `project.godot` → F5 → **CPoW XR 월드**

## Meta Quest APK

→ **[docs/QUEST_APK_BUILD.md](docs/QUEST_APK_BUILD.md)** (전체 가이드)

```bash
cd fantasy_simulator/client/godot
cp export_presets.quest.cfg export_presets.cfg
GODOT_BIN=/path/to/godot bash scripts/build_quest_apk.sh
adb install -r build/cpow-quest.apk
```

Quest는 PC API에 LAN으로 접속: `uvicorn api.server:app --host 0.0.0.0 --port 8765`

## 구조

```
client/godot/
  scenes/boot.tscn           # Android→XR / Desktop→메뉴
  scenes/xr/world_xr.tscn  # CPoW XR 창조 월드
  export_presets.quest.cfg # Quest Export 템플릿
  scripts/build_quest_apk.sh
  docs/QUEST_APK_BUILD.md
  docs/XR_SETUP.md
```

## 자주 보는 오류 (원인)

| 증상 | 원인 | 해결 |
|------|------|------|
| `HTTP 404: session not found` | Godot만 실행, 세션 없음 | 메인 메뉴 **새 게임** 먼저 |
| `연결 실패` / `network error` | API 서버 미실행 | 아래 uvicorn 실행 |
| `ecology or hybrid mode required` | 구버전 story 세션 | **새 게임** (hybrid 자동) |
| 스킬 트리 빈 화면 | API 꺼짐 또는 세션 만료 | 서버 + 새 게임 |

검증: `bash scripts/verify.sh` (Python 테스트 + API 스모크)

## 빠른 시작

1. **API 서버** (다른 터미널):

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --reload --port 8765
```

2. **Godot 4.6+** → Import → 이 폴더의 `project.godot` → F5

3. **Cursor** → 레포 루트 또는 이 폴더 열기 → [docs/CURSOR_GODOT.md](../../docs/CURSOR_GODOT.md)

## 구조

```
client/godot/
  project.godot
  scenes/main_menu.tscn      # 새 게임 → 2D 탐험
  scenes/exploration.tscn   # WASD + 타일 ↔ 시뮬 좌표
  scenes/inventory.tscn     # 인벤 · 착용/사용
  scenes/item_catalog.tscn  # 아이템 도감 (213+)
  scripts/net/api_client.gd # sync_position, run_turn
  scripts/player/player_controller.gd
```

**좌표 연동:** 이동 시 `POST /v1/world/position` · 탐험 시 `POST /v1/turn` + position.  
설계: `docs/design/19_SPATIAL_SIMULATION.md`

## Cursor 연동

- 확장: **Godot Tools** (`geequlim.godot-tools`)
- `.vscode/settings.json` 에 `godot_tools.editor_path` 설정
- GDScript는 Cursor에서 편집, 씬·노드는 Godot 에디터에서 편집

## Steam

[docs/STEAM_GODOT.md](../../docs/STEAM_GODOT.md)
