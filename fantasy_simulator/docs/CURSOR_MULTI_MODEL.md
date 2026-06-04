# Cursor 멀티 모델 운영 가이드

이 문서는 **Cursor에서 fantasy_simulator를 실제로 운영**할 때 권장하는 멀티 모델 구조입니다.

## 역할별 모델 배치

| 역할 | 추천 모델 | 왜? | Cursor 사용법 |
|------|-----------|-----|---------------|
| **서사·몰입·캐릭터** | Claude Opus 4.8 High | 산문 품질, 캐릭터/세계관 일관성 | 별도 **Chat** 또는 Composer에서 전담 |
| **규칙 엄격 실행** (마법·전투·경제) | Codex 5.3 High | 구조적 사고 + 에이전틱 실행 | Mechanics 전용 Chat, JSON 강제 |
| **빠른 아이디어·대안** | GPT-5.5 High / Composer | 속도·유연성 | 브레인스토밍, 가벼운 이벤트 |
| **전체 오케스트레이션** | Cursor Composer + `simulation_engine.py` | 파일·상태·모델 호출 제어 | 메인 엔진 |

## 프로젝트 구조

```
fantasy_simulator/
├── world_state.json          # ★ Cursor가 읽는 중앙 상태 (매 턴 자동 동기화)
├── state/                    # 엔진 내부 샤드 (자동 관리)
├── rules/                    # 마법·전투 규칙 문서
├── characters/               # 캐릭터 JSON
├── prompts/                  # 역할별 시스템 프롬프트
│   ├── narrator_claude.md    → Opus
│   ├── mechanics_codex.md    → Codex (JSON only)
│   ├── world_arbiter.md      → Opus (일관성 검사)
│   └── quick_event_gpt.md    → GPT-5.5
├── config/llm_routing.json   # 파이프라인·모델 ID
├── simulation_engine.py      # 메인 오케스트레이터
└── utils/
    ├── llm_router.py         # decide_model_and_prompt()
    ├── llm_client.py         # call_claude / call_codex / call_gpt
    └── state_manager.py        # load/save + world_state.json 동기화
```

## 핵심: `world_state.json`을 중앙에

- **모든 모델·Cursor Chat은 `world_state.json`을 SSOT로 읽습니다.**
- `simulation_engine.py`가 턴 종료마다 `state/` → `world_state.json` 자동 동기화.
- Cursor Composer/Chat에서 작업 전: `@world_state.json` 첨부 또는 파일 열어두기.

## `simulation_engine.py` 분기 로직

플레이어 행동이 들어오면:

```
1. classify_action_needs(action, state)
   → narrative? mechanics? quick_ideas?

2. 순차 실행 (기본 explore 파이프라인):
   GPT-5.5  → quick_event_gpt.md     (가벼운 분기)
   Codex    → mechanics_codex.md     (규칙 JSON)
   Opus     → narrator_claude.md     (서사 plain text)

3. 5턴마다 Opus → world_arbiter.md  (일관성 검사)

4. apply_changes_to_state → world_state.json 동기화
```

**둘 다 필요할 때 순서:** 기본은 **Codex(규칙) → Claude(서사)**.  
규칙 결과를 서사에 반영하기 위해 mechanics를 narrator 앞에 둡니다.

## Cursor에서 모델 지정하는 현실적인 방법

### 1. Composer (오케스트레이션)
- 상단 모델: **Composer** 또는 원하는 모델
- `@simulation_engine.py`, `@world_state.json`, `@prompts/` 참조
- 턴 실행: `python3 simulation_engine.py --mode llm --action explore`

### 2. 서사 전용 Chat
- 모델: **Claude Opus 4.8 High** 고정
- 시스템: `prompts/narrator_claude.md` 내용 붙여넣기
- 입력: `world_state.json` + 플레이어 행동

### 3. Mechanics 전용 Chat
- 모델: **Codex 5.3 High** 고정
- 시스템: `prompts/mechanics_codex.md`
- **JSON only** 출력 강조 → `schemas/mechanics_codex.json` 참조

### 4. 브레인스토밍 Chat
- 모델: **GPT-5.5 High** 또는 Composer
- 시스템: `prompts/quick_event_gpt.md`

### 5. 일관성 검사 (주기적)
- 모델: **Claude Opus 4.8 High**
- 프롬프트: `prompts/world_arbiter.md`
- "현재 world_state를 검토하고 모순 찾아서 수정해"

## 추천 실제 운영 루틴

| 작업 | 도구 |
|------|------|
| 세계관·캐릭터·서사 | Opus 4.8 전용 Chat |
| 메카닉스·규칙 | Codex 5.3 전용 Chat |
| 파일 수정·턴 실행 | Cursor Composer |
| 상태 복잡해질 때 | Opus + `world_arbiter.md`로 모순 검사 |

## CLI 빠른 참조

```bash
python3 simulation_engine.py --show-routing    # 모델 분기 확인
python3 simulation_engine.py --show-prompts    # 프롬프트 미리보기
python3 simulation_engine.py --mode hybrid --turns 1 --action explore
python3 simulation_engine.py --export-legacy     # 수동 world_state.json 동기화
```

## API 키 (자동 호출 시)

```bash
export ANTHROPIC_API_KEY=...   # Opus (narrator, world_arbiter)
export OPENAI_API_KEY=...      # Codex + GPT-5.5
```

키 없으면 `mock` provider로 오프라인 테스트 가능.
