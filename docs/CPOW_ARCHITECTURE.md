# CPoW Architecture

## 개요

이 문서는 **CPoW (Creativity-Proof of Work) 시뮬레이션 엔진**의 아키텍처를 정의합니다.  
이 프로젝트는 게임이 아니라, 유저 창조 데이터가 물리 법칙이 되는 자율 시뮬레이션 시스템입니다.

## 3대 핵심 모듈

```
┌─────────────────────────────────────────────────────────┐
│                  SimulationEngine                        │
│  (틱 루프 · 상태 관리 · 모듈 오케스트레이션)              │
└──────────┬──────────────────┬──────────────────┬───────┘
           │                  │                  │
    ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐
    │   Physics   │    │    CPoW     │    │   Shared    │
    │   Engine    │    │   Engine    │    │    State    │
    │             │    │             │    │             │
    │ 속성 정의 →  │    │ Action +    │    │ Merge /     │
    │ 상호작용 결과│    │ Delta →     │    │ Negotiation │
    │             │    │ 에너지·점수  │    │             │
    └─────────────┘    └─────────────┘    └─────────────┘
```

### ① 물리 정의 엔진 (`cpow_engine/physics/`)

- **원칙**: Fire 클래스를 개발자가 만들지 않음. 유저가 `heat_intensity` 속성을 정의.
- **역할 인터페이스**: `HeatSource`, `Material`, `EnergyTransfer`
- **규칙**: `PhysicsRule` 데이터 구조 — `heat_transfer`, `energy_emission` 등
- **출력**: `InteractionResult` (effect_type, magnitude, energy_delta)

### ② CPoW 환산 엔진 (`cpow_engine/cpow/`)

- **입력**: `ActionRecord` + `WorldDelta` + `SimulationState`
- **출력**: `CPoWScore` (energy, economic_value, creativity_score)
- **봇 억제 휴리스틱**:
  - 반복 행동 패널티 (`repetition_penalty`)
  - 동일 fingerprint 감쇄 (`creativity_score`)
  - 균일한 간격·동일 payload 탐지 (`bot_risk`)

### ③ 공유 상태 동기화 (`cpow_engine/shared_state/`)

- **입력**: `StatePatch` 리스트 (author_id, base_version, objects)
- **충돌 처리**: 오류가 아닌 `ConflictRecord` → Merge/Negotiation
- **전략**: `MERGE` (가중 평균), `NEGOTIATE`, `LAST_WRITE_WINS`, `REJECT`

## 데이터 스키마

### CreativeObject

```json
{
  "id": "abc123",
  "creator_id": "user_alpha",
  "label": "창조된 열원",
  "properties": [
    {"name": "heat_intensity", "value": 100.0, "unit": "joules_per_tick"}
  ],
  "connections": ["def456"],
  "creativity_fingerprint": "a1b2c3..."
}
```

### SimulationState

```json
{
  "tick": 3,
  "objects": { "...": "..." },
  "energy_pool": 245.7,
  "entropy": 0.85,
  "version": 5
}
```

## 판타지 → CPoW 전환 매핑

| 레거시 (버림) | CPoW (가져감) |
|---------------|---------------|
| `파이어볼` 스킬 | `heat_intensity` 속성 오브젝트 |
| 고정 몬스터 스탯 | `material_type` + `thermal_conductivity` |
| 아이템 강화 공식 | 속성 가중 병합 (SharedState) |
| 고정 스킬 리스트 | `PhysicsRule` 데이터 |
| Godot 3D 에셋 로더 | 유지 (표현층) |
| 인벤토리 UI | 유지 (오브젝트 목록 UI) |
| Auth | 유지 (creator_id) |

## MVP 검증 시나리오

1. 유저 A가 `heat_intensity=100` 오브젝트 생성
2. 유저 A가 `material_type=iron` 오브젝트 생성
3. 두 오브젝트 연결
4. 틱 진행 → `heat_transfer` 상호작용 → 에너지 풀 증가
5. CPoW 점수 산출 (창조성 보너스)
6. 유저 B/C가 동일 오브젝트에 상충 패치 → 가중 평균 병합

## 확장 로드맵

- [ ] `fantasy_simulator` 어댑터 (`state["cpow"]` 샤드)
- [ ] `sungjwa_hunter_sim` 어댑터 (ChaosRNG ↔ CPoW entropy)
- [ ] JSON 스키마 검증 (`config/cpow_schema.json`)
- [ ] 네트워크 전송 프로토콜 (WebSocket 패치 스트림)
