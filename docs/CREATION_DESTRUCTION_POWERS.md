# 창조력 · 파괴력 — 게이지, 내구도, 균열

## 핵심

모든 유저는 **창조력 게이지**와 **파괴력 게이지**를 동시에 가집니다.

| 파워 | 쓰임 | 세계에서의 위치 |
|------|------|-----------------|
| **창조력** | 합의 확정 창조 시 소비 → `creation_investment`·`durability` 부여 | 창조 데이터 축적 = **플러스** |
| **파괴력** | 확정 오브젝트 파괴 시 `durability`만큼 소비 | 파괴 = **마이너스** (패널티) |

> 창조력이 강한 사람 → 더 단단한 오브젝트 (높은 `durability`)  
> 파괴력이 강한 사람 → 단단한 것도 부술 수 있음 (게이지 ≥ 내구도)

## 흐름

```
창조 제안 → 합의 → 창조력 소비 → is_confirmed + durability
                                    │
파괴 시도 ← 파괴력 ≥ durability? ─no→ 거부
                │
               yes
                ▼
         파괴력 소비 + 창조 패널티 + 균열(rift) + 몬스터 반응
```

## 균열 · 몬스터 · 이주

- 파괴할수록 `rift.level` 상승
- `monster_threat` 높아지면 **파괴자를 추적 공격**
- 에리어 구성원은 **파괴력으로 방어** (`/v1/areas/defend`)
- 균열이 크면 **이주 권고** (`migration_recommended`)
- **핵심 코어** 추출 → 다른 에리어에 복원 가능

## 패널티 해소 — 오직 창조로만

파괴로 쌓인 `destruction_penalty`는 **시간·방어로는 풀리지 않습니다.**  
**합의 확정 창조**를 할 때만 감소합니다.

```
파괴 → destruction_penalty ↑, creation_data_score ↓
창조(확정) → penalty -= creation_spent × 0.55, score 일부 회복
```

큰 피해를 냈다면 **다시 창조해서** 세계에 기여해야 창조 상한과 평판이 돌아옵니다.

패널티로 창조 상한이 줄어든 상태라도, **보유 창조력만큼 부분 창조**로 회복을 시작할 수 있습니다  
(최소 `REDEMPTION_MIN_SPEND` 이상). 여러 번 창조하며 패널티를 조금씩 갚아 나갑니다.

## 오브젝트 파괴력 부여 · NPC · 에리어 규모

유저는 확정 오브젝트에 `imbued_destruction`을 부여할 수 있고, NPC에 창조력을 위임해 농사 등 작업을 시킬 수 있습니다.  
작은 에리어의 파괴력은 큰 에리어에 지배당하며, 강한 파괴 유닛은 **본인 파괴력** 또는 **에리어 확장**이 필요합니다.

자세한 내용: [AREA_EXTENT_NPC.md](./AREA_EXTENT_NPC.md)

## API

```bash
GET  /v1/areas/powers?area_id=...&user_id=bob

POST /v1/areas/mutate   {"operation": "destroy", ...}
POST /v1/areas/defend   {"power_spend": 20}
POST /v1/areas/extract_core
POST /v1/areas/restore_core  {"label": "새 심장"}
POST /v1/areas/migrate
```

## 오브젝트 속성 (확정 후)

| 속성 | 의미 |
|------|------|
| `creation_investment` | 창조력 소비량 |
| `durability` | 파괴에 필요한 파괴력 |
| `is_confirmed` | 합의 확정 (1=파괴 가능) |
| `is_core_facility` | 핵심 시설 (높은 내구도) |

## 모듈

```
cpow_engine/areas/powers.py
cpow_engine/areas/durability.py
cpow_engine/areas/destruction.py
cpow_engine/areas/rift.py
```
