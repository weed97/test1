# 35 — 캐릭터 레벨 · 직업 · 무기 클래스 레벨 (각 만렙 999)

## 세 축 분리

```text
캐릭터 레벨 (1~999)     — 생명력·기초 능력·성장 총량
직업 레벨 (1~999/직업)  — 선택 직업별 스킬·역할 (직업 변경 가능, 직업별 레벨 유지)
무기 클래스 레벨 (1~999) — 투핸드/원핸드/활/지팡이… 각각 독립
```

| 축 | 만렙 | 바꿀 수 있나 | 비고 |
|----|------|--------------|------|
| **캐릭터** | 999 | — (캐릭터 고유) | `character_level` |
| **직업** | 999 | **직업 변경 OK** | `active_job_id` + `jobs[job_id].level` |
| **무기 클래스** | 999 | 클래스마다 따로 | `weapon_masteries[class_id].level` |

**위력은 완전히 다름** — 같은 캐릭터 Lv200이라도 투핸드 Lv800 vs 활 Lv20이면 전투·제작·결속 자격이 전혀 다르다.

설정: `config/weapon_mastery.json` · `config/progression.json` (`character`, `job_progression`)  
상태: `heroes[id]`

---

## 직업 변경

- `job_change_allowed: true`
- `persist_levels_per_job: true` — 기사 Lv400 키우다 레인저로 바꿔도 `jobs.knight.level` 은 **그대로**, 레인저는 `jobs.ranger.level` 별도.
- 스킬·전투 스타일은 **활성 직업** + **지금 쓰는 무기 클래스** 조합.
- 무기 클래스 레벨은 직업 변경과 **무관하게 유지**.

---

## 무기 클래스

| `class_id` | 라벨 |
|------------|------|
| `two_handed_sword` | 투핸드 소드 |
| `one_handed_sword` | 원핸드 소드 |
| `bow` | 활 |
| `staff` | 지팡이·술기 |
| `dagger` | 단검 |
| `spear` | 창 |

각 클래스 **만렙 999**.  
**경지(rank)** 는 레벨 구간으로 자동 (전역 `rank_thresholds`):

| rank | 최소 레벨 |
|------|-----------|
| novice | 1 |
| adept | 100 |
| expert | 300 |
| master | 600 |
| grandmaster | 900 |
| **만렙 경지** | **999** (엑스칼리버 결속은 **Lv999 + grandmaster**) |

XP는 레벨별 **공식** (`xp_formula`) — 999칸 테이블을 JSON에 두지 않음.

---

## 영웅 상태 예

```json
{
  "character_level": 220,
  "character_xp": 1840000,
  "active_job_id": "knight",
  "jobs": {
    "knight": { "level": 180, "xp": 920000 },
    "ranger": { "level": 45, "xp": 38000 }
  },
  "weapon_masteries": {
    "two_handed_sword": { "level": 999, "rank": "grandmaster", "xp": 0 },
    "bow": { "level": 12, "rank": "novice", "xp": 1100 }
  }
}
```

- 투핸드 999 → 엑스칼리버 **결속 자격** (들기만으로는 불가)
- 같은 캐릭터가 활 Lv12 → 활 전투는 **초보 수준**

---

## 위력 합성 (체감)

구현 시 대략:

```text
effective_power ∝ f(character_level) × g(active_job_level) × h(weapon_class_level_used)
```

무기를 바꾸면 `h`가 바뀌어 **같은 캐릭터도 체감이 완전히 달라짐**.  
직업만 바꿔도 `g`가 바뀜. **세 축이 곱**으로 작용.

---

## 착용 · 결속 (`can_bind_artifact`)

1. `required_mastery_class` (예: `two_handed_sword`)
2. 해당 클래스 `level == 999`
3. `rank == grandmaster` (Lv ≥ 900이면 grandmaster, **결속은 999 요구**)
4. **bind ritual** — 인벤·임시 장착만으로는 준신 권한 없음

| 시도 | 결과 |
|------|------|
| 소지·운반 | 가능 (권한 없음) |
| 마스터리 부족 장착 | 훈련용 / 스탯 미적용 |
| **엑스칼리버 결속** | 투핸드 **Lv999** 만 |

---

## 엑스칼리버

[34_DEMIGOD_SOVEREIGN_EXCALIBUR.md](34_DEMIGOD_SOVEREIGN_EXCALIBUR.md) — `requires_mastery_level_at_max: true` → **999**.

---

## 관련

- [22_CHARACTER_PROGRESSION.md](22_CHARACTER_PROGRESSION.md)
- [34_DEMIGOD_SOVEREIGN_EXCALIBUR.md](34_DEMIGOD_SOVEREIGN_EXCALIBUR.md)
