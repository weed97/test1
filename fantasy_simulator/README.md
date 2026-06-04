# Fantasy Simulator

판타지 세계 **엘도리아**를 턴제로 시뮬레이션하는 오케스트레이터입니다.  
`world_state.json`을 단일 진실 공급원(Single Source of Truth)으로 두고, 규칙·캐릭터·프롬프트를 분리해 관리합니다.

## 디렉터리 구조

```
fantasy_simulator/
├── world_state.json          # 현재 세계 상태 (중요)
├── rules/                    # 마법 체계, 전투 규칙 등 상세 문서
├── characters/               # 캐릭터 데이터
├── prompts/                  # 역할별 시스템 프롬프트
├── simulation_engine.py      # 메인 루프 (오케스트레이터)
└── utils/
```

## 요구사항

- Python 3.10+
- 외부 의존성 없음 (표준 라이브러리만 사용)

## 사용법

```bash
cd fantasy_simulator

# 현재 세계/파티 상태 확인
python3 simulation_engine.py --status

# 3턴 탐색 (시드 고정)
python3 simulation_engine.py --turns 3 --seed 42 --action explore

# 휴식 (HP/마나 회복)
python3 simulation_engine.py --action rest

# 보스 전투
python3 simulation_engine.py --combat malachar_voidweaver --turns 5 --seed 7

# LLM 연동용 역할 프롬프트 미리보기
python3 simulation_engine.py --show-prompts
```

## 핵심 개념

| 구성요소 | 역할 |
|----------|------|
| `world_state.json` | 날짜·날씨·긴장도·파티·전투·이벤트 로그 |
| `rules/` | 마법/전투 판정 규칙 (문서 + 엔진 참조) |
| `characters/` | PC/NPC 스탯·스펠·장비 JSON |
| `prompts/` | 내레이터·전투 심판·세계 중재자 시스템 프롬프트 |
| `simulation_engine.py` | 턴 진행, 전투/탐색/휴식, 상태 저장 |

## 프롬프트 역할

- **narrator** — 장면 서사 생성
- **combat_referee** — 전투 판정 JSON 출력
- **world_arbiter** — 거시적 세계 변화(파벌·긴장도·날씨)

엔진은 규칙 기반으로 단독 실행 가능하며, `prompts/`는 LLM API 연동 시 그대로 system prompt로 사용할 수 있습니다.

## world_state.json 갱신

매 턴 종료 시 `world_state.json`이 자동 저장됩니다.  
전투 종료 후 캐릭터 HP/마나는 `characters/*.json`에도 반영됩니다.
