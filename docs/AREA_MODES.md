# 창조 에리어 — 창조모드 · 모험모드 · 창조모험

## 한 줄 답

**가능합니다.** 초기 창조자가 **에리어(영역)** 를 열고 그 안의 **법칙**을 정하면, 다른 사람들은 그 틀 안에서 **협력 창조** 또는 **모험**을 할 수 있습니다. 에리어가 커지면 **지역 경제·문명 단계**가 자동으로 올라갑니다.

## 세 가지 모드

| 모드 | 코드 | 누가 무엇을 |
|------|------|-------------|
| **창조 모드** | `creation` | 창시자가 법칙·열원·재료 틀을 세움. 협력자만 함께 창조 |
| **모험 모드** | `adventure` | 창조된 틀 안에서 탐험·상호작용. 직접 대형 창조는 제한 |
| **창조모험 모드** | `creation_adventure` | 창시자 + 협력자가 펄스마다 함께 키우고, 모험가는 작은 기여·탐험 |

```
창시자(aria) ──found──→ 에리어 + 법칙 + 심장(열원)
       │
       ├── 협력자(bob) ──create──→ 재료·연결 (펄스 큐)
       └── 모험가(carol) ──adventure──→ explore / interact / contribute(불씨)
                    │
                    ▼
              펄스 → 함께 반영 → 경제·문명 성장
```

## 합의 & 법칙 검증

**새 오브젝트**는 구성원 **합의(과반 승인)** 후에만 세계에 반영됩니다.  
법칙 위반 시도는 **감쇄 없이 즉시 거부**됩니다 (버그·해킹 방지).

```
제안(create) → 법칙 검증 ─실패→ 거부 (law_violation)
                │
               통과
                ▼
           합의 투표 ─거부→ 폐기
                │
              승인
                ▼
           펄스 → 월드 반영
```

### 법칙 검증 (하드 블록)

| 검사 | 거부 코드 |
|------|-----------|
| 허용 속성 화이트리스트 | `forbidden_property` |
| heat 상한 초과 | `heat_exceeds_law_limit` |
| NaN/Inf | `non_finite_value` |
| 필수 속성 누락 | `missing_required_property` |
| 창조 심장 위조 | `forbidden_area_seed` |

### 합의 API

```bash
# 창조 제안 (합의 대기 가능)
POST /v1/areas/create  {...}

# 투표
POST /v1/areas/vote  {
  "area_id": "area_...",
  "voter_id": "aria",
  "proposal_id": "prop_...",
  "approve": true
}
```

## 역할

| 역할 | 창조 | 모험 | 오브젝트 변형 |
|------|------|------|----------------|
| `founder` 창시자 | ✓ (넓은 한도) | ✓ | ✓ grow/shrink/destroy 전체 |
| `collaborator` 협력자 | ✓ (협동 펄스) | ✓ | ✓ 변형·파괴 (심장 제외) |
| `adventurer` 모험가 | ✗ (기여만) | ✓ | 자기가 만든 것만 소규모 |
| `observer` 관찰자 | ✗ | ✗ | ✗ |

## 에리어 법칙 (`area_templates.json`)

템플릿별로 물리 상수·허용 창조 타입·펄스 리듬이 다릅니다.

| 템플릿 | 모드에 적합 | 특징 |
|--------|-------------|------|
| `foundry` | creation | 높은 열 한도, 느린 펄스 — 틀 세우기 |
| `wilderness` | adventure | 탐험·연결 중심, 낮은 열 한도 |
| `settlement` | creation_adventure | 균형 잡힌 협동 정착지 |

## 지역 경제·문명

오브젝트·기여자·에너지·틱이 쌓이면 `civilization_level` 이 오릅니다.

| 단계 | 이름 | 해금 시스템 |
|------|------|-------------|
| 0 | 황야 | — |
| 1 | 모닥불 거점 | `energy_exchange` |
| 2 | 작업장 | `material_craft` |
| 3 | 정착지 | `collab_governance` |
| 4 | 교역 거점 | `regional_trade` |
| 5 | 문명 권역 | `civilization_protocol` |

## API

```bash
# 에리어 개척 (창시자)
POST /v1/areas/found  {
  "founder_id": "aria",
  "label": "불의 정원",
  "mode": "creation_adventure",
  "template": "settlement"
}

# 참가
POST /v1/areas/join  {"area_id": "area_...", "creator_id": "bob"}

# 창조 (모드·역할에 따라 허용)
POST /v1/areas/create  {
  "area_id": "area_...",
  "creator_id": "bob",
  "type": "material",
  "label": "철괴",
  "material": "iron"
}

# 모험 행동
POST /v1/areas/adventure  {
  "area_id": "area_...",
  "actor_id": "carol",
  "action": "explore"
}

# 구성원 오브젝트 변형
POST /v1/areas/mutate  {
  "area_id": "area_...",
  "actor_id": "bob",
  "object_id": "...",
  "operation": "grow",
  "property_name": "heat_intensity",
  "factor": 1.15
}
POST /v1/areas/mutate  {"operation": "shrink", "factor": 0.85, ...}
POST /v1/areas/mutate  {"operation": "modify", "delta": -10.0, ...}
POST /v1/areas/mutate  {"operation": "set", "value": 80.0, ...}
POST /v1/areas/mutate  {"operation": "destroy", ...}
POST /v1/areas/mutate  {"operation": "rename", "text_value": "공동의 심장", ...}

# 상태·문명·대기 큐
GET /v1/areas/state?area_id=area_...
GET /v1/areas/list
```

## 모듈

```
cpow_engine/areas/
  modes.py      # SimulationMode
  roles.py      # Founder / Collaborator / Adventurer
  laws.py       # AreaLawSet — 지역 물리·펄스 규칙
  economy.py    # RegionalEconomy — 문명·교역
  mutations.py  # 구성원 오브젝트 변형 (grow/shrink/destroy)
  area.py       # CreatedArea
  registry.py   # AreaRegistry
```

## 데모

```bash
python3 -m cpow_engine.demo --areas
```

## 관련

- [COLLABORATIVE_WORLD.md](COLLABORATIVE_WORLD.md) — 빌드 펄스·노이즈 감쇄
- [CPOW_ARCHITECTURE.md](CPOW_ARCHITECTURE.md) — 엔진 3모듈
- `fantasy_simulator/docs/design/14_CONTRIBUTION_PERMISSIONS.md` — 기여도 티어 (향후 연동)
