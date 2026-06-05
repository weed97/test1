# Cursor × Godot 4.6+ 연동

**가능합니다.** Godot 에디터(씬·애니·타일맵)와 Cursor(GDScript·문서·API·Python)를 **같은 폴더**로 열어 병행 작업하는 방식이 가장 효율적입니다.

## 프로젝트 위치

```
fantasy_simulator/client/godot/    ← Godot 4.6+ 프로젝트 (project.godot)
```

## 1. Godot 에디터

1. [Godot 4.6](https://godotengine.org/) 설치  
2. **Import** → `client/godot/project.godot` 선택  
3. **F5** 실행 전, 터미널에서 API 서버 실행:

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --reload --port 8765
```

4. 게임에서 **새 게임** → **탐험** → 서버 `lines` 가 텍스트창에 표시되면 연동 성공

## 2. Cursor

### 폴더 열기

| 방식 | 경로 | 용도 |
|------|------|------|
| **권장** | 레포 루트 `/workspace` | Python API + Godot + 설계 문서 한 번에 |
| Godot만 | `fantasy_simulator/client/godot` | 클라이언트 집중 |

### 확장 (권장)

Cursor는 VS Code 확장과 호환됩니다.

1. Extensions → **Godot Tools** (`geequlim.godot-tools`) 설치  
2. `client/godot/.vscode/settings.json` 에 Godot 실행 파일 경로 설정:

```json
"godot_tools.editor_path": "/usr/bin/godot4"
```

(Windows 예: `C:\\Program Files\\Godot\\Godot_v4.6-stable_win64.exe`)

3. Godot 에디터에서 **Editor → Editor Settings → Network → Language Server → Enable**  
4. Cursor에서 `.gd` 파일 열면 자동완성·정의로 이동 (LSP)

> LSP가 안 붙으면: Godot를 한 번 실행한 뒤 Cursor 재시작. 클라우드 VM에는 Godot 바이너리가 없을 수 있음 — **로컬 PC**에서 에디터+LSP, Cursor는 **원격/SSH**로 스크립트만 편집해도 됨.

## 3. 일하는 패턴 (추천)

| 작업 | 도구 |
|------|------|
| 씬·UI·노드 트리 | Godot Editor |
| `api_client.gd`, HUD 스크립트 | Cursor |
| `api/server.py`, 밸런스 JSON | Cursor |
| 실행 테스트 | Godot F5 + 터미널 uvicorn |
| Steam Export | Godot Export (+ 서버 번들) |

**같은 Git 브랜치**에서 커밋 — Godot가 씬 저장하면 Cursor에 바로 반영.

## 4. Cloud Agent / Cursor Background Agent

- Agent는 **GDScript·tscn·Python API** 수정 가능  
- Godot **GUI 실행·F5 테스트**는 보통 **사용자 로컬**에서  
- Agent 터미널에서 `uvicorn` + API 단위 테스트는 가능 (`tests/test_api_server.py`)

## 5. 주의

- `.godot/` 캐시는 git 제외 (이미 `.gitignore`)  
- `tscn` 충돌 시 Godot 쪽에서 다시 저장하거나 한쪽만 편집  
- 규칙·스토리 로직은 **Python에만** — Cursor에서 GDScript에 전투 공식 복제하지 않기  

## 관련 문서

- [STEAM_GODOT.md](STEAM_GODOT.md)  
- [design/15_GODOT_RELEASE_ARCHITECTURE.md](design/15_GODOT_RELEASE_ARCHITECTURE.md)  
- [client/godot/README.md](../client/godot/README.md)
