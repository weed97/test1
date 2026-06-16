# 시스템 거버넌스 — 공동발의 · 전체 공지 · 창조력 우위 투표

## 원칙

| 레이어 | 규칙 |
|--------|------|
| **오브젝트 창조** | 구성원 간 **자유** (기존 합의·법칙 적용) |
| **시스템 규칙** | 매크로 방지·창조적 파괴·선거/전쟁 등 — **공동 발의 + 투표** 필수 |

한 명의 창조가가 시스템을 독단적으로 만들 수 없습니다.

## 발의 단계

```
0. 자격 검증           — 긴 흐름 창작만 허용 (단순 spec·봇형 발의 차단)
1. 초안 (drafting)     — 100+ 창조자 구성 (composer 서명, 최소 기간·시간 분산)
2. 공동발의 (cosponsoring) — 1000+ 구성원 cosponsor
3. 전체 공지 (announced)   — 모든 유저에게 공지
4. 투표 (voting)       — 찬성/반대
5. 시행 (enacted) / 기각 (rejected)
```

테스트·소규모 환경에서는 `GovernancePolicy`로 임계값을 낮출 수 있습니다.

## 긴 흐름 창작만 허용 (봇·단순 창작 차단)

거버넌스에 들어가려면 `spec`에 **긴 흐름**이 포함되어야 합니다.  
`{rate_limit: 10}` 같은 단순 키-값만 있으면 `simple_creation_blocked` 로 거부됩니다.

필수 요소 (`LongFlowPolicy` 기본값):

| 항목 | 기본 임계값 |
|------|-------------|
| `rationale` | 120자 이상 |
| `long_flow.steps` 또는 `flow_steps` | 3단계 이상 (`macro_bot_defense`, `election_war`는 4단계) |
| 각 단계 `label` + `description` | 설명 40자 이상 |
| 제목 | 12자 이상 |
| 초안 기간 | 작성 후 최소 300초 경과 후 cosponsoring 전환 |
| 구성 서명 분산 | 첫·마지막 composer 서명 간 최소 60초 |

예시 spec:

```json
{
  "rationale": "매크로 봇이 단순 창조로 생태계를 교란하지 못하도록...",
  "long_flow": {
    "steps": [
      {"label": "관찰", "description": "봇 행동 패턴을 기록하고 분석한다."},
      {"label": "설계", "description": "rate limit과 예외 조항을 문서화한다."},
      {"label": "시범", "description": "소규모 그룹에서 시범 적용한다."},
      {"label": "전면", "description": "전역 적용 전 최종 검토를 완료한다."}
    ]
  },
  "creations_per_window": 2,
  "window_sec": 3600
}
```

거부 시 API 응답: `reason: "simple_creation_blocked"`, `codes` 배열에 세부 사유.

## 살아 있는 에리어 + 실제 영향력 검증

시간 조작만으로 통과하는 봇을 막기 위해, 시스템 발의는 **실제 유저가 체류·공동창작하는 에리어**에서 영향력을 쌓은 구성원만 가능합니다.

`POST /v1/governance/draft` 에 `area_id` 필수.

### 에리어 생태 (`LivingAreaPolicy` 기본값)

| 항목 | 기본 임계값 |
|------|-------------|
| 인간 구성원 | 2명 이상 (NPC 제외) |
| 인간 창조자 수 | 2명 이상 |
| 인간 확정 창조 | 3건 이상 |
| 공동창작 이벤트 | 1건 이상 (합의 투표·공동 펄스·co-create) |
| NPC 창조 비율 | 50% 이하 |

### 구성원 자격

| 항목 | 기본 임계값 |
|------|-------------|
| 인간 확정 창조 | 1건 이상 |
| 창조력 투자 | 10 이상 |
| 공동창작 신호 | 1건 이상 (합의 투표 / co-create / 다인 펄스) |

거부 사유 예: `area_not_living`, `insufficient_area_influence`, `npc_creation_dominates_area`

활동은 `AreaActivityTracker`가 창조 확정·합의 투표·펄스 공동창작 시 자동 기록합니다.

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
POST /v1/governance/draft      {"author_id","area_id","kind","title","spec":{}}
POST /v1/governance/compose    {"proposal_id","user_id"}
POST /v1/governance/cosponsor  {"proposal_id","user_id"}
POST /v1/governance/vote       {"proposal_id","user_id","approve":true}
POST /v1/governance/tick       # 공지→투표 전환
GET  /v1/governance/state
```

## 시행(Enacted) → 런타임 집행

투표로 `enacted` 된 시스템은 `SystemRuntime`에 등록되어 **실제 동작**을 바꿉니다.

| kind | spec 예시 | 런타임 효과 |
|------|-----------|-------------|
| `macro_bot_defense` | `creations_per_window`, `window_sec` | 창조 속도 제한 |
| | `min_creator_cooldown_sec` | CollabPolicy 쿨다운 강화 |
| | `block_npc_creation` | NPC 창조 차단 |
| `creative_destruction` | `max_destroys_per_window` | 파괴 횟수 상한 |
| | `penalty_multiplier` | 파괴 패널티 배율 |
| `election_war` | `cross_destroy_scale` | 교차 파괴 비용 |
| `custom` | `governance_approval_ratio` | 다음 투표 통과 비율 |

`GET /v1/governance/state` → `runtime_rules`, `runtime_enacted`

## 모듈

```
cpow_engine/areas/governance.py
cpow_engine/areas/governance_eligibility.py   # 긴 흐름·에리어 생태 검증
cpow_engine/areas/area_activity.py            # 인간 창작·공동창작 활동 기록
cpow_engine/areas/system_runtime.py   # 런타임 집행
cpow_engine/areas/registry.py
```
