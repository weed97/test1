# Fantasy Simulator — Eldoria

Cursor 멀티 모델 운영을 위한 판타지 시뮬레이터.  
**`world_state.json`은 최소 상태 hub**이며, 상세 서사는 `lore/`·`events/`에 분리됩니다.

> 운영: [docs/CURSOR_MULTI_MODEL.md](docs/CURSOR_MULTI_MODEL.md) · 콘텐츠: [docs/LORE_AND_EVENTS.md](docs/LORE_AND_EVENTS.md)

## 프로젝트 구조

```
fantasy_simulator/
├── world_state.json          # ★ 최소 상태 hub (Cursor @ 참조)
├── state/                    # canonical shards
├── lore/                     # NPC·지역 상세 (on-demand)
├── events/seeds.json         # 이벤트 씨앗 카탈로그
├── rules/
├── characters/               # stat + lore_ref
├── prompts/
├── config/llm_routing.json
├── simulation_engine.py
└── utils/
    ├── content_loader.py     # lore/events 필요 시 로드
    ├── turn_processor.py
    ├── llm_router.py
    ├── llm_client.py
    └── state_manager.py
```

## 멀티 모델 분기

상세 아키텍처: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

| 필요 | 모델 | 진입점 |
|------|------|--------|
| 서사 | Claude Opus 4.8 | `turn_processor` → `llm_client.call_claude` |
| 규칙 | Codex 5.3 | `turn_processor` → `llm_client.call_codex` |
| 오케스트레이션 | Composer + 엔진 | `simulation_engine.run_turn` |

**단일 진입점:** `utils/turn_processor.process_player_action()`

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
