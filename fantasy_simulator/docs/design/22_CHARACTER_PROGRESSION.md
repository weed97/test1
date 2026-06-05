# 22 — 캐릭터·몬스터 성장 (탐험 연동)

탐험 중 **플레이어 파티**와 **필드 몬스터**가 함께 성장하는 데이터 주도 레이어입니다. Godot 스프라이트 상한과 맵별 개체 수를 맞춥니다.

## 목표

| 대상 | 성장 축 |
|------|---------|
| 영웅 (party) | **캐릭터 Lv** · **직업별 Lv** (변경 가능) · **무기 클래스별 Lv** · 스킬 · 장비 |
| 몬스터 | 진화 체인 (고블린 → 챔피언 → 킹) |
| 맵 | `max_total` / 종족별 `species_caps` |

## 세 레벨 축 (각 만렙 999)

| 축 | 필드 | 만렙 |
|----|------|------|
| 캐릭터 | `character_level` | 999 |
| 직업 (직업마다 저장) | `jobs[job_id].level` | 999 |
| 무기 클래스 | `weapon_masteries[class_id].level` | 999 |

- **직업 변경 가능** — `active_job_id`만 바꿈, 각 직업 레벨은 **유지**.
- **무기 레벨**은 직업과 독립 — 투핸드 999 + 활 10 같은 극단적 분포 가능.
- **위력**은 세 축이 합쳐져 **완전히 다른 체감** — [35_WEAPON_CLASS_MASTERY.md](35_WEAPON_CLASS_MASTERY.md).

## 설정

- `config/progression.json` — `character`, `job_progression`, 직업, 스킬, 아이템
- `config/weapon_mastery.json` — 무기 클래스·경지·만렙 999
- 상태: `flags.ecology.progression.heroes[<character_id>]`

## 영웅 (현재·목표 스키마)

- 세션 생성 시 `init_heroes_from_party()` — 가렛→기사, 엘라라→마법 견습
- **레거시** `job_level` 단일 필드 → 마이그레이션: `jobs[active_job_id].level`
- `explore` / 전투 시 캐릭터 XP · 직업 XP · **주 사용 무기 클래스** XP 분리 지급 (후속)
- `equip_item` — 직업·최소 레벨 + 무기 클래스 요구 (후속)
- `change_job(job_id)` — `job_change_allowed` (후속 API)

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
| POST | `/v1/progression/change_job` (후속) |

`GET /v1/world/agents` 응답에 `species_id`, `evolution_tier`, `label` 포함.

## Godot (후속)

- 진행 HUD: 캐릭터 Lv · 활성 직업 Lv · 무기 클래스 Lv
- 몬스터 스프라이트: `evolution_id` → 아틀라스 키

## 관련 문서

- [20_LIVING_FIELD_ECOLOGY.md](20_LIVING_FIELD_ECOLOGY.md)
- [19_SPATIAL_SIMULATION.md](19_SPATIAL_SIMULATION.md)
- [35_WEAPON_CLASS_MASTERY.md](35_WEAPON_CLASS_MASTERY.md)
