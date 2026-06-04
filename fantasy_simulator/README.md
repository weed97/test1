# Fantasy Simulator — Eldoria

Cursor 멀티 모델 운영을 위한 판타지 시뮬레이터.  
**`world_state.json`이 중앙 SSOT**이며, 매 턴마다 자동 동기화됩니다.

> 상세 운영 가이드: [docs/CURSOR_MULTI_MODEL.md](docs/CURSOR_MULTI_MODEL.md)

## 프로젝트 구조

```
fantasy_simulator/
├── world_state.json          # ★ 현재 세계 상태 (Cursor SSOT)
├── state/                    # 엔진 내부 샤드 (자동 관리)
├── rules/                    # 마법 체계, 전투 규칙
├── characters/               # 캐릭터 데이터
├── prompts/                  # 역할별 시스템 프롬프트
│   ├── narrator_claude.md    → Opus 4.8 High
│   ├── mechanics_codex.md    → Codex 5.3 High (JSON)
│   ├── world_arbiter.md      → Opus (일관성)
│   └── quick_event_gpt.md    → GPT-5.5 High
├── config/llm_routing.json
├── simulation_engine.py      # CLI + SimulationEngine (턴 루프)
└── utils/
    ├── turn_processor.py     # process_player_action (단일 진입점)
    ├── llm_router.py
    ├── llm_client.py
    └── state_manager.py
```

## 멀티 모델 분기 (`simulation_engine.py`)

| 필요 | 모델 | 프롬프트 |
|------|------|----------|
| 서사·캐릭터 | Claude Opus 4.8 High | `narrator_claude.md` |
| 규칙·메카닉스 | Codex 5.3 High | `mechanics_codex.md` (JSON only) |
| 빠른 아이디어 | GPT-5.5 High | `quick_event_gpt.md` |
| 오케스트레이션 | Cursor Composer + 엔진 | `simulation_engine.py` |

**기본 순서 (explore):** GPT → **Codex(규칙)** → **Opus(서사)**

## Cursor 사용법

1. **Composer** — `@world_state.json` + `@simulation_engine.py`로 턴 실행/파일 관리
2. **Opus Chat** — 서사 전담, `narrator_claude.md` 시스템 프롬프트
3. **Codex Chat** — 규칙 전담, `mechanics_codex.md`, JSON only
4. **GPT/Composer** — `quick_event_gpt.md`로 브레인스토밍
5. **주기적** — Opus + `world_arbiter.md`로 `world_state.json` 모순 검사

## CLI

```bash
cd fantasy_simulator

# 대화형 플레이 (Cursor 터미널)
python3 simulation_engine.py
python3 simulation_engine.py --mode hybrid -i

# 배치/스크립트 모드
python3 simulation_engine.py --batch --mode rule --turns 3 --seed 42
python3 simulation_engine.py --batch --mode llm --action explore

python3 simulation_engine.py --show-routing
python3 simulation_engine.py --show-providers   # API 키 / mock 상태 확인
python3 simulation_engine.py --show-prompts

# 수동 hub 동기화
python3 simulation_engine.py --export-legacy
```

**대화형 명령:** `explore`, `rest`, `combat <적>`, `status`, `help`, `quit`  
자유 입력도 가능 (예: `cast fireball`, `investigate ruins`)

## 모드

| 모드 | 동작 |
|------|------|
| `rule` | rule engine만 (오프라인) |
| `hybrid` | rule → GPT/Opus (탐색), rule → Codex → Opus (전투) |
| `llm` | 전체 LLM 파이프라인 |

## API 키 (선택)

```bash
export ANTHROPIC_API_KEY=...   # Opus
export OPENAI_API_KEY=...      # Codex, GPT-5.5
```

## 테스트

```bash
python3 -m unittest discover -s tests -v
```
