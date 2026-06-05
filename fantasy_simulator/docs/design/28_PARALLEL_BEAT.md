# 28 — 병렬 비트 (Parallel Beat)

## 왜 필요한가

생태 모드에서는 NPC·몬스터·건설자가 **같은 순간**에 움직이는 것처럼 보여야 한다. OS 스레드 병렬이 아니라 **논리적 병렬**:

1. **Plan** — 모든 에이전트가 의도만 기록 (월드 변경 없음)
2. **Resolve** — 같은 타겟에 대한 타격을 합산, 이동 충돌은 우선순위로 정리
3. **Commit** — 한 번에 상태 반영
4. **Macro** — 문명·전쟁·플레이어 건설 등 맵 단위 레인 (같은 턴 스냅샷)

Godot는 턴 종료 후 `GET /v1/world/agents` 스냅샷을 한꺼번에 그리면 “동시에 일어난” 느낌을 낼 수 있다.

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
- `flags.ecology.last_parallel_beat` — `{ map_id, plans, survivors }`
- `flags.ecology.last_macro_parallel` — macro 레인 메타

## 관련 문서

- `11_TEMPORAL_MODEL.md` — 턴 vs 체감 동시성
- `27_*` — ecology_agent / 지성
