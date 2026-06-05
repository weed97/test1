# 05 — 서사 아크

## 시즌 1 (현재): 잿빛 봉인의 균열

**ID:** `ashen_seal_cracking` · **퀘스트:** `smoke_on_the_mountain`

### 3막 구조

| Phase | 이름 | progress | 핵심 질문 |
|-------|------|----------|-----------|
| 1 | 균열의 전조 | 0→35 | 「무엇이 일어나고 있는가?」 |
| 2 | 세력의 대립 | 35→65 | 「누구 편에 설 것인가?」 |
| 3 | 최후의 선택 | 65→100 | 「봉인을 어떻게 할 것인가?」 |

### 1단계 분기 (A–E)

→ `02_ISEKAI_FRAME.md` 각인 표 참고.  
클라이맥스 5종 + `phase1_climax_descent` 공통 하강.

### 2단계 삼분법 × 동맹 5

- **15 경로** (5×3) — `test_phase2_cross_routes`
- 동맹만 **5 세력 클라이맥스** — `phase2_climax_alliance_*`

### 3단계 결말

| ending (예) | 조건 요약 |
|-------------|-----------|
| `seal_maintained` | reinforce + 높은 자치회/십자 평판 |
| `new_order` | 균형·다세력 동맹 |
| `ancient_awakening` | break / 서약 루트 |
| `age_of_chaos` | chaos / 배신·중립 극단 |

`main_stories.json` → `endings[]`, `ending_scores` 누적.

## 서브 아크 (병렬)

| 아크 | 씨앗/퀘스트 | Phase 연동 |
|------|-------------|------------|
| 토렌 금형 | `torren_side_quest` | 1–2 |
| 회색 망토의 시험 | `grey_cloak` 대화·산 방문 | 1–3 |
| 핀의 북쪽 유물 | `merchant_finn` | 1 |
| 실버 스토커 | 퀘스트 stage 3 | 1–3 |
| 음모 | `conspiracy` shard | 2+ |
| 과거 캐릭터 | `player_past` | 메타·이세계 |

## 시즌 2 (설계): 「봉인 너머」

- 지도: 실버헤이븐 + 해안.
- 메인 ID: `beyond_ashen_seal` (가칭).
- 전제: 시즌 1 `resolved_ending` 에 따라 시작 `world_state` 분기.
- 새 Phase 1: **「균열 이후의 질서」** — 40 progress.

## 시즌 3 (설계): 「관리자의 거짓」

- 메타 아크: VR 운영사·신 레이어 공개.
- `conspiracy` + `grey_cloak` 수렴.
- 플레이어 선택: **게임 속 혁명** vs **로그아웃 저항**.

## 에피소드 (주간)

| 유형 | 길이 | 예 |
|------|------|-----|
| 마을 에피소드 | 3–5턴 | 축제·역병 |
| 던전 에피소드 | 8–12턴 | 일회성 탑 |
| PvP 에피소드 | — | 변경 외곽 분쟁 (로드맵) |

`events/seeds/expansion_*.json` 으로 샤드.

## 서사 톤 스펙트럼

```
일상(여관) — 미스터리(우물) — 정치(회관) — 호러(숲) — 장엄(관측탑) — 메타(관리자)
```

LLM 라우팅: `talk`/`explore` → Claude, `combat` → Codex, `world_arbiter` → 일관성 검사.

## 4차 벽 규칙

| 상황 | 허용 |
|------|------|
| 로비·튜토리얼 | 메타 언어 OK |
| 애쉬포인트 일상 | 3층만 (diegetic) |
| `grey_cloak` 심화 | 2층 힌트 (전송 의심) |
| GM 이벤트 | 1층 명시 |

## 결말 후 (Post-credit)

- `resolved_ending` 기록 → Link OS 「기억 서고」
- NG+ : 일부 평판 50% 이전, 플래그 `legacy_import`
- 하드코어 사망 슬롯: 「벽화」으로 NPC 대사에 이름 각인 (옵션)
