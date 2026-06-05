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

`config/agent_intelligence.json` · `config/monster_pack_behavior.json`

- **strategy** — `plunder_frenzy`(몬스터 기본), `rival_hunter`, `builder_focus` …
- **iq** (0–100) — 스킬 선택 점수·명중 보정·MP 회복
- **몬스터 relations** — 같은 문명도 **동맹 7%**만, 대부분 `rival` (내부 경쟁)
- **greed** (탐욕) — NPC보다 **몬스터 라이벌** 우선 타겟
- **pack** — `alpha` / `grunt`, `dominance`, 킬 시 무리 전체 `power_bonus` 성장
- **과다 지배** — 문명 번영 하락 (`[무리·자멸]`) — 강하지만 스스로 망할 수 있음

틱: `tick_agent_mind()` + `tick_rivalries()` **내부전** (`[내부전]`, `[무리]`)

인간 NPC는 여전히 연합·건설; **세계 운영은 강한 몬스터 객체**가 움직이는 쪽에 가깝다.

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
