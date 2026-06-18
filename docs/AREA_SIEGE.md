# 에리어 공성·수성 — 자연스러운 교전 흐름

고정된 "공성전 페이즈 1·2·3" **없음**. 적대 관계에서 파괴·요새·반격이 **연속 압력**으로 쌓이고, 그에 따라 교전이 유리/불리해집니다.

## 원칙

| CPoW 원칙 | 공성·수성 적용 |
|-----------|----------------|
| 데이터가 법 | `fortification_rating`, `garrison_heat` 속성 — 성벽 클래스 없음 |
| 고정 룰 없음 | `assault_momentum` vs 요새 강도 — 연속 수치 |
| 항시 가능 | **적대** 선언만으로 교전 가능 — 별도 "공성 시작" 버튼 없음 |
| 창조·파괴 대칭 | 공격=교차 파괴, 수성=요새 창조 + `repulse` + 균열 방어 |

## 흐름 (자연 발생)

```
적대 선언 ──→ 긴장 컨텍스트 생성 (압력 0)
      │
      ├─ 공격: POST /v1/areas/cross_destroy
      │         └ assault_momentum ↑, 이후 파괴 난이도 ↓ (방어 마모)
      │
      ├─ 수성: fortification_rating 오브젝트 창조
      │         └ 요새 강도 ↑, 틱마다 공성 압력 감쇠
      │
      ├─ 수성: POST /v1/areas/siege/repulse  (파괴력 소비)
      │         └ assault_momentum ↓
      │
      └─ 수성: POST /v1/areas/defend (균열)
                └ 일부 파괴력이 인접 공성 압력에도 반영
```

`flow.label` 은 UI용 **설명**일 뿐, 게임 규칙 페이즈가 아닙니다.

| flow | 의미 (예시) |
|------|-------------|
| `border_tension` | 적대만 있고 아직 교전 없음 |
| `skirmish` | 소규모 파괴·방어 오감 |
| `siege_pressure` | 공성 압력 누적 |
| `breach_window` | 방어 마모 — 파괴 유리 |
| `defenders_hold` | 요새·반격이 압도 |

## 수성 — 오브젝트 속성

창조 시 properties 예시:

```json
{
  "label": "북쪽 성곽",
  "properties": [
    {"name": "fortification_rating", "value": 95.0, "unit": "points"},
    {"name": "garrison_heat", "value": 40.0, "unit": "joules_per_tick"}
  ]
}
```

또는 확정 오브젝트에 `imbued_destruction` 부여 → 방어 저항에 기여.

## API

```bash
# 한 쌍의 공성 압력 (연속 상태)
GET /v1/areas/siege?attacker_area_id=A&defender_area_id=B

# 이 에리어와 관련된 모든 교전
GET /v1/areas/siege/active?area_id=B

# 수성 반격 — 파괴력으로 공성 압력 밀어냄
POST /v1/areas/siege/repulse
{
  "defender_area_id": "B",
  "attacker_area_id": "A",
  "actor_id": "guardian",
  "power_spend": 25
}

# 공격 (기존) — 성공 시 siege 상태 갱신
POST /v1/areas/cross_destroy
```

## 교차 파괴 난이도

`siege_cross_scale_modifier`:

- 요새가 강하고 공성 압력이 낮으면 → 공격 **어려움**
- `assault_momentum` 이 요새를 압도하면 → **突破口** 구간, 파괴 유리

지배 비율(작은 에리어 vs 큰 에리어)은 기존 `dominance` 와 함께 적용됩니다.

## 모듈

```
cpow_engine/areas/siege.py
cpow_engine/areas/registry.py   # SiegeLedger 통합
docs/AREA_DIPLOMACY.md          # 적대 선언
```

## Godot 클라이언트 (향후)

`cpow_client` 에서 `AreasClient.fetch_siege()` / HUD 압력 게이지 — 고정 턴 UI 없이 연속 바 표시.
