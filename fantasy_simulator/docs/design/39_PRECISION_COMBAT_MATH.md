# 39 — 정밀 전투 수학 (0.001 단위)

## 원칙

| 규칙 | 내용 |
|------|------|
| **저장** | 부동소수점 금지 — **정수 milli** (`×1000`) |
| **표시** | 공격·방어·데미지 **소수 3자리** (`45.125`) |
| **확률** | 회피·크리 **0.001%** (`12.345%` → `12345` / `rate_scale`) |
| **민감도** | **데미지 1.000 차이**·방어 1.000 차이가 최종 피해에 **반드시** 반영 |
| **우선순위** | 캐릭터 Lv → 무기 클래스 Lv → 아이템 등급 ([36](36_ITEM_GRADES_AND_LEVEL_SUPREMACY.md)) |

설정: `config/combat_precision.json`  
구현: `utils/combat_precision.py`

---

## 스케일

```text
fixed_scale = 1000   → stat_milli = round(stat × 1000)
rate_scale  = 100000 → rate_milli = round(percent × 1000)   // 100% = 100000
```

예:

- 공격력 `120.450` → `120450`
- 크리 `15.125%` → `15125`

---

## 피해 파이프라인

```mermaid
flowchart TD
  H[명중 판정 hit_rate] -->|miss| Z[0]
  H -->|hit| R[raw_attack_milli]
  R --> L[level_supremacy mult]
  L --> M[방어 mitigation K/(K+def)]
  M --> C{크리?}
  C -->|yes| F[× crit_mult 2.000]
  C -->|no| G[after_armor]
  F --> MIN[min 1.000 damage]
  G --> MIN
```

### 1. 명중 · 회피

```text
hit_rate_milli = clamp(
  base + accuracy_bonus - evasion_penalty,
  min_hit_rate,
  max_hit_rate
)
```

- 기본 `100.000%` 에서 **회피·명중 milli**로 **0.001%** 단위 조정.
- 상한 `99.500%`, 하한 `5.000%` (완전 무적·필중 방지).

### 2. 방어 (피해 감소)

```text
after_armor_milli = raw_attack_milli × K / (K + defense_milli)   // 정수 나눗셈, 중간 mult 생략
mitigation_mult_milli = K × 1000 / (K + defense_milli)           // 표시·감사용
```

중간 배율을 먼저 `//` 로 자르면 **방어 1.000 차이**가 사라질 수 있어 **피해는 항상 직접식**으로 계산한다.

- `K` = `8_500_000` milli (설정 조절).
- **방어 +1.000** → mult 하락 → 피해 **최소 0.050 이상** 감소 (테스트 `sensitivity_targets`).

### 3. 레벨 우월 (캐릭터 > 무기 > 등급)

```text
score = Δchar×500 + Δweapon×350 + Δgrade×150
level_mult_milli = 1000 + score × per_level_delta / 1000
```

### 4. 크리티컬

- 기본 `5.000%`, 상한 `75.000%`.
- 배율 `2.000×` (milli `2000`).

### 5. 최소 피해

- 명중 시 **최소 `1.000`** (`min_final_damage_milli: 1000`).

---

## 장비 · 스탯 입력

무기·방어구·악세는 [38](38_COMBAT_POWER.md) 템플릿에서 **milli** 로 합산 후 파이프라인 입력:

| 필드 | 설명 |
|------|------|
| `attack_milli` | 무기 베이스 + 마스터리 + 스탯 |
| `defense_milli` | 방어구 + vit 등 |
| `accuracy_milli` / `evasion_milli` | 명중·회피 |
| `crit_rate_milli` | 크리 % |

**무기마다** `base_damage_min/max`·레벨당 곡선 **다름** — 합산 전에 템플릿별 계산.

---

## 밸런스 가드

| 가드 | 값 |
|------|-----|
| `max_damage_per_strike_milli` | 500000.000 상한 |
| `max_hp_milli` | 2000000.000 |
| 명중 시 0 피해 | 금지 (`never_zero_if_hit`) |
| 신·준신 소원 | [34](34_DEMIGOD_SOVEREIGN_EXCALIBUR.md) 금지 edict 별도 |

민감도 테스트: `tests/test_combat_precision.py`

---

## API (후속)

```json
POST /v1/combat/preview_strike
{
  "attacker": { "attack_milli": 120450, "character_level": 220, ... },
  "defender": { "defense_milli": 80400, ... }
}
→ { "damage": 45.127, "damage_milli": 45127, "audit": { ... } }
```

Godot 툴팁: `120.450 ATK` · `크리 15.125%` · 예상 피해 `43.200~47.800`

---

## 한 줄

**모든 전투 수치는 0.001 단위 정수 권위 · 1.000 차이도 파이프라인 전체에 전파 · 캐릭터 Lv > 무기 Lv > 등급 · 테스트로 밸런스 고정.**
