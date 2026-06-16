# 시스템 거버넌스 — 공동발의 · 전체 공지 · 창조력 우위 투표

## 원칙

| 레이어 | 규칙 |
|--------|------|
| **오브젝트 창조** | 구성원 간 **자유** (기존 합의·법칙 적용) |
| **시스템 규칙** | 매크로 방지·창조적 파괴·선거/전쟁 등 — **공동 발의 + 투표** 필수 |

한 명의 창조가가 시스템을 독단적으로 만들 수 없습니다.

## 발의 단계

```
1. 초안 (drafting)     — 100+ 창조자 구성 (composer 서명)
2. 공동발의 (cosponsoring) — 1000+ 구성원 cosponsor
3. 전체 공지 (announced)   — 모든 유저에게 공지
4. 투표 (voting)       — 찬성/반대
5. 시행 (enacted) / 기각 (rejected)
```

테스트·소규모 환경에서는 `GovernancePolicy`로 임계값을 낮출 수 있습니다.

## 투표권

**창조력 > 파괴력** 인 구성원만 투표 가능:

```
creation_gauge + creation_data_score  >  destruction_gauge + destruction_penalty
```

파괴력이 높은 구성원은 **창조적 파괴 시스템** (`creative_destruction`) 발의에 참여해  
「시스템이 무너지지 않는 선에서 파괴를 창조적으로」 설계합니다.  
단, 최종 투표는 창조 우위 구성원이 합니다.

## 독점 방지

- 동일 주도자가 활성 발의에서 과도한 비중 → 차단
- 시행된 시스템이 한 종류에 85% 이상 쏠리면 `system_monopolized` — 신규 발의 제한

## 시스템 종류 예시

| kind | 용도 |
|------|------|
| `macro_bot_defense` | 매크로·봇 방지 |
| `creative_destruction` | 창조적 파괴 규칙 |
| `election_war` | 선거전·전쟁 시스템 |
| `custom` | 기타 공동 규칙 |

## API

```bash
POST /v1/governance/draft      {"author_id","kind","title","spec":{}}
POST /v1/governance/compose    {"proposal_id","user_id"}
POST /v1/governance/cosponsor  {"proposal_id","user_id"}
POST /v1/governance/vote       {"proposal_id","user_id","approve":true}
POST /v1/governance/tick       # 공지→투표 전환
GET  /v1/governance/state
```

## 모듈

```
cpow_engine/areas/governance.py
cpow_engine/areas/registry.py   # GovernanceLedger 통합
```
