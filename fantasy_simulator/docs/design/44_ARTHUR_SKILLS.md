# 44 — 아서왕 핵심 스킬 5종

설정: `config/field_ecology.json` (`skills`) · `config/combatants.json` · `config/equipment_templates.json`  
코드: `utils/combat_stats.py` (`resolve_arthur_skill`, `preview_arthur_skill_damage`) · `utils/agent_mind.py` · `utils/ecology_objects.py` (`skill_definition`)

---

## 스킬 목록

| ID | 이름 | 파이프라인 | 전투 |
|----|------|------------|------|
| `sovereign_blade_combo` | 성검 연속베기 | `sovereign_strike` (basic) | 타격당 **10,000** 캡 · 3연타 |
| `sovereign_broad_cleave` | 왕의 광역검 | `sovereign_aoe` | 일반 광역 **×0.5** → **5,000** |
| `kings_aegis` | 왕의 가호 | `sovereign_buff` | 방어·재생·위기 버티기 |
| `excalibur_sovereign_judgment` | 주권의 심판 | `sovereign_aoe` (ultimate) | HP **25%** 이하 · 쿨 **7200s** · 원샷 |
| `sovereign_wish_rite` | 주권 소원 의식 | `world_edict` | 전투 외 · 4년 주기 edict |

`npc_arthur_pendragon` · `excalibur_sovereign_blade.skills` 에 동일 5종 연결.

---

## 맥스뎀 캡 (필수)

| 구분 | 상한 |
|------|------|
| 기본 타격 (`sovereign_strike_mode: basic`) | **10,000** |
| 스킬 타격 | **50,000** |
| Lv999×0.1% | **미적용** (`suppress_character_level_scaling`) |

`strike_damage_milli` · `_sovereign_strike_damage_milli` · `resolve_excalibur_aoe` 가 동일 캡을 공유.

---

## 광역·궁극기

- **왕의 광역검**: `resolve_excalibur_aoe(..., ultimate=False)` — 50만 HP 정예 **한 방 생존**
- **주권의 심판**: `resolve_excalibur_aoe(..., ultimate=True)` — 반경 **100px**, 스킬 불능, 마법사만 바이탈 **10px** 회피, 10명 집결 시 전멸

설정 앵커: `config/damage_scaling.json` → `excalibur_ultimate`

---

## 왕의 가호

- `damage_reduction_milli`, `regen_per_sec_milli` (연합 공성 regen 앵커와 동일 160k/s)
- `crisis_hp_ratio: 0.25` — 궁극기 발동 구간과 정합
- 전투 피해 0 — 버프 전용

---

## 주권 소원 의식

- `config/demigod_sovereign.json` 연동
- `forbidden_edicts` · `wish_edict_types` 반환
- 전투 데미지 없음 — `POST /v1/sovereign/wish` 루트와 별도 시뮬 엔트리

---

## API · 시뮬

| 엔드포인트 | 용도 |
|------------|------|
| `POST /v1/combat/arthur_skill` | 스킬 ID별 `resolve_arthur_skill` |
| `POST /v1/combat/arthur_aoe` | 광역/궁극기 직접 시뮬 (하위 호환) |
| `preview_skill_damage` (agent_mind) | 필드 에이전트·병렬 비트 경로 |

---

## 관련 문서

- [34_DEMIGOD_SOVEREIGN_EXCALIBUR.md](34_DEMIGOD_SOVEREIGN_EXCALIBUR.md)
- [43_WORLD_PIERCE_ELITES.md](43_WORLD_PIERCE_ELITES.md)
