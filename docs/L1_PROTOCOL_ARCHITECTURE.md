# L1 Protocol Architecture — CPoW 블록체인

## 한 줄 정의

**창조가 에너지가 되고, 물리 법칙이 자산이 되는 프로토콜** — 운영자 개입 없이 합의 알고리즘이 진실(Truth)을 보장하는 L1 기반 계층.

이 문서는 "코인을 만드는 것"이 아니라 **"생태계의 규칙을 프로토콜로 만드는 것"**에 집중합니다.

## 왜 L1이 필요한가

| 목표 | L1이 보장하는 것 |
|------|------------------|
| 신뢰의 자동화 | 화폐·물리 법칙을 운영자가 임의 변경 불가 (불변 코드) |
| 진정한 소유권 | 창조물의 탄생·소유 증명 (Registry) |
| 에너지 가치 정산 | CPoW 점수에 따른 토큰(NRG) 발행이 노드 합의로 투명하게 이루어짐 |

## 하이브리드 아키텍처: 속도 vs 신뢰

```
┌─────────────────────────────────────────────────────────────┐
│                    Off-chain (Game Engine)                   │
│  실시간 물리 연산 · 충돌 · 열 · AI · 렌더링                    │
│  cpow_engine/physics · engine · shared_state                 │
└──────────────────────────┬──────────────────────────────────┘
                           │ 주기적 Submit (Rollup)
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    On-chain (Layer 1)                        │
│  창조물 Registry · 에너지 발행 · 합의 · 자산 장부             │
│  cpow_engine/chain/                                          │
└─────────────────────────────────────────────────────────────┘
```

**원칙**: 블록체인은 '진실(Truth)'만, 엔진은 '현실(Physics)'만 다룬다.

### On-chain (L1)

- 창조물 고유 해시·데이터 구조 저장 (`CreationRegistry`)
- CPoW 점수 기반 에너지 토큰(NRG) 발행 (`MINT_ENERGY` tx)
- 유저 합의 화폐·자산 거래 장부
- Genesis 열역학 법칙 (불변 프로토콜 표준)

### Off-chain (Engine)

- 실시간 물리 연산 (충돌, 열, 전기)
- 환경 상호작용·AI
- 틱 단위 CPoW 점수 계산
- 롤업 배치로 L1 제출 (`RollupSubmitter`)

## Genesis 블록 — 프로토콜의 유전자

Genesis 블록에는 **두 가지 기축 데이터**가 함께 기록됩니다.

### 1. 열역학 법칙 (Protocol Physics) — "이 세계의 DNA"

운영자가 아닌 **프로토콜**이 보장하는 불변 물리 공식. 오프체인 연산의 검증 기준.

```json
{
  "id": "thermo_002",
  "name": "heat_transfer",
  "formula": "heat_transfer",
  "expression": "transfer = heat_intensity * thermal_conductivity * 0.01",
  "immutable": true
}
```

### 2. 초기 신뢰 점수 (Genesis Validators/Creators) — "첫 신뢰의 씨앗"

최초 검증자·창조자에게 부여되는 trust_score. 합의 가중치의 출발점.

```json
{
  "id": "validator_genesis_0",
  "trust_score": 1.0,
  "role": "founding_validator"
}
```

> **결정**: Genesis의 첫 번째 블록은 "열역학 법칙"과 "초기 신뢰 점수"를 **동시에** 담습니다. 법칙은 세계의 물리적 유전자, 신뢰 점수는 경제·합의의 유전자입니다.

설정 파일: `cpow_engine/config/genesis.json`

## 모듈 구조

```
cpow_engine/chain/
├── genesis.py      # Genesis 블록·열역학 법칙·토큰 파라미터
├── block.py        # Block, Transaction, Merkle root
├── registry.py     # 창조물 등록 (소유권 증명)
├── consensus.py    # CPoW 가중 Tendermint-style 합의
├── validator.py    # 봇·중복·에너지 검증
├── rollup.py       # 오프체인 배치 → L1 제출 (가스 최적화)
└── bridge.py       # Off-chain ↔ On-chain 브릿지
```

