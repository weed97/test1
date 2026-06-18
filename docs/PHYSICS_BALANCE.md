# 물리 교차 · 자동 균형

**목표**: 물리 교차가 **매우 활발**한 세계이면서, 에너지·열이 **스스로 균형점**을 찾는 구조.

고정된 "밸런스 패치"나 턴당 캡이 아니라, **속성 피드백 + 연속 조절**로 구현합니다.

## 두 레이어

```
┌─────────────────────────────────────────────────────────┐
│  DefinitionPhysicsEngine  — 직접 연결 (열→재료 등)       │
├─────────────────────────────────────────────────────────┤
│  ExtendedPhysicsEngine    — 전기·유체·복사·구조         │
│  FieldPhysics             — 중력·풍·전역 압력           │
├─────────────────────────────────────────────────────────┤
│  CrossoverPhysics         — 허브·2-hop·환경·전하·복사   │
│    → hub_crossover, path_crossover, ambient_coupling    │
├─────────────────────────────────────────────────────────┤
│  apply_feedback           — residual_heat, heat drain   │
│  PhaseChangePhysics       — 용융·응고                    │
├─────────────────────────────────────────────────────────┤
│  EquilibriumRegulator     — 풀 과열 방출·저온 보충       │
│    → balance_index (0~1)                                │
└─────────────────────────────────────────────────────────┘
```

확장 속성·환경장·상변화 상세: [PHYSICS_EXTENDED.md](./PHYSICS_EXTENDED.md)

## 활발한 교차 (Crossover)

| 경로 | 조건 | effect_type |
|------|------|-------------|
| **허브 공명** | A→H, B→H 동일 허브 | `hub_crossover` |
| **2-hop** | A→M←B (직접 연결 없음) | `path_crossover` |
| **환경 결합** | `energy_pool` 전역 장 | `ambient_coupling` |

직접 `connect` 없이도 **허브 오브젝트**를 두면 교차가 살아납니다.

### 피드백 속성

- `residual_heat` — 교차로 흡수된 잔열 (다음 틱에 다시 방출)
- `heat_intensity` — 전달 시 서서히 감소 (에너지 보존 쪽)

## 자동 균형 (Equilibrium)

`config/physics_balance.json` 튜닝:

| 파라미터 | 역할 |
|----------|------|
| `target_energy_per_object` | 오브젝트 수 × 목표 → 에너지 풀 목표치 |
| `pool_dissipation_rate` | 과열 풀 방출 |
| `pool_injection_rate` | 침체 시 미세 보충 (세계 정지 방지) |
| `heat_pull_to_ambient` | 개별 열원을 평균으로 당김 |
| `residual_decay` | 잔열 소멸 |

`balance_index` ≈ 1.0 에 가까울수록 **활발 + 안정** (풀·열 분산·상호작용 수 종합).

## 틱 파이프라인

```python
base = physics.resolve_interactions(objects)
cross = crossover.resolve(objects, energy_pool=pool)
crossover.apply_feedback(objects, base + cross)
pool += sum(energy_delta)
equilibrium.regulate(state, interactions)  # balance_index 갱신
```

에리어·협동 월드 펄스(`CollaborativeWorld.advance_pulse`)가 `engine.tick()` 을 호출하므로 **모든 에리어에 자동 적용**.

## API / 관측

협동 월드 공개 상태:

```json
{
  "physics_balance": {
    "balance_index": 0.82,
    "crossover_density": 0.35,
    "interaction_count": 12
  }
}
```

`GET /v1/areas/state` → `area.world` 에 포함.

## 설계 원칙

1. **교차는 많게** — 연결 그래프·허브·에너지 풀이 경로를 만든다
2. **균형은 연속적으로** — 임계값 페이즈 없음
3. **데이터가 법** — `fortification_rating`·`heat_intensity` 등 속성만 사용
4. **죽은 세계 방지** — `pool_injection_floor` 이하일 때 미세 에너지 주입

## 모듈

```
cpow_engine/physics/crossover.py
cpow_engine/physics/equilibrium.py
cpow_engine/physics/balance_config.py
cpow_engine/config/physics_balance.json
cpow_engine/engine.py
```

## 테스트

```bash
python3 -m unittest cpow_engine.tests.test_physics_balance -v
```
