# 26 — 월드 전쟁 · 침입 · 최상위 위협 (왕국은 무너져도 세계는 남는다)

## 목표

| 있음 | 없음 |
|------|------|
| 종족·문명 간 **침입·전쟁** (자원·마나·약탈·비밀·귀물) | 한 번에 **전 세계 멸망** |
| 영역마다 **최상위 몬스터(apex)** 가 왕국을 위협 | 최상위가 모든 문명을 0으로 |
| **연합 방어** — 막거나, 막았는데도 대규모 패배 | 무조건 플레이어·NPC 압승 |
| **아슬아슬한 전력 비율** 로그 | 단순 주사위 승패 |

## 전쟁 목적 (`war_goals`)

- `resource` — 자원 거점  
- `mana` — 마나 샘  
- `plunder` — 약탈  
- `secrets` — 비밀 정보  
- `relic` — 극희 귀물  

침입 발생 시 `casus_belli` + `goal_label` 이 전쟁 기록에 남음.

## 전력 해석

```
공격력 = 문명 번영 + 단계 보너스 + 난수
방력 = 같은 realm 연합 문명 합 × coordination(0.88) + 플레이어 건설/고용 보너스
비율 = 공격 / 방어
```

## 결과 밴드

| outcome | 비율(대략) | 의미 |
|---------|------------|------|
| `repelled` | < 0.72 | 침입 실패 |
| `stalemate` | ~1.0 | 교착·양측 피해 |
| `invasion_success` | < 1.75 | **한 왕국** 큰 피해 |
| `kingdom_collapse` | < 2.4 | **한 왕국** 거의 멸망, **realm·세계 유지** |
| `apex_kingdom_fall` | apex 전용 | 최상위 개체 + 연합 실패 시 왕국 함락 직전 |

**안전장치** (`world_conflicts.json` `balance`):

- `world_prosperity_floor` — 어떤 문명도 최저 번영 이하로 안 떨어짐  
- `never_erase_all_kingdoms` — 한 틱에 왕국 1개만 붕괴 수준  
- 최상위 이벤트도 **cannot_erase_world**

## 최상위 위협 (apex)

영역·문명에 묶인 보스급 존재 예:

| ID | 이름 | 조건 |
|----|------|------|
| `ashen_leviathan` | 잿빛 레비아탄 | shadow_clan dominion |
| `goblin_overking` | 고블린 오버킹 | goblin horde |
| `silver_ancient` | 실버 고대목 | elf high_court |
| `pride_worldbreaker` | 세계포식 우두머리 | beastkin pride_rule |

- 몬스터 문명이 **방어 문명보다 셀 때** 왕국 하나를 거의 지울 수 있음  
- 연합이 강하면 `apex_repelled` / 약하면 `narrow_defeat` / 매우 약하면 `apex_kingdom_fall`

## 틱·API

- `tick_world_conflicts` — `world_systems` 생태 틱 마지막  
- `GET /v1/ecology/wars?session_id=` — `active_war`, `history`, `apex_predators`  
- 로그: `[전쟁]`, `[재앙]`  

## Godot (후속)

- 월드맵 화살표: 침입 방향  
- 전쟁 패널: 목적·연합 vs 공격 수치·결과  
- “간신히 막음” / “연합 패배” 연출 색상

## 관련

- [24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md](24_ELDORIA_UNIVERSE_AND_POWER_ECOLOGY.md)  
- [25_AGENT_COMPETITION_AND_MONSTER_CIVILIZATIONS.md](25_AGENT_COMPETITION_AND_MONSTER_CIVILIZATIONS.md)  
- `config/world_conflicts.json` · `utils/world_conflicts.py`
