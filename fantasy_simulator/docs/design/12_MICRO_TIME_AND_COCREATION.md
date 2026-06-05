# 12 — 초정밀 시간 & 공동 창조

## 목표

| 요구 | 설계 응답 |
|------|-----------|
| 「1 비트 ≈ 1분」 체감 | `temporal_mode="precision"` + `world.minute_of_day` |
| 시간을 철저히 | CLI `[시각 HH:MM]`, 상태창 시계, 일자·주기 동기 |
| 유저가 세계를 만든다 | `flags.world_building` + 기록 비석·워크숍 루프 |
| 현실에서 못 하는 것 | [13_ISEKAI_AFFORDANCES.md](13_ISEKAI_AFFORDANCES.md) |

## Precision 모드 (T1.5)

```mermaid
flowchart LR
  Intent[플레이어 의도] --> Classify[classify_moment]
  Classify --> Minutes[resolve_time_minutes]
  Minutes --> Clock[advance_world_minutes]
  Clock --> Sync[time_of_day + day]
```

### 분 단위 기본표

| Moment | 분 | 비고 |
|--------|-----|------|
| glance | 0 | 시선·귀 기울이기 |
| step | 1 | 최소 이동 비트 |
| talk | 5 | 대화 |
| investigate | 8 | 조사 |
| explore | 5 | 탐색 |
| travel | 15 | 구역 이동 |
| combat | 3 | 교전 비트 |
| rest | → 06:00 | `advance_to_morning` |

`time_scale` 로 전체 배율 조절 (0.5 = 절반 속도).

### CLI

```bash
python3 simulation_engine.py -i --precision
```

Classic(`기본`)은 **라우트 클리어 테스트**용 — Precision은 플레이·몰입용.

### 코드

| 모듈 | 역할 |
|------|------|
| `utils/world_clock.py` | `minute_of_day`, `format_clock`, 일자 롤오버 |
| `utils/temporal.py` | `resolve_time_minutes`, `format_clock_line` |
| `utils/rule_engine.py` | `advance_time_minutes`, 레거시 마이그레이션 |

## 공동 창조 (Co-creation) 루프

플레이어가 **세계를 실제로 확장**하도록 유도하되, Mnemosyne·운영자가 품질을 지킨다.

1. **발견** — 플레이 중 「기록 비석」「빈 제단」 등 월드빌딩 훅 노출  
2. **제안** — Link OS 워크숍에서 씨앗 초안 (대화·퀘스트·소문)  
3. **검증** — lore 일관성·R3 육감·메인 스토리 충돌 자동 스코어  
4. **반영** — `flags.world_building.approved_seeds` → `events/seeds/community_*.json`  
5. **기념** — 게임 내 비석·NPC 대사에 기여자 서명 (opt-in)

엔진 훅 (T1): `flags.world_building` — **기여도·티어·권한·성장 목표** 는 [14_CONTRIBUTION_PERMISSIONS.md](14_CONTRIBUTION_PERMISSIONS.md) 참고.

| 모듈 | 역할 |
|------|------|
| `config/contributor_tiers.json` | 티어·점수·성장 목표·seed_limits |
| `utils/contrib_permissions.py` | `can()`, `award_contribution()`, `tier_progress()` |

T2+: BCI 「이 장면을 남기고 싶다」 제스처 → 동일 파이프라인.

## 다음 단계

- T2 `presence_tick(dt)` — 분 시계는 멈추지 않고 주변만 흐름  
- T3 RTwP 전투 — combat moment를 초 단위 서브비트로 분해  
- 커뮤니티 씨앗 PR 템플릿 + `test_community_seed_lint.py`
