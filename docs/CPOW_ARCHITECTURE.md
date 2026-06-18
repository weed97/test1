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
- **교차·균형**: `crossover.py` (허브·2-hop·환경장), `equilibrium.py` — [PHYSICS_BALANCE.md](PHYSICS_BALANCE.md)
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
  "visual": {
    "glb_url": "https://cdn.example/sword.glb",
    "slot": "weapon",
    "attach_bone": "RightHand"
  },
  "creativity_fingerprint": "a1b2c3..."
}
```

3D 클라이언트(`cpow_client/godot`)용 `visual` 필드 — [cpow_client/godot/docs/CLIENT_ARCHITECTURE.md](../cpow_client/godot/docs/CLIENT_ARCHITECTURE.md)

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

**원칙: 엔진 우선, 블록체인은 은행.** → [CPOW_ROADMAP.md](CPOW_ROADMAP.md)

### Phase 1 — 시뮬레이션 엔진 (최우선)
- [x] 물리 정의 엔진 (`cpow_engine/physics/`)
- [x] CPoW 환산 (`cpow_engine/cpow/`)
- [x] 공유 상태 동기화 (`cpow_engine/shared_state/`)
- [ ] `fantasy_simulator` / Godot 실시간 연동
- [ ] `sungjwa_hunter_sim` 어댑터

### Phase 2 — CPoW 가치화 정교화
- [x] 가중치 튜닝 (`config/cpow_scoring.json`) — [CPOW_PHASE2.md](CPOW_PHASE2.md)
- [x] 봇 시뮬레이션 (`bot_sim/`)
- [x] 레거시 어댑터 (`adapters/`)
- [x] JSON 스키마 검증 (`schema/`, `cpow_schema.json`)

### Phase 3 — 브릿지 (엔진 완성 후)
- [x] L1 레퍼런스 (`cpow_engine/chain/`, `bridge.py`)
- [ ] 프로덕션 브릿지 연동

### Phase 4 — L1 프로토콜 (선택·후순위)
- [x] Genesis 스키마 (`cpow_engine/config/genesis.json`)
- [ ] Cosmos SDK `x/cpow` 또는 롤업 (가치 모델 검증 후)

→ L1 상세: [L1_PROTOCOL_ARCHITECTURE.md](L1_PROTOCOL_ARCHITECTURE.md)
