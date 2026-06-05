# 07 — 콘텐츠 로드맵

## 현재 (v0.9 — 시즌 1 코어)

| 영역 | 수량 | 상태 |
|------|------|------|
| 이벤트 씨앗 | ~151 | ✅ |
| 메인 3단계 | 1 story | ✅ |
| 동맹 분기 | 5+3+5 climaxes | ✅ |
| NPC 핵심 | 6+ | ✅ |
| 지역 | ashpoint, forest, tower | ✅ |
| 유닛 테스트 | 137+ | ✅ |

## Phase Nex — BCI×Mnemosyne (설계 → 구현)

| 단계 | 내용 |
|------|------|
| Nex-0 | `09`·`10` 문서, `bci_meta.schema`, narrator 육감 가이드 ✅ |
| Nex-1 | `flags.bci_meta` + Guardian disconnect |
| Nex-2 | Mnemosyne rumor / NPC memory tick |
| Nex-3 | `[체감]` 턴 훅, interoception + `rest` |
| Nex-4 | R4 앵커 미니게임, 시즌3 Mnemosyne 음모 |

## Phase A — VR 메타 최소 (2–3주 개발 상당)

- [ ] `flags.vr_meta` 샤드 + 로비 씬 3종
- [ ] `prompts/narrator_claude.md` 풀다이브 감각 가이드
- [ ] `status`에 세션 시간·고통 캡 표시
- [ ] 강제 disconnect 복구 턴

## Phase B — 세계 확장 (시즌 1.5)

| 콘텐츠 | 씨앗 +20 | lore |
|--------|----------|------|
| 블랙팽 협곡 | raid, ambush | `lore/locations/blackfang_gorge.md` |
| 우물 미궁 | horror 5 | night-only |
| 상인 캐러밴 | trade escort | `silverwood_trade_union` |

## Phase C — 시즌 2 「봉인 너머」

- 새 `main_stories` entry `beyond_ashen_seal`
- `capital` zone + 실버헤이븐 허브
- Phase 1–3 재사용 패턴 (`_advance_phase_flow` 리팩터 후)
- 시즌 1 결말 import 테이블

| 시즌1 결말 | 시즌2 시작 modifier |
|------------|---------------------|
| seal_maintained | 낮은 tension, 십자 우호 |
| ancient_awakening | 높은 tension, 호러 가중 |
| age_of_chaos | 산적 점령 이벤트 |

## Phase D — 소셜·경제

- 파티: 공유 `flags.party_id`, 인스턴스 던전
- 경제: 경매장 (골드 싱크), 제작 (토렌 확장)
- 길드: `faction_reputation` 가상 7번째 「길드」

## Phase E — 메타 아크 (시즌 3)

- `conspiracy` 메인화
- 「은빛 관리자」 보스 (메타)
- 플레이어 선택: 패치 수용 / 저항 엔딩

## 씨앗 제작 템플릿

```json
{
  "id": "example_vr_hook",
  "title": "…",
  "seed_type": "main_story",
  "main_plot_link": "ashen_seal_cracking",
  "requires_main_story_phase": 2,
  "requires_action": ["talk"],
  "location_zones": ["ashpoint"],
  "weight": 20,
  "outcome": {
    "summary": "한 줄",
    "faction_reputation": {"ashpoint_council": 5},
    "tension_delta": 2,
    "flags_set": {"example_flag": true}
  }
}
```

## 퀘스트 라인

| ID | 역할 | 단계 |
|----|------|------|
| `smoke_on_the_mountain` | 튜토리얼·산 | 1–3 |
| (예정) `covenant_depths` | 서약 던전 | 2 |
| (예정) `warden_archives` | 진실 엔딩 | 2–3 |

## 현지화·접근성

- 기본 언어: 한국어 (이세계 「언어 동화」)
- 고통/호러: 캡 + 필터
- 색각: UI (미래) — 엔진 텍스트는 이미 명확한 명사 위주

## KPI (콘텐츠팀)

| 지표 | 목표 |
|------|------|
| 시즌1 완주율 | 25%+ |
| 2단계 분기 도달 | 80%+ |
| 결말 4종 분포 | 각 10%+ (극단 편중 방지) |
| 평균 플레이 시간 | 8–15h |
