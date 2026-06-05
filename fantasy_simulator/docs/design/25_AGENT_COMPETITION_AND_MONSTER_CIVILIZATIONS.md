# 25 — 에이전트 경쟁 · 몬스터 문명 · NPC 번영

## 지향

| 대상 | 경쟁 | 결과 |
|------|------|------|
| **몬스터 ↔ 몬스터** | 서로 다른 **문명(부족)** 이 같은 맵에서 영역·먹이 다툼 | 승자 번영↑, 패자 HP↓·퇴각 |
| **몬스터 ↔ NPC** | 포식 (기존) | NPC 쓰러짐 → 몬스터 문명 번영↑, 공동체 번영↓ |
| **NPC ↔ NPC** | 건설·자원·인구 (라이벌 거점) | 앞선 건설자 번영, 뒤처진 거점은 build 감소 |

**전설급 개체는 소수** (doc 24) — 문명 전체가 강해져도 **맵 species_caps** 로 독점 방지.

## 몬스터 문명

`config/monster_civilizations.json`

| ID | 이름 | 단계 예 |
|----|------|---------|
| `goblin_tribe` | 고블린 부족연 | 흩어진 무리 → 전투 무리 → 군세 |
| `shadow_clan` | 그림자 일족 | 새끼 무리 → 사냥 무리 → 영역 지배 |

- `evolution_chain` → `civilization_id` 자동 매핑  
- `culture_tags`: raid, totem, ambush … (Godot·서사 훅)  
- **라이벌** 목록: 고블린 ↔ 그림자 — 인접 시 `[경쟁]` 로그

상태: `flags.ecology.civilizations[<civ_id>].prosperity`, `stage_id`, `wins/losses`

## NPC 번영

- `ashpoint_commons` — 애쉬포인트 builder·민간인 묶음  
- 건설 진행이 쌓이면 **공동체 번영** 상승  
- builder 2명 이상이면 **마을 경쟁** (선두 / 라이벌 압박)  
- 몬스터가 NPC 처치 시 공동체 번영 감소

## 틱 순서 (`tick_field_ecology`)

1. 개별 AI (포식·건설·도주)  
2. `tick_agent_competition` — 라이벌 전투 → NPC 경쟁 → 문명 단계 갱신  

## 플레이어 종족 · 연동 번영 (coupling)

세션 생성 시 `player_race` (`human` | `dwarf` | `elf` | `dark_elf` | `beastkin`):

- 해당 **realm·왕국·플레이어 문명** 에서 시작 (`init_player_civilization`)
- 여정 단계: **모험가 → 개척자 → 왕국 시민 → 왕국** (건설·왕국 선포와 연동)
- 플레이어가 건설/레벨업/왕국 선포 → **펄스** → 같은 맵 문명 + **연결 문명** + **오프맵 대륙 문명** 동시 성장

관찰용: `GET /v1/ecology/civilizations` — `player_profile`, `civilizations`, `recent_events`, `world_pulse`

로그 예: `[여정] 인간 — 왕국 시민`, `[세계] 심로 대장간 연맹 — 「대장간 번영」 (연동(건축 Lv3))`

## API / Godot

`GET /v1/world/agents` 에 `civilization_id`, `culture_tags`, `prosperity` 포함.  
`GET /v1/ecology/civilizations?session_id=` — 실시간 문명 요약·이벤트 피드.  
`POST /v1/session/new` body: `"player_race": "human"`.

## MMO 확장

- 문명 간 **동맹·혈전** (플레이어 길드와 별도)  
- 번영 높은 문명만 **희귀 진화** 해금 — 전 서버 1마리 독점 X  
- NPC 도시가 번영 단계에 따라 **타일 스왑** (hamlet → village)

## 관련

- [20_LIVING_FIELD_ECOLOGY.md](20_LIVING_FIELD_ECOLOGY.md)  
- [22_CHARACTER_PROGRESSION.md](22_CHARACTER_PROGRESSION.md)  
- [24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md](24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md)  
- `utils/agent_competition.py`
