# CPoW Simulation Engine

> **이 프로젝트는 게임이 아닙니다.**  
> 유저의 창조적 데이터(오브젝트·물리 정의)가 시스템 상태를 변화시키는 **데이터 창조 기반의 자율 시뮬레이션 엔진**입니다.

## 한 줄 정의

**CPoW (Creativity-Proof of Work) 시뮬레이션 엔진** — 물리 법칙을 하드코딩하지 않고, 유저가 정의한 속성 데이터가 실시간으로 상호작용하며, 창조 행위가 에너지·가치로 환산되는 자율 시뮬레이션 시스템.

## 핵심 모듈

| 모듈 | 경로 | 설명 |
|------|------|------|
| **물리 정의 엔진** | `cpow_engine/physics/` | HeatSource, Material, EnergyTransfer 등 속성 조합 → 물리적 결과 |
| **CPoW 환산 엔진** | `cpow_engine/cpow/` | Action Data + World Delta → 에너지·경제 점수 (봇 억제 휴리스틱 포함) |
| **공유 상태 동기화** | `cpow_engine/shared_state/` | 다중 유저 물리 정의 충돌 시 Merge/Negotiation 프로토콜 |
| **L1 프로토콜** | `cpow_engine/chain/` | Genesis, Registry, Consensus, Validator, Rollup, Bridge |
| **XR 브릿지** | `cpow_engine/xr/` | 공간 제스처 → CreativeObject 변환 |

## 빠른 실행 (MVP)

```bash
# CPoW 엔진 데모: Heat 속성 오브젝트 생성 → 에너지 발생
python3 -m cpow_engine.demo --seed 42 --ticks 3

# L1 프로토콜 통합 데모: 오프체인 연산 → 온체인 제출
python3 -m cpow_engine.demo --chain --seed 42 --ticks 5

# 단위 테스트
python3 -m unittest discover -s cpow_engine/tests -v
```

## 설계 원칙

1. **기능(Function) vs 콘텐츠(Data)** — 엔진은 함수만 제공, 법칙·도구는 데이터 구조.
2. **동적 상태** — State는 오브젝트 생성·연결에 따라 매 틱마다 변화.
3. **엔트로피 기반 보상** — 단순 반복(작업장)은 낮은 점수, 고유한 창조물은 높은 점수.
4. **속성 치환** — `파이어볼` 스킬 대신 `heat_intensity` 속성 오브젝트.

## 레거시 프로젝트 (전환 중)

기존 판타지 시뮬레이터는 **인프라 뼈대**(에셋 로더, UI, Auth)만 유지하고, 하드코딩된 게임 로직(몬스터 스탯, 스킬 리스트, 강화 공식)은 CPoW 속성 시스템으로 점진 전환합니다.

| 경로 | 상태 | 비고 |
|------|------|------|
| `cpow_engine/` | **핵심 엔진** | CPoW 시뮬레이션 (신규) |
| `fantasy_simulator/` | 전환 중 | Eldoria — Godot 클라이언트·API 뼈대 유지 |
| `sungjwa_hunter_sim/` | 전환 중 | 성좌 헌터 — CPoW 어댑터 연동 예정 |
| `item_catalog/` | 유지 | 아이템 도감 UI |
| `mmorpg_sim/`, `fantasy_mmorpg/` | 레거시 | 텍스트 MMORPG 참고용 |

## 개발

- Cursor 규칙: [`.cursorrules`](.cursorrules)
- 에이전트 가이드: [`AGENTS.md`](AGENTS.md)
- 아키텍처 상세: [`docs/CPOW_ARCHITECTURE.md`](docs/CPOW_ARCHITECTURE.md)
- L1 프로토콜: [`docs/L1_PROTOCOL_ARCHITECTURE.md`](docs/L1_PROTOCOL_ARCHITECTURE.md)
- **개발 로드맵**: [`docs/CPOW_ROADMAP.md`](docs/CPOW_ROADMAP.md) — 엔진 우선, 블록체인은 은행
- **XR 활용**: [`docs/XR_INTEGRATION.md`](docs/XR_INTEGRATION.md) — Godot OpenXR 연동
