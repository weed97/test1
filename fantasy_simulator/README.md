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
│       ├── claude/           # Claude 오버레이 (서사)
│       └── codex/            # Codex 오버레이 (엄격 JSON)
├── simulation_engine.py
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

## LLM 호출 구조

`config/llm_routing.json`에서 역할별 모델과 파이프라인을 정의합니다.

| 역할 | 기본 모델 | structured | 용도 |
|------|-----------|------------|------|
| narrator | claude | ✗ | 서사 생성 |
| combat_referee | codex | ✓ | 전투 JSON 판정 |
| world_arbiter | codex | ✓ | 거시 세계 갱신 JSON |

**파이프라인 예시 (explore):** `world_arbiter` → `narrator`

- `TurnPipeline`이 턴 액션마다 역할 순서대로 LLM 호출
- Codex 역할은 `schemas/*.json` + `prompts/models/codex/*_overlay.txt`로 JSON 강제
- 실패 시 `structured_output.py`가 repair 프롬프트로 재시도 (최대 3회)

## API 키 (선택)

| Provider | 환경 변수 | 역할 |
|----------|-----------|------|
| Anthropic | `ANTHROPIC_API_KEY` | Claude (narrator) |
| OpenAI | `OPENAI_API_KEY` | Codex (structured roles) |

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
