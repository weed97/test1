# 에리어 규모 · 파괴력 부여 · NPC · 지배

## 핵심

| 기능 | 설명 |
|------|------|
| **오브젝트 파괴력 부여** | 유저 `destruction_gauge` → 오브젝트 `imbued_destruction` |
| **NPC + 창조력** | NPC 생성 후 창조력 위임, 작업 지시 (농사 등) |
| **에리어 규모** | 넓을수록 파괴력 부여 상한·내구도 상한 증가 |
| **지배** | 작은 에리어의 파괴력은 큰 에리어에 눌림 |

## 파괴력 부여

```
유저 파괴력 → imbue → 오브젝트 imbued_destruction
파괴 저항 = durability + imbued×0.85 + extent보너스
```

상한 = `min(개인 파괴력 티어, 에리어 규모 상한)`

**큰 파괴 유닛**을 만들려면:
1. 본인 `destruction_gauge_max`가 높아야 하거나
2. `expand_area`로 에리어를 넓혀 `area_extent`를 키운다

## NPC 농사

```
spawn_npc → allocate 창조력 → set_task: farm → npc/tick
```

NPC는 에리어 **허용 작업**만 수행 (`farm`, `guard`).  
창조력은 주인에게서 위임받은 `creation_gauge`만 사용.

## 에리어 간 지배

```
dominance_ratio = local_extent / foreign_extent
```

작은 에리어(`extent` 낮음)의 `imbued_destruction`은 큰 에리어 대비  
`effective_imbued_power`로 감쇄된다 — 작은 땅의 파괴 유닛은 큰 땅에 눌린다.

## API

```bash
POST /v1/areas/imbue          {"area_id","actor_id","object_id","amount"}
POST /v1/areas/spawn_npc      {"area_id","owner_id","label"}
POST /v1/areas/npc/allocate   {"area_id","owner_id","npc_id","amount"}
POST /v1/areas/npc/task       {"area_id","owner_id","npc_id","task":"farm"}
POST /v1/areas/npc/tick       {"area_id"}
POST /v1/areas/expand         {"area_id","actor_id"}
GET  /v1/areas/dominance      ?area_id_a=...&area_id_b=...
```

## 모듈

```
cpow_engine/areas/extent.py
cpow_engine/areas/imbue.py
cpow_engine/areas/npcs.py
cpow_engine/areas/dominance.py
```
