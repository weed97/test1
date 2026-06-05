# 28 — 병렬 비트 (Parallel Beat)

## 왜 필요한가

생태 모드에서는 NPC·몬스터·건설자가 **같은 순간**에 움직이는 것처럼 보여야 한다. OS 스레드 병렬이 아니라 **논리적 병렬**:

1. **Plan** — 모든 에이전트가 의도만 기록 (월드 변경 없음)
2. **Resolve** — 같은 타겟에 대한 타격을 합산, 이동 충돌은 우선순위로 정리
3. **Commit** — 한 번에 상태 반영
4. **Macro** — 문명·전쟁·플레이어 건설 등 맵 단위 레인 (같은 턴 스냅샷)

Godot는 턴 종료 후 `GET /v1/world/agents` 스냅샷을 받되, **연출만** 시간축으로 어긋낸다.

## 규칙 동시 vs 연출 따로 (lock-step 방지)

| 층 | 동작 |
|----|------|
| **시뮬** | Plan → Resolve → Commit **한 번** (공정한 동시 타격) |
| **연출** | `presentation_schedule[]` 의 `delay_ms` 로 이동·타격 트윈을 **0~480ms** 분산 |
| **팩** | `group_by_pack: true` → 무리는 비슷한 타이밍, 팩끼리는 다른 wave |
| **전투** | 같은 `target_id` 는 `combat_sync_window_ms` 안에서만 모음 → “한꺼번에 패임”은 유지, 배회와는 다른 리듬 |

Godot 예: `tween_delay = schedule[actor_id].delay_ms / 1000.0` 후 위치/애니 적용.  
**비트 사이**에는 서버와 무관하게 idle·ambient·시선만 Godot에서 돌리면 “각자 노는” 느낌이 살아난다.

`subticks_per_moment > 1` 은 시뮬 자체를 여러 미세 비트로 쪼개는 옵션(후속). 연출만으로 부족할 때 검토.

## 설정

- `config/parallel_beat.json`
- `flags.ecology.parallel_beat` — 세션별 on/off (없으면 ecology 기본값 `enabled_by_default_in_ecology`)

## 틱 경로

| 모드 | 진입점 |
|------|--------|
| Ecology + parallel | `tick_world_systems` → `run_world_parallel_beat` |
| Ecology + sequential | `tick_field_ecology` (순차 `tick_agent_mind`) + macro |
| Field only | `tick_field_ecology` — parallel이면 `tick_field_ecology_parallel` + `tick_agent_competition` |

## 전투 규칙 (필드)

- 동일 `target_id`에 대한 `attack`/`skill` 플랜을 모아 **피해 합산** 후 한 번에 HP 차감
- `max_attackers_per_target`, `simultaneous_damage_scale`로 밸런스 조절
- 스킬은 `preview_skill_damage` + `commit_skill_costs`로 이중 적용 방지

## API / 상태 힌트

- `flags.ecology.beat_mode` — `"parallel"` | (미설정 시 sequential)
- `flags.ecology.last_parallel_beat` — `{ map_id, plans, survivors, presentation_schedule, presentation_duration_ms }`
- `GET /v1/world/agents` → `beat_presentation` (클라이언트용 요약)
- `flags.ecology.last_macro_parallel` — macro 레인 메타

## 관련 문서

- `11_TEMPORAL_MODEL.md` — 턴 vs 체감 동시성
- `27_*` — ecology_agent / 지성
