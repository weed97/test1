# 45 — 레벨 해금 · 스킬 카탈로그 (Lv999)

설정: `config/progression_unlocks.json` · `config/item_grades.json` · `config/weapon_mastery.json`  
코드: `utils/skill_catalog.py` · `utils/level_unlocks.py` · `utils/progression.py`

---

## 목표

| 요구 | 응답 |
|------|------|
| **999까지 성장** | 캐릭터 Lv · 직업 Lv · 무기 숙련 Lv 각 999 |
| **클래스당 ~300 스킬** | 카탈로그 생성기 — 공격80·이동40·보조50·버프45·디버프45·패시브40 |
| **무기 숙련 스킬** | 클래스당 60 (공격25·이동10·버프10·패시브15) |
| **레벨마다 해금** | 스킬·착용 등급·슬롯·강화 티어 |
| **점점 강해짐** | 스킬 tier + 영웅 Lv에 따른 `effective_skill_power` |

---

## 성장 3축 + 해금 종류

```text
캐릭터 Lv 1~999  → 패시브 스킬 · 패시브 슬롯 · 캐릭터 마일스톤
직업 Lv 1~999    → 클래스 스킬 300 · 직업 강화 티어 · 직업 마일스톤
무기 숙련 Lv 1~999 → 무기 전용 스킬 60 · 등급 착용 · 결속 자격
```

| 축 | 스킬 해금 | 장비/기능 해금 |
|----|-----------|----------------|
| 캐릭터 | `passive` 40종 (`character_level`) | 악세 슬롯, 파티 슬롯… |
| 직업 | `knight_atk_001` … 300종 (`job_level`) | 스킬 강화 티어 2~5 |
| 무기 숙련 | `wpn_bow_watk_001` … 60종 | 훈련 무기·신화 착용·999 결속 |

---

## 스킬 ID 규칙

| 패턴 | 예 | 개수 |
|------|-----|------|
| `{job}_{cat}_{tier:03d}` | `knight_atk_040` | 300/직업 |
| `wpn_{class}_{cat}_{tier:03d}` | `wpn_bow_wmov_005` | 60/무기클래스 |

카테고리 prefix: `atk` `mov` `sup` `buf` `deb` `psv` / 무기: `watk` `wmov` `wbuf` `wpsv`

---

## 해금 레벨 분배

각 카테고리 내 tier `1..N` → 요구 레벨 **1~999 균등 분배**:

```text
unlock_level = 1 + (tier - 1) × 998 / (N - 1)
```

- **패시브**만 `character_level` 축
- **공격 tier 40·80** 등 일부는 추가 `weapon_mastery_level` 게이트
- 무기 스킬은 `weapon_mastery_level` 축

---

## 스킬 위력 성장

```text
effective_power = base_power × (1 + job_lv/999×0.5 + char_lv/999×0.2 + (enhance_tier-1)×0.08)
                  × (1 + (tier-1)×0.012)
```

- `base_power` = tier·해금레벨 기반 (`skill_catalog.scaling`)
- `job_skill_enhance_tier` = 직업 Lv 100/300/600/900 마일스톤

---

## 착용 해금 (`item_grades.wield_gates`)

| 등급 | 캐릭터 Lv | 무기 숙련 Lv | 경지 |
|------|-----------|--------------|------|
| 일반 | 1 | 1 | — |
| 신화 | 500 | 700 | master |
| 준신 | 800 | 999 | grandmaster |

`can_wield_grade()` — 미달 시 소지만 가능, 실전 스탯 미적용.

추가 마일스톤: `progression_unlocks.equip_unlock_curve` (숙련 25 훈련검 … 999 결속 게이트)

---

## API · 상태

- `GET /v1/progression/status` → `unlock_status`, `skill_catalog` 요약
- 영웅 상태: `flags.ecology.progression.heroes[id]`
  - `character_level`, `jobs`, `weapon_masteries`, `unlocked_skills`, `equip_unlocks`

---

## 직업 8종 · 고유 이름 · 전투 AI

| 직업 | ID | 스킬 수 |
|------|-----|---------|
| 기사 | `knight` | 300 |
| 레인저 | `ranger` | 300 |
| 마법 견습 | `arcane_apprentice` | 300 |
| 방랑자 | `wanderer` | 300 |
| 성기사 | `paladin` | 300 |
| 암살자 | `assassin` | 300 |
| 성직자 | `cleric` | 300 |
| 광전사 | `berserker` | 300 |

- **고유 이름**: `utils/skill_names.py` — 마일스톤 tier(1·5·10…80) 한글명, 시그니처 스킬 VFX
- **전투 AI**: `utils/combat_skill_ai.py` — 공격/버프/디버프/이동 상황별 `pick_combat_skill`
- **아서**: HP 25% 이하 + 다수 적 → `excalibur_sovereign_judgment` 우선
- **Godot**: `scenes/skill_tree.tscn` — `GET /v1/progression/skill_tree`

---

## 관련

- [22_CHARACTER_PROGRESSION.md](22_CHARACTER_PROGRESSION.md)
- [35_WEAPON_CLASS_MASTERY.md](35_WEAPON_CLASS_MASTERY.md)
- [36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md](36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md)
- [44_ARTHUR_SKILLS.md](44_ARTHUR_SKILLS.md) — 준신 예외(맥스뎀 캡)
