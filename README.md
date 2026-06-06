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

| 경로 | 설명 |
|------|------|
| `fantasy_simulator/` | Eldoria 본편 — ecology/hybrid 시뮬, 스킬트리, Godot 2D |
| `data/items.json` + `index.html` | 중세 판타지 **아이템 도감** 웹앱 |
| `sungjwa_hunter_sim/` | 성좌 헌터 외부 시뮬레이터 (Python) |
| `mmorpg_sim/` | 텍스트 MMORPG 시뮬 스캐폴드 |
| `fantasy_mmorpg/` | 판타지 MMORPG 텍스트 엔진 |
| `src/` (루트) | 중세 판타지 JS 시뮬레이터 (브라우저) |

## 아이템 도감 실행

```bash
python3 -m http.server 8000
# http://localhost:8000
```

## 세계관 — 잿빛 왕관의 노래

**잿빛 왕관의 노래**는 오래된 왕국, 금지된 마법, 무너져 가는 기사도, 용의 핏줄을 둘러싼 중세 판타지 세계관입니다. 내전 직전의 왕국 **아르벨론**을 배경으로 사라진 왕관과 고대 저주를 추적합니다.

- **루멘폴 성도** · **그림바르크 산맥** · **은잎 숲** · **검은 방앗간 마을** · **세라크 항구**
- 세력: 태양십자 기사단, 백탑 마법사 길드, 황혼 교단, 붉은사슴 가문
- Eldoria(`fantasy_simulator`)의 애쉬포인트·실버우드는 이 세계관의 변경 지역으로 연결됩니다.

자세한 로어·시나리오는 `docs/world/ash_crown_setting.md` 참고.

## 개발

클라우드 에이전트 설정: `AGENTS.md`
