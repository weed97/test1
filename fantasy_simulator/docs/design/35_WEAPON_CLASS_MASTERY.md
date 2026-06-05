# 35 — 무기 클래스별 직업 · 레벨 · 경지

## 원칙

| 잘못된 이해 | 올바른 규칙 |
|-------------|-------------|
| 인벤에 투핸드검을 **들고** 있으면 엑스칼리버 OK | **투핸드 소드 클래스 최고 경지** 만 **인정(착용·결속)** |
| 주직업 `knight`면 무기 무관 | **무기 클래스마다** 별도 **레벨·랭크** |
| 장비 슬롯에 끼움 = 착용 | **마스터리 검사 + 결속(bind)** 통과 시에만 준신급 인정 |

설정: `config/weapon_mastery.json`  
상태: `heroes[id].weapon_masteries[<class_id>]`

---

## 무기 클래스 (예)

| `class_id` | 라벨 | 주직업과 관계 |
|------------|------|----------------|
| `two_handed_sword` | 투핸드 소드 | 기사도 **별도** 레벨 필요 |
| `one_handed_sword` | 원핸드 소드 | 쌍수·방패 빌드 |
| `bow` | 활 | 레인저 |
| `staff` | 지팡이·술기 | 마법 견습 |

각 클래스:

- `level` 1~10 (설정별 `max_level`)
- `rank`: novice → adept → expert → master → **grandmaster** (최고 경지)
- `xp` — 전투·훈련·제작으로 **해당 클래스만** 오름

**주직업 `job_id` / `job_level`** 과 **무기 클래스** 는 **분리**. 둘 다 레벨이 붙는다.

---

## 영웅 상태 예

```json
{
  "job_id": "knight",
  "job_level": 4,
  "weapon_masteries": {
    "two_handed_sword": { "level": 10, "rank": "grandmaster", "xp": 6120 },
    "one_handed_sword": { "level": 3, "rank": "adept", "xp": 400 }
  }
}
```

- 투핸드 Lv10 grandmaster → **엑스칼리버 자격 후보**
- 원핸드 Lv3 → 한손검 전설 제작만 가능 (등급 상한 낮음)

---

## 착용 판정 (`can_bind_artifact`)

```text
1. artifact.required_mastery_class == "two_handed_sword"
2. hero.weapon_masteries[class].rank == "grandmaster"
3. hero.weapon_masteries[class].level >= class.max_level
4. ritual bind 성공 (들기만·인벤 장착만으로는 실패)
```

| 시도 | 결과 |
|------|------|
| 인벤에 넣기만 | OK (소지) |
| 장착 슬롯에 끼기 (마스터리 부족) | 훈련용·스탯 미적용 또는 거부 |
| **엑스칼리버 결속** | grandmaster **만** + 승계 의식 |

---

## 엑스칼리버 연동

[34_DEMIGOD_SOVEREIGN_EXCALIBUR.md](34_DEMIGOD_SOVEREIGN_EXCALIBUR.md)

- `weapon_kind: two_handed_sword`
- `requires_mastery_rank: grandmaster` + `level == max_level`
- 연합이 검을 뺏어도 **grandmaster 투핸드** 가 **결속**해야 `world_sovereign` 활성

---

## XP 획득 (후속 구현)

| 활동 | 클래스 XP |
|------|-----------|
| 해당 무기로 전투 승리 | 주 사용 무기 클래스 |
| 훈련 POI / 대장간 연습 | 지정 클래스 |
| 다른 클래스 사용 | 그 클래스로 분배 (주직업과 무관) |

---

## 관련

- [22_CHARACTER_PROGRESSION.md](22_CHARACTER_PROGRESSION.md) — 주직업·스킬
- [34_DEMIGOD_SOVEREIGN_EXCALIBUR.md](34_DEMIGOD_SOVEREIGN_EXCALIBUR.md) — 준신 결속
