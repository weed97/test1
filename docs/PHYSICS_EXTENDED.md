# 확장 물리 엔진

기본 열·재료 상호작용 위에 **전기·유체·복사·구조·환경장·상변화** 레이어가 추가되었습니다.

## 틱 파이프라인

```
DefinitionPhysicsEngine   — 직접 연결 (열→재료, 전도)
        ↓
ExtendedPhysicsEngine     — 전기·유체·복사·구조 하중
        ↓
FieldPhysics              — 중력·풍 냉각·전역 압력
        ↓
CrossoverPhysics          — 허브·2-hop·전하·복사 교차
        ↓
apply_feedback (확장·환경·교차)
        ↓
PhaseChangePhysics        — 용융·응고
        ↓
EquilibriumRegulator      — 에너지·열 균형
```

## 오브젝트 타입 (API `type`)

| type | 핵심 속성 | effect_type 예시 |
|------|-----------|------------------|
| `charge` | `electric_charge` | `electrostatic`, `charge_crossover` |
| `fluid` | `fluid_pressure`, `viscosity` | `fluid_flow`, `ambient_pressure` |
| `radiant` | `radiation_intensity` | `radiation`, `radiation_crossover` |
| `structural` | `mass`, `structural_stress`, `melting_point`, `phase` | `structural_load`, `gravity`, `phase_melt` |
| `heat` / `material` | (기존) | `heat_transfer`, `hub_crossover` |

### API 창조 예시

```json
{
  "type": "charge",
  "label": "번개 구",
  "electric_charge": 120.0
}
```

```json
{
  "type": "structural",
  "label": "다리",
  "mass": 800.0,
  "material": "steel",
  "melting_point": 1500.0
}
```

## 환경장 (FieldPhysics)

| 장 | 조건 | effect_type |
|----|------|-------------|
| 중력 | `mass` 보유 | `gravity` → `structural_stress` 증가 |
| 풍 | 열·복사가 있는 오브젝트 | `wind_cooling` → `heat_intensity` 감소 |
| 압력 | `fluid_pressure` 보유 | `ambient_pressure` → 풀·기준압 쪽으로 수렴 |

## 상변화 (PhaseChangePhysics)

- `material_type` + `melting_point` + 온도(`heat_intensity` + `residual_heat` 근사)가 있으면 동작
- `temperature >= melting_point` → `phase` unit `liquid` (`phase_melt`)
- `temperature < melting_point * freeze_ratio` → `solid` (`phase_freeze`)

## 설정 (`config/physics_balance.json`)

| 키 | 기본값 | 설명 |
|----|--------|------|
| `extended_physics_enabled` | true | 확장 상호작용 on/off |
| `field_physics_enabled` | true | 환경장 on/off |
| `phase_change_enabled` | true | 상변화 on/off |
| `electrostatic_coupling` | 1.0 | 전하 결합 강도 |
| `fluid_flow_factor` | 0.35 | 유체 흐름 |
| `radiation_coupling` | 0.8 | 복사 전달 |
| `structural_load_factor` | 0.12 | 구조 하중 |
| `gravity_strength` | 9.8 | 중력 |
| `wind_strength` | 0.5 | 풍 냉각 |
| `ambient_pressure_base` | 101.3 | 기준 압력 (kPa) |
| `pressure_coupling` | 0.06 | 압력 수렴 속도 |
| `charge_hub_bleed` | 0.14 | 허브 전하 교차 |
| `radiation_bleed_factor` | 0.22 | 복사 bleed |
| `freeze_ratio` | 0.92 | 응고 온도 비율 |

자세한 교차·균형 튜닝은 [PHYSICS_BALANCE.md](./PHYSICS_BALANCE.md) 참고.

## 남은 물리 로드맵

- 에리어별 물리 법칙 (`AreaLawSet`)
- 3D 좌표 기반 거리 감쇠 (현재는 연결 그래프 거리)
- XR 실시간 `connect` + 속성 부여

전체 백로그: [TODO_REMAINING.md](./TODO_REMAINING.md)
