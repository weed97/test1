# Cursor 멀티 모델 운영 가이드

Cursor에서 **fantasy_simulator**를 운영할 때의 실제 구조입니다.  
코드 기준 문서: [ARCHITECTURE.md](ARCHITECTURE.md)

## 역할별 모델 배치

| 역할 | 추천 모델 | 프롬프트 | 코드 경로 |
|------|-----------|----------|-----------|
| 서사·캐릭터 | Claude Opus 4.8 High | `prompts/narrator_claude.md` | `llm_client.call_claude` |
| 규칙·메카닉스 | Codex 5.3 High | `prompts/mechanics_codex.md` | `llm_client.call_codex` (JSON) |
| 빠른 아이디어 | GPT-5.5 High | `prompts/quick_event_gpt.md` | `llm_client.call_gpt` |
| 일관성 검사 | Claude Opus 4.8 | `prompts/world_arbiter.md` | 5턴마다 자동 |
| 오케스트레이션 | Composer + 엔진 | — | `simulation_engine.py` |

## 프로젝트 구조

```
fantasy_simulator/
├── world_state.json          # Cursor hub mirror (state/ 자동 export)
├── state/                    # ★ canonical storage (엔진 SSOT)
├── rules/
├── characters/
├── prompts/
├── config/llm_routing.json
├── simulation_engine.py      # CLI + SimulationEngine.run_turn
└── utils/
    ├── turn_processor.py     # process_player_action() — 단일 진입점
    ├── llm_router.py         # decide_model_and_prompt() 키워드 라우팅
    ├── llm_client.py         # live API / mock / retry / degrade
    └── state_manager.py      # save + hub sync
```

## 턴 처리 흐름 (실제 코드)

```
1. decide_model_and_prompt(action)   # 키워드 → claude | codex | rule
2. process_player_action()
     hybrid? → rule engine 먼저
     use_llm? → llm_client (실패 시 rule fallback)
     5턴마다 world_arbiter
3. StateManager.save() → state/ + world_state.json
```

**키워드 라우팅 (기본):**
- `attack`, `cast`, `combat` → Codex (JSON)
- `explore`, `talk`, `look` → Claude (text)
- `rest`, 기타 → rule engine

## LLM mock vs live 확인

```bash
python3 simulation_engine.py --show-providers
```

- API 키 없음 → **mock** (오프라인 테스트)
- API 키 있음 → **live** 호출
- live 실패 → 네트워크 재시도 → mock degrade → rule engine fallback

터미널 출력 태그: `[mock]`, `[degraded]`, `[fallback]`

## Cursor 운영 루틴

| 작업 | 도구 |
|------|------|
| 대화형 플레이 | 터미널: `python3 simulation_engine.py` |
| 파일·턴 관리 | Composer + `@world_state.json` |
| 서사 | Opus Chat + `narrator_claude.md` |
| 규칙 | Codex Chat + `mechanics_codex.md` (JSON only) |
| 상태 모순 검사 | Opus + `world_arbiter.md` |

## CLI

```bash
cd fantasy_simulator

python3 simulation_engine.py                    # 대화형 REPL
python3 simulation_engine.py --show-providers   # mock/live 확인
python3 simulation_engine.py --show-routing
python3 simulation_engine.py --batch --mode llm --action explore
python3 simulation_engine.py --export-legacy    # 수동 hub export
```

## API 키

```bash
export ANTHROPIC_API_KEY=...   # Opus
export OPENAI_API_KEY=...      # Codex, GPT-5.5
```

## 에러 처리 요약

| 단계 | 동작 |
|------|------|
| Structured JSON invalid | schema repair retry (최대 3회) |
| Network / API error | network retry → mock degrade |
| LLM 완전 실패 | rule engine fallback, 턴 계속 진행 |
| world_arbiter 실패 | 스킵 (턴 중단 없음) |

설정: `config/llm_routing.json` → `network`, `structured_output`
