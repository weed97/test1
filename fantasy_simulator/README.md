# Fantasy Simulator

판타지 세계 **엘도리아**를 턴제로 시뮬레이션하는 오케스트레이터입니다.

## 디렉터리 구조

```
fantasy_simulator/
├── state/                    # 샤arded world state (권장 SSOT)
│   ├── meta.json
│   ├── world.json
│   ├── factions.json
│   ├── party.json
│   ├── inventory.json
│   ├── flags.json
│   ├── combat.json
│   └── event_log.json        # entries[] + next_turn (로그 분리)
├── world_state.json          # 레거시 단일 파일 (마이그레이션/내보내기용)
├── config/
│   └── llm_routing.json      # 역할→모델 라우팅, 파이프라인 정의
├── schemas/                  # structured output JSON Schema
├── rules/
├── characters/
├── prompts/
│   ├── base/                 # 공통 역할 프롬프트
│   └── models/
│       ├── codex_53/         # Codex 5.3 — 규칙 엄격 JSON
│       ├── opus_48_high/     # Opus 4.8 high — 서사·대사
│       └── gpt_55_high/      # ChatGPT 5.5 high — 빠른 이벤트 대안
├── simulation_engine.py      # 전체 턴 오케스트레이션 (SSOT)
└── utils/
    ├── state_store.py        # 샤드 load/save
    ├── prompt_router.py      # base + model overlay 조립
    ├── structured_output.py  # JSON 추출·검증·repair
    ├── rule_engine.py        # 규칙 기반 판정 (fallback/hybrid)
    └── llm/
        ├── router.py         # provider 라우팅
        ├── pipeline.py       # 턴당 역할 호출 순서
        └── providers/        # mock, anthropic, openai
```

## 실행 모드

| 모드 | 설명 |
|------|------|
| `rule` | 규칙 엔진만 (LLM 불필요, 오프라인) |
| `llm` | LLM 파이프라인 (world_arbiter→narrator 등) |
| `hybrid` | 규칙으로 주사위/수치 → LLM으로 서사·검증 |

```bash
cd fantasy_simulator

# 규칙만
python3 simulation_engine.py --mode rule --turns 3 --seed 42

# Hybrid: 규칙 + mock LLM (API 키 불필요)
python3 simulation_engine.py --mode hybrid --turns 2 --action explore

# LLM 라우팅 확인
python3 simulation_engine.py --show-routing

# state/ → world_state.json 내보내기
python3 simulation_engine.py --export-legacy
```

## LLM 모델 배치

| 구분 | 모델 | 역할 |
|------|------|------|
| **턴 오케스트레이션** | `simulation_engine.py` | 파이프라인 실행, state 저장 |
| **규칙 엄격 적용** | Codex 5.3 (`codex_53`) | `combat_referee`, `world_arbiter` |
| **서사·캐릭터 대사** | Opus 4.8 high (`opus_48_high`) | `narrator` |
| **빠른 이벤트 대안** | ChatGPT 5.5 high (`gpt_55_high`) | `event_alternatives` |

**LLM 파이프라인 (explore):** `event_alternatives` → `world_arbiter` → `narrator`

**Hybrid (explore):** 규칙 엔진(수치) → `event_alternatives` → `narrator`

- Codex 5.3: `schemas/*.json` + strict JSON + repair 재시도
- Opus 4.8 high: `effort=high`, 캐릭터 대사 포함 서사
- GPT 5.5 high: `reasoning_effort=high`, 2~4개 이벤트 분기 빠른 생성

## API 키 (선택)

| Provider | 환경 변수 | 역할 |
|----------|-----------|------|
| Anthropic | `ANTHROPIC_API_KEY` | Opus 4.8 high (narrator) |
| OpenAI | `OPENAI_API_KEY` | Codex 5.3, ChatGPT 5.5 high |

키가 없으면 `default_model: mock`으로 자동 fallback.

## world_state 샤딩

단일 JSON 대신 `state/` 샤드로 분리:

- **world.json** — 날짜, 날씨, 긴장도
- **event_log.json** — `entries[]` (히스토리 독립 성장)
- **combat.json** — 전투 중에만 non-null

기존 `world_state.json`이 있으면 최초 로드 시 자동 마이그레이션.

LLM 컨텍스트에는 `StateStore.llm_context_snapshot()`으로 최근 이벤트 10건만 전달.

## 테스트

```bash
python3 -m unittest discover -s tests -v
```
