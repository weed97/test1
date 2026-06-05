# 27 — 생태 에이전트 객체 (시뮬 권위 · Godot = 스프라이트)

## 원칙

| 층 | 역할 |
|----|------|
| **JSON/텍스트 정의** | archetype · evolution · skills · intelligence |
| **Python `ecology_agent` 객체** | HP/MP/스탯/스킬/관계/지성 — **진짜 상태** |
| **Godot** | `godot_sprite_key` 로 **이미지만** 표시 |

정의만 있고 객체가 없으면 스킬·전투가 재현되지 않는다.  
스폰 시 `build_ecology_agent()` / `enrich_evolved_agent()` 가 객체를 만든다.

## 객체 스키마

```json
{
  "object_type": "ecology_agent",
  "instance_id": "goblin_a1b2",
  "kind": "monster",
  "label": "고블린",
  "stats": { "str": 12, "agi": 10, "int": 6, "vit": 10 },
  "hp": 28, "max_hp": 28,
  "mp": 22, "max_mp": 22,
  "skills": ["scratch"],
  "skill_cooldowns": { "scratch": 0 },
  "intelligence": {
    "iq": 48,
    "strategy": "rival_hunter",
    "disposition": "hostile"
  },
  "relations": { "other_id": "ally|hostile|neutral" },
  "civilization_id": "goblin_tribe"
}
```

## 지성 · 상호운영

`config/agent_intelligence.json`

- **strategy** — `predator_pack`, `builder_focus`, `defensive_flee`, `rival_hunter` …
- **iq** (0–100) — 스킬 선택 점수·명중 보정·MP 회복
- **relations** — 같은 문명 `ally`, 라이벌 `hostile`, 몬스터↔NPC `hostile`
- **높은 iq** → 사거리·쿨다운·MP 고려한 스킬 선택 → 더 나은 전투 결과

틱: `tick_agent_mind()` — 이동 · 스킬(`[스킬]`) · 기본 공격 · 도주(`[지성]`)

## 스킬

- 정의: `field_ecology.json` `skills` + `progression.json` `skills`
- `mana_cost`, `range_tiles`, `cooldown_beats`, `power`
- MP 부족 시 기본 타격

## API (Godot)

`GET /v1/world/agents?session_id=&map_id=&instance_id=`

- `schema`: `ecology_agent`
- 각 항목: `stats`, `hp`, `mp`, `intelligence`, `relations`, `godot_sprite_key`

## 모듈

| 파일 | 역할 |
|------|------|
| `utils/ecology_objects.py` | 생성·정규화·manifest |
| `utils/agent_mind.py` | 관계·전략·스킬 전투 |
| `utils/field_agents.py` | 스폰·틱·목록 |

## 관련

- [20_LIVING_FIELD_ECOLOGY.md](20_LIVING_FIELD_ECOLOGY.md)
- [25_AGENT_COMPETITION_AND_MONSTER_CIVILIZATIONS.md](25_AGENT_COMPETITION_AND_MONSTER_CIVILIZATIONS.md)
- [15_GODOT_RELEASE_ARCHITECTURE.md](15_GODOT_RELEASE_ARCHITECTURE.md)
