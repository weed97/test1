# CPoW 개발 로드맵 — 엔진 우선, 블록체인은 은행

## 핵심 원칙

> **게임을 블록체인에 올리는 것이 아니라, 창조 증명(CPoW)을 위한 장부를 만드는 것.**  
> 블록체인은 게임을 돌리는 엔진이 아니라, 게임 속 가치를 저장하는 **은행**이다.

이 문서는 "지금 당장 L1을 만들어야 하는가?"에 대한 답입니다.  
**답: 아니오. 시뮬레이션 엔진과 CPoW 가치 산정 로직을 먼저 완성한다.**

---

## 왜 Cosmos SDK가 "안 맞는" 느낌이 드는가

Cosmos SDK는 **자산 이동 + 지분 증명(PoS)** 에 최적화되어 있습니다. CPoW 비전과의 괴리:

| Cosmos SDK 기본 철학 | CPoW 비전 |
|---------------------|-----------|
| 블록 단위 상태 확정 (Finality) | 실시간 물리 상호작용 |
| Stake(지분) 검증 | 창조성·복잡도 검증 |
| `x/staking`, `x/bank` 중심 | `x/cpow` 커스텀 필요 |
| 검증자 = 토큰 보유량 | 검증자 = 창조 데이터 품질 판단 |

**결론**: Cosmos SDK를 그대로 쓰면 안 맞습니다.  
하지만 **CometBFT 합의 + ABCI 커스텀 앱**으로 뜯어고치면 소버린 체인으로는 여전히 유효한 선택지입니다.

---

## 현실적인 4단계 로드맵

```
Phase 1 ──→ Phase 2 ──→ Phase 3 ──→ Phase 4
시뮬레이션     CPoW 가치화      브릿지           L1 프로토콜
엔진 MVP      로직 정교화      (은행 붙이기)     (선택·후순위)
[지금 여기]    [다음]           [엔진 완성 후]    [가치 검증 후]
```

### Phase 1: 시뮬레이션 엔진 (현재 — 최우선)

**목표**: 창조하고, 에너지를 얻고, 협력하는 **재미**를 코드로 구현.

| 모듈 | 상태 | 내용 |
|------|------|------|
| `cpow_engine/physics/` | ✅ MVP | 속성 정의 → 상호작용 |
| `cpow_engine/cpow/` | ✅ MVP | CPoW 점수·봇 억제 |
| `cpow_engine/shared_state/` | ✅ MVP | 충돌 병합 |
| `cpow_engine/engine.py` | ✅ MVP | 틱 루프 |
| `cpow_engine/xr/` | ✅ MVP | XR 제스처 → CreativeObject |
| `cpow_engine/collab/` | ✅ MVP | 협동 오픈월드 + 노이즈 감쇄 — [COLLABORATIVE_WORLD.md](COLLABORATIVE_WORLD.md) |
| `cpow_engine/areas/` | ✅ MVP | 창조·모험·창조모험 에리어 — [AREA_MODES.md](AREA_MODES.md), [CREATION_DESTRUCTION_POWERS.md](CREATION_DESTRUCTION_POWERS.md) |
| Godot OpenXR 클라이언트 | ✅ MVP | `world_xr.tscn` — [XR_INTEGRATION.md](XR_INTEGRATION.md) |

```bash
python3 -m cpow_engine.demo --seed 42 --ticks 5
python3 -m cpow_engine.demo --collab --ticks 3
python3 -m cpow_engine.demo --areas
```

### Phase 2: CPoW 가치화 정교화

**목표**: "이 오브젝트가 창의적인가?" 판단 로직을 엔진 안에서 다듬기.

- [ ] 복잡도·상호작용 밀도·엔트로피 가중치 튜닝
- [ ] 봇 시뮬레이션 테스트 ("봇이 들어오면 어디가 취약한가?")
- [ ] `fantasy_simulator` / `sungjwa_hunter_sim` 어댑터
- [ ] JSON 스키마 검증 (`config/cpow_schema.json`)

**이 단계가 완성되기 전에는 L1 작업을 시작하지 않는다.**

### Phase 3: 브릿지 (은행 붙이기)

**목표**: 엔진 점수 → 온체인 장부 변환. 게임 로직은 오프체인 유지.

| 구현 | 상태 | 역할 |
|------|------|------|
| `cpow_engine/chain/bridge.py` | ✅ 레퍼런스 | 오프체인 → 온체인 제출 |
| `cpow_engine/chain/rollup.py` | ✅ 레퍼런스 | 배치 Merkle 제출 |
| `cpow_engine/chain/registry.py` | ✅ 레퍼런스 | 창조물 소유권 증명 |
| 프로덕션 브릿지 | 🔲 | 엔진 완성 후 |

