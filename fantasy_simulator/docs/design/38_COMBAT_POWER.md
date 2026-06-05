# 38 — 전투력 (Combat Power) · 장비 · 직업 스탯 루트

## 전투력이란

`effective_power` 의 **플레이어-facing 이름** = **전투력**.

설정: `config/combat_power.json`

**강함 우선순위** (변경 없음):

```text
1. 캐릭터 레벨
2. 무기 클래스 레벨
3. 아이템 등급 (준신 · 신화 · 전설 · 영웅 · 희귀 · 고급 · 일반)
```

전투력은 위 세 축 + **아래 상세**를 합산해 산출한다.

---

## 구성 요소

| 요소 | 설정 | 설명 |
|------|------|------|
| **직업 스탯 루트** | `job_stat_routes.json` | 기사=힘·체력, 마법=지능… **직업마다 성장 곡선 다름** |
| **무기 템플릿** | `equipment_templates.json` | 종류별 **기본 데미지·공속·속성** 다름 |
| **무기 레벨 보너스** | `combat_power.json` `weapon_mastery_scaling` | 클래스마다 **레벨당 추가치** 다름 (대검=공격↑, 활=치명↑) |
| **방어구** | 동일 | 방어·저항·블록 — 등급·베이스 다름 |
| **악세서리** | 동일 | 스탯·발동 효과·유틸 |

```text
전투력 ≈ 캐릭터·직업 스탯
       + 무기마스터리 스케일링
       + 장착 무기 CP
       + 장착 방어구 CP
       + 악세서리 CP
       + 등급 특수효과/스킬
```

---

## 무기 — 종류·레벨·등급

- **종류** (`two_handed_sword`, `bow` …): `base_damage_min/max`, `attack`, `speed` **각각 다름**.
- **무기 클래스 Lv**: `mastery_bonus_curve` — 대검은 `attack_per_level` 0.95, 활은 `crit_per_level` 0.015 등 **추가치 곡선 분리**.
- **등급**:
  - 일반~영웅: 특수효과·아픽스 슬롯
  - **전설 이상**: **스킬 부여** · **전투 패턴 변화** (`combat_transform`)
  - 신화·준신: 영역·주권급 훅

예: `sealbreaker_blade` (전설) — `legend_cleave`, `wide_arc_strikes`

---

## 방어구 · 악세서리

| 슬롯 | 주 스탯 | 등급 이상 |
|------|---------|-----------|
| **방어구** | defense, resist, block | 전설+ 스킬 (`mythic_bulwark` 등) |
| **악세서리** | bonus 스탯, proc | 전설+ 스킬·파티 버프 |

방어구·악세도 **템플릿별 베이스 다름** + **등급별 affix/skill**.

---

## 등급별 전투 훅 (`grade_combat_hooks`)

| 등급 | 아픽스 | 스킬 | 전투 변화 |
|------|--------|------|-----------|
| 일반 | 0 | ✕ | — |
| 고급 | 1 | ✕ | — |
| 희귀 | 1 | ✕ | 특수효과 |
| 영웅 | 2 | ✕ | 특수효과 |
| **전설+** | 2+ | **○** | **큰 변화 가능** |
| 신화 | 3 | ○ | 영역 affix |
| 준신 | 4 | ○ | 주권 훅 |

---

## 착용 게이트 (요약)

등급이 높아도 **캐릭터 Lv · 무기 클래스 Lv** 미달이면 실전 스탯·스킬 **미적용** — [36](36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md).

---

## API · UI (후속)

- `GET /v1/progression/status` → `combat_power` per hero  
- 장비 툴팁: 베이스 데미지 · 마스터리 보너스 · 등급 스킬 목록  

---

## 관련

- [22_CHARACTER_PROGRESSION.md](22_CHARACTER_PROGRESSION.md)
- [35_WEAPON_CLASS_MASTERY.md](35_WEAPON_CLASS_MASTERY.md)
- [36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md](36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md)