## 트랜잭션 유형

| TxType | 설명 |
|--------|------|
| `REGISTER_CREATION` | 창조물 fingerprint 온체인 등록 |
| `MINT_ENERGY` | CPoW 점수 기반 NRG 토큰 발행 |
| `SUBMIT_ROLLUP` | 오프체인 틱 배치 Merkle 제출 |
| `PHYSICS_AMENDMENT` | (미래) 거버넌스 통한 법칙 수정 |
| `TRANSFER` | NRG 토큰 이전 |

## 보안: Validator 로직

1. **중복 fingerprint 거부** — 가짜 창조물 에너지 탈취 방지
2. **bot_risk ≥ threshold 거부** — 봇 행동 패턴 탐지
3. **에너지 재계산 검증** — 오프체인 주장 vs 온체인 재검증 (15% 허용 오차)
4. **Genesis formula 검증** — 등록되지 않은 물리 공식 거부

## 가스비 최적화: Rollup

- 오프체인에서 N틱(기본 10)을 `RollupBatch`로 묶음
- Merkle root만 L1에 `SUBMIT_ROLLUP` tx로 제출
- 개별 틱마다 트랜잭션을 내지 않아 가스비 절감

## 프로덕션 로드맵

현재 `cpow_engine/chain/`은 **Python 레퍼런스 구현** (stdlib only, 테스트·프로토타입용).

> **중요**: L1 프로덕션 착수는 Phase 1–2(시뮬레이션 엔진 + CPoW 가치화) 완성 **후**에 진행한다.  
> 블록체인은 게임 엔진이 아니라 가치를 저장하는 **은행**이다.  
> → 상세 로드맵: [CPOW_ROADMAP.md](CPOW_ROADMAP.md)

### Cosmos SDK가 "안 맞는" 이유

Cosmos SDK는 PoS·자산 이동에 최적화. CPoW(창조성·복잡도 검증)와는 기본 철학이 다름.  
그러나 **CometBFT + 커스텀 ABCI(`x/cpow`)** 로 뜯어고치면 소버린 체인으로는 유효.

| 괴리 | Cosmos 기본 | CPoW 필요 |
|------|------------|-----------|
| 검증 대상 | Stake(지분) | 창조성·fingerprint |
| 상태 확정 | 블록 단위 | 실시간 물리(오프체인) |
| 핵심 모듈 | `x/staking` | `x/cpow` (신규) |

### 프레임워크 선택 (Phase 4)

| 전략 | 적합한 경우 |
|------|------------|
| **A: Cosmos SDK + x/cpow** | 완전한 소버린 체인, IBC, 독자 경제권 |
| **B: 롤업 (OP Stack / Orbit)** | 빠른 MVP, ETH 생태계, Solidity 팀 |

**현재 권장**: 어느 쪽도 지금 시작하지 않음. 엔진·CPoW 로직 먼저.

### Cosmos SDK 마이그레이션 (Phase 4 착수 시)

1. `genesis.json` → Cosmos `genesis.json`의 `app_state.cpow` 섹션
2. `CreationRegistry` → `MsgRegisterCreation` + `Keeper`
3. `CPoWConsensus` → Tendermint ABCI + CPoW 가중 투표 확장
4. `RollupSubmitter` → IBC 또는 전용 롤업 존

## 실행

```bash
# L1 + 오프체인 통합 데모
python3 -m cpow_engine.demo --chain --seed 42 --ticks 5

# L1 프로토콜 테스트
python3 -m unittest cpow_engine.tests.test_chain -v
```

## Cursor 설계 프롬프트 예시

> CPoW 기반 L1을 설계한다. 창조물 Registry, CPoW 가중 합의, Rollup 배치 제출, Validator 중복·봇 검증을 구현하라. Genesis에는 열역학 법칙과 초기 신뢰 점수를 함께 기록한다.
