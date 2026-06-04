# Lore & Events (메모리 효율 콘텐츠)

`world_state.json` / `state/`에는 **상태값만**. 서사·대사·상세 묘사는 여기.

## 구조

```
lore/
  npcs.md              # NPC 상세 (외형, 성격, 비밀, 대사)
  locations/
    ashpoint.md        # 지역 묘사

events/
  seeds.json           # 이벤트 씨앗 카탈로그 (ID + summary + hook)

characters/
  torren_blacksmith.json   # 엔진용 최소 stat + lore_ref
  lilian_innkeeper.json
  grey_cloak.json
```

## world_state에 넣는 것 (최소)

- `world`: day, time, location, tension, **rumors** (한 줄씩)
- `flags.pending_events`: 씨앗 ID 목록만 (`["plaza_song", ...]`)
- `npc_locations`: NPC ID → 위치 문자열
- `event_log`: 최근 N턴만 (요약 한 줄)

## world_state에 넣지 않는 것

- NPC 긴 묘사, 대사 전문
- 지역 상세 설명
- 이벤트 전체 시나리오

## LLM에 전달

`StateManager.snapshot()`이 필요할 때만 `ContentLoader`로 불러옴:

- `narrative_context.location_lore`
- `narrative_context.npc_lore`
- `narrative_context.event_seeds` (pending_events ID → seeds.json)

플레이어가 `talk to torren` 등으로 행동하면 키워드 라우터 → Claude + snapshot에 해당 lore 포함.

## 씨앗 이벤트 소비

이벤트가 발생하면 `flags.pending_events`에서 ID를 제거하고 `event_log`에 한 줄 요약만 추가.

## 퀘스트 & 평판 (`flags` 샤드)

```json
"reputation": {"ashpoint": 50, "torren": 0, "lilian": 5},
"quests": {"active": "smoke_on_the_mountain", "stage": 1, "completed": []}
```

- **퀘스트 카탈로그:** `events/quests.json`
- **스토리 bible:** `lore/quests/smoke_on_the_mountain.md`
- **대사 풀:** `events/dialogues.json`

## Act 2 — 북쪽 숲 / 관측탑 (quest stage 3+)

`investigate forest` (stage 2→3) 시 **숲 전용 씨앗 5개**가 `pending_events`에 추가됩니다.

| seed id | 트리거 | 내용 |
|---------|--------|------|
| broken_rune_pillar | explore/investigate | 룬 기둥 발견 |
| tower_whisper | explore/rest (밤) | 탑 속삭임 |
| mold_in_moss | explore (torren_side_quest) | 주조금형 (사이드) |
| seal_drip | investigate | 봉인 액체 |
| sentinel_stirring | explore | 룬 센티넬 전투 힌트 |

- **mini-boss:** `combat rune_sentinel` → `seal_fragment_obtained`
- **boss:** `combat silver_stalker` (파편 획득 후)

## 사이드 퀘스트

- `torren_lost_mold`: torren_commission → 숲에서 mold_in_moss → talk torren

## 대사 (stage-aware)

`events/dialogues.json` v2 — `by_quest_stage`, `by_flag` 풀.  
`ContentLoader.load_npc_dialogues(npc_id, state)`가 퀘스트 stage에 맞는 대사 선택.

## CLI 예시

```
talk torren
investigate well
investigate forest
investigate tower
quest
combat rune_sentinel
combat silver_stalker
```