```bash
python3 -m cpow_engine.demo --chain --seed 42 --ticks 5
```

### Phase 4: L1 프로토콜 (선택·후순위)

**목표**: 운영자 없는 자율 생태계를 위한 불변 장부.  
**전제**: Phase 1–2에서 가치 산정이 검증된 후에만 착수.

---

## L1 프레임워크 비교

### 전략 A: Cosmos SDK + 커스텀 ABCI (소버린 체인)

```
CometBFT (합의·P2P·보안)  ←── 그대로 사용
        │
        ABCI
        │
x/cpow (커스텀)           ←── x/staking 대체/병행
  - MsgRegisterCreation
  - MsgMintEnergy
  - MsgSubmitRollup
```

| 장점 | 단점 |
|------|------|
| 독자 물리 법칙·합의 정의 가능 | PoS 모듈 제거·CPoW 모듈 신규 개발 필요 |
| 검증된 P2P·보안 (10년+ 개발 절약) | Go 생태계, 팀 역량 필요 |
| IBC로 다른 체인 연동 | 실시간 물리는 반드시 오프체인 |

**적합한 경우**: 완전한 소버린 체인, 독자 경제권이 필요할 때.

### 전략 B: 롤업 (OP Stack / Arbitrum Orbit)

```
이더리움 (보안·결산)
        │
   L2/L3 앱체인
        │
 CPoW 스마트 컨트랙트
```

| 장점 | 단점 |
|------|------|
| 이더리움 보안 상속 | 이더리움 생태계 종속 |
| 스마트 컨트랙트로 보상 로직 구현 용이 | 완벽한 독자 노선 아님 |
| 빠른 프로토타입 | 가스비·EVM 제약 |

**적합한 경우**: 빠른 MVP, 기존 Web3 유저 유입, ETH 생태계 활용.

### 권장 결정 기준

| 질문 | Cosmos SDK | 롤업 |
|------|-----------|------|
| 완전한 독자 체인이 필요한가? | ✅ | ❌ |
| 6개월 내 프로토타입이 필요한가? | ❌ | ✅ |
| Go/Rust 팀이 있는가? | ✅ | ❌ (Solidity) |
| IBC 크로스체인이 필요한가? | ✅ | 제한적 |

**현재 시점 권장**: 어느 쪽도 **지금 시작하지 않음**.  
Phase 1–2 완성 후, 가치 모델이 검증되면 전략 A 또는 B를 선택.

---

## 아키텍처 불변 원칙

이 원칙은 프레임워크 선택과 무관하게 유지됩니다.

1. **오프체인 = Physics** — 실시간 물리·AI·렌더링
2. **온체인 = Truth** — Registry, 에너지 발행, 소유권
3. **제출(Submit) ≠ 실행** — 엔진이 계산, 체인이 검증·기록
4. **Rollup 필수** — 틱마다 tx 내지 않음, 배치 Merkle 제출
5. **PoS ≠ CPoW** — Stake가 아닌 창조성·복잡도로 가치 산정

```
┌─────────────────────────────────────────┐
│  Off-chain Engine (재미·창의성·물리)      │
│  cpow_engine/physics · engine · cpow     │
└──────────────────┬──────────────────────┘
                   │ RollupBatch (주기적)
                   ▼
┌─────────────────────────────────────────┐
│  On-chain Ledger (은행·장부·소유권)       │
│  Registry · NRG 발행 · 합의              │
└─────────────────────────────────────────┘
```

---

## Cursor 프롬프트 (Phase 4 착수 시)

> 창조물(Creativity)을 자산화하는 블록체인을 설계한다. PoS가 아닌 CPoW 합의 모델.  
> x/staking을 제거하고 x/cpow 모듈 구조를 제안하라.  
> 게임 물리는 오프체인, 창조 데이터(해시·점수)만 온체인 Submit/검증.  
> Cosmos SDK vs 롤업 중 이 프로젝트에 적합한 프레임워크를 비교하라.

---

## 관련 문서

- [CPOW_ARCHITECTURE.md](CPOW_ARCHITECTURE.md) — 엔진 3대 모듈
- [L1_PROTOCOL_ARCHITECTURE.md](L1_PROTOCOL_ARCHITECTURE.md) — L1 레퍼런스 구현
- [../cpow_engine/config/genesis.json](../cpow_engine/config/genesis.json) — Genesis 스키마
