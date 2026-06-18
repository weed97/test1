# weed97/test1 — 판타지 시뮬레이터 모노레포

이 저장소의 **메인 프로젝트**는 `fantasy_simulator/` (Eldoria — Python API + Godot 클라이언트)입니다.

## 빠른 실행 (Eldoria)

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --port 8765
bash scripts/verify.sh
```

Godot 4: `fantasy_simulator/client/godot/project.godot` → **새 게임** (API 서버 필수).

## 포함 프로젝트

| 경로 | 설명 | 실행 |
|------|------|------|
| `fantasy_simulator/` | Eldoria 본편 | `uvicorn api.server:app` |
| `item_catalog/` | 아이템 도감 웹앱 | `cd item_catalog && python3 -m http.server 8000` |
| `sungjwa_hunter_sim/` | 성좌 헌터 시뮬 | `python sungjwa_hunter_sim/main.py` |
| **CPoW 3D** (`cpow_engine/`, `cpow_api/`, `cpow_client/`) | 창조 시뮬 (Eldoria와 분리) | → [README_CPOW.md](README_CPOW.md) · **독립 브랜치** [`cpow-world`](https://github.com/weed97/test1/tree/cpow-world) |
| `mmorpg_sim/` | 텍스트 MMORPG | `python -m mmorpg_sim.cli --name Arin` |
| `fantasy_mmorpg/` | 판타지 MMORPG 엔진 | `python -m fantasy_mmorpg.cli` |
| `js_medieval_sim/` | JS 중세 판타지 시뮬 | `cd js_medieval_sim && npm test` |

## 세계관

→ `docs/world/ash_crown_setting.md` (잿빛 왕관의 노래)

## 개발

`AGENTS.md`
