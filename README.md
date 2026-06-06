# weed97/test1 — 판타지 시뮬레이터 모노레포

이 저장소의 **메인 프로젝트**는 `fantasy_simulator/` (Eldoria — Python API + Godot 클라이언트)입니다.

## 빠른 실행 (Eldoria)

```bash
cd fantasy_simulator
pip install -r requirements-api.txt
uvicorn api.server:app --port 8765

# 검증 (268 tests + API smoke)
bash scripts/verify.sh
```

Godot 4: `fantasy_simulator/client/godot/project.godot` 열기 → 메인 메뉴에서 **새 게임** (API 서버 필수).

## 포함 프로젝트

| 경로 | 설명 | 실행 |
|------|------|------|
| `fantasy_simulator/` | Eldoria 본편 — ecology/hybrid, 스킬트리, Godot 2D | `uvicorn api.server:app` |
| `data/items.json` + `index.html` | 중세 판타지 **아이템 도감** 웹앱 | `python3 -m http.server 8000` |
| `sungjwa_hunter_sim/` | 성좌 헌터 외부 시뮬레이터 | `python sungjwa_hunter_sim/main.py` |
| `mmorpg_sim/` | 텍스트 MMORPG 시뮬 | `python -m mmorpg_sim.cli --name Arin` |
| `fantasy_mmorpg/` | 판타지 MMORPG 텍스트 엔진 | `pip install -e fantasy_mmorpg && pytest` |
| `src/` (루트) | 중세 판타지 JS 시뮬레이터 | `npm test` (package.json) |

## 아이템 도감

```bash
python3 -m http.server 8000
# http://localhost:8000
```

## 세계관 — 잿빛 왕관의 노래

아르벨론 왕국 배경 로어. Eldoria 애쉬포인트·실버우드와 연결됩니다.  
→ `docs/world/ash_crown_setting.md`

## 개발

클라우드 에이전트: `AGENTS.md`
