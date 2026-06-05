# 22 — 캐릭터·몬스터 성장 (탐험 연동)

탐험 중 **플레이어 파티**와 **필드 몬스터**가 함께 성장하는 데이터 주도 레이어입니다. Godot 스프라이트 상한과 맵별 개체 수를 맞춥니다.

## 목표

| 대상 | 성장 축 |
|------|---------|
| 영웅 (party) | 주직업·레벨·**무기 클래스별 레벨**·스킬·장비 슬롯 |
| 몬스터 | 진화 체인 (고블린 → 챔피언 → 킹) |
| 맵 | `max_total` / 종족별 `species_caps` |

## 설정

- `config/progression.json` — 직업, 스킬, 아이템, `evolution_chains`, `map_spawn_limits`
- 상태: `flags.ecology.progression.heroes[<character_id>]`

## 영웅

- 세션 생성(`ecology` / `hybrid`) 시 `init_heroes_from_party()` — 가렛→기사, 엘라라→마법 견습
- `explore` 턴 종료 시 `on_explore_progression()` → `explore_xp` (기본 8)
- 레벨업 시 `skills_by_level` 자동 해금 또는 `skill_points`로 `unlock_skill`
- `equip_item` — 주직업·최소 레벨 검사
- **무기 클래스 마스터리** — `config/weapon_mastery.json` · [35_WEAPON_CLASS_MASTERY.md](35_WEAPON_CLASS_MASTERY.md) (투핸드/원핸드/활/지팡이 각각 레벨·경지)

## 몬스터 진화

- `spawn_evolved_monster(chain_id, tier)` — 숲 시드: 고블린×3, 그림자 야수×1
- 습격으로 NPC 처치 시 `evolution_xp_per_plunder` → `grant_evolution_xp` → 티어 상승 로그 `[진화]`

## 스폰 한도 (Godot 안전)

```json
"forest_01": {
  "max_total": 12,
  "max_monsters": 8,
  "species_caps": { "goblin": 5, "shadow_beast": 3 }
}
```

- `can_spawn_agent()` — 스폰 전 검사
- `godot_recommended_max_sprites_per_map`: 32 (클라이언트 힌트)

## API

| 메서드 | 경로 |
|--------|------|
| GET | `/v1/progression/status?session_id=` |
| POST | `/v1/progression/unlock_skill` |
| POST | `/v1/progression/equip` |

`GET /v1/world/agents` 응답에 `species_id`, `evolution_tier`, `label` 포함.

## Godot (후속)

- 진행 HUD: 직업 Lv, 스킬 포인트, 맵 스폰 카운트
- 몬스터 스프라이트: `evolution_id` → 아틀라스 키

## 관련 문서

- [20_LIVING_FIELD_ECOLOGY.md](20_LIVING_FIELD_ECOLOGY.md)
- [19_SPATIAL_SIMULATION.md](19_SPATIAL_SIMULATION.md)
