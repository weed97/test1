# Steam + Godot 출시 가이드

에르도리아: **Godot = 그래픽·입력**, **Python API = 게임 규칙·저장·스토리**.

## 아키텍처 (한 장)

```
[Steam 플레이어]
      │
      ▼
Godot 4 (eldoria-godot) ──HTTP──► Python API (이 레포)
      │                              GameSession.run_turn()
      │                              state/ · events/ · combat
      ▼
  렌더·UI·사운드만              LLM은 서버 전용 (선택)
```

상세: [design/15_GODOT_RELEASE_ARCHITECTURE.md](design/15_GODOT_RELEASE_ARCHITECTURE.md)

## 1. 로컬 개발 (지금 바로)

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --reload --host 127.0.0.1 --port 8765
```

다른 터미널:

```bash
curl -s http://127.0.0.1:8765/v1/health
curl -s -X POST http://127.0.0.1:8765/v1/session/new -H 'Content-Type: application/json' -d '{"seed":42,"temporal_mode":"precision"}'
# session_id 를 넣어서
curl -s -X POST http://127.0.0.1:8765/v1/turn -H 'Content-Type: application/json' -d '{"session_id":"...","action":"explore"}'
```

## 2. Godot 프로젝트

`client/godot/README.md` 참고. 핵심:

- Project Settings → HTTP Allow → `127.0.0.1:8765` (개발)
- `api_client.gd` 가 `POST /v1/turn` 호출
- `lines[]` → 대사 라벨 / 타이핑 연출
- `world.tension`, `clock` → HUD

**출시 빌드**에는 `API_BASE_URL` 을 환경별로:

| 빌드 | URL |
|------|-----|
| 개발 | `http://127.0.0.1:8765` |
| Steam (싱글) | `http://127.0.0.1:8765` + **게임과 함께 번들된 로컬 서버** |
| Steam (온라인) | `https://api.yourdomain.com` |

### Steam 싱글플레이 권장

Godot exe 옆에 `eldoria-server/` 를 두고, 시작 시 Godot이 **자식 프로세스**로 `uvicorn` 실행 (또는 PyInstaller로 `eldoria-server.exe` 하나로 패킹).

플레이어는 Python을 설치할 필요 없음.

## 3. Steamworks 체크리스트

| 항목 | 메모 |
|------|------|
| App ID | Steamworks에서 생성 |
| Godot export | Windows x86_64 먼저 |
| Depots | Godot PCK + server 바이너리 |
| Steam API | GodotSteam 등 — 업적·클라우드 세이브는 **서버 session_id** 와 매핑 |
| 클라우드 세이브 | `api_sessions/{id}/state/` zip 업로드 또는 자체 세이브 API |
| 오프라인 | MVP: 로컬 서버 필수. 완전 오프라인은 GDScript 미러 (장기) |
| EULA / 개인정보 | LLM 사용 시 서버 로그 정책 명시 |

## 4. Godot 씬 최소 세트 (MVP)

1. `main_menu` — 새 게임 → `POST /v1/session/new`
2. `exploration` — Explore 버튼 → `/v1/turn`
3. `hud` — `world`, `gold`, `clock`
4. `combat` — `combat_start` / 전투 턴
5. (2차) `camp`, `workshop`

## 5. 서버 배포 (온라인 샤드)

- Docker: `fantasy_simulator` + uvicorn, 볼륨 `api_sessions/`
- HTTPS 리버스 프록시 (CORS: Steam 빌드 origin)
- `mode=rule` 기본 — LLM 키는 서버 환경변수만

## 6. 다음 구현 순서

| # | 작업 |
|---|------|
| G0 | ✅ FastAPI `/v1/turn` |
| G1 | Godot 빈 프로젝트 + `api_client.gd` |
| G2 | combat 씬 바인딩 |
| G3 | Steam export + 서버 번들 스크립트 |
| G4 | Steamworks 업적 1개 (첫 탐험) |

## 테스트

```bash
pip install -r requirements-api.txt
python3 -m unittest tests.test_api_server -v
```
