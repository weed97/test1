# 성좌 헌터 시뮬레이션 — 외부 시뮬레이터

순수 Python(표준 라이브러리만 사용)으로 작성된 **성좌 헌터** 턴제 시뮬레이터입니다.
8개의 **예측 불가 변수**가 모든 판정에 풀(full)로 반영되며, `[외부 업데이트] 질의`
형식의 Q&A로 JSON 변수를 **실시간 업데이트**할 수 있습니다.

## 주요 기능

- **8개 예측 불가 변수 풀 적용** — 난수·확률·이벤트·위기·연쇄가 모두 변수의 영향을 받음
- **외부 업데이트 Q&A** — `[외부 업데이트] 질의: <키>=<값>` → `[외부 업데이트] 응답: ...`
- **JSON 기반 실시간 변수 업데이트** — `config/variables.json`을 즉시 읽고/쓰기
- **자동 출력** — 매 턴 헌터 상태창 → 이벤트 발생 → 이벤트 로그 자동 렌더링
- **재현성** — `--seed` 고정 시 동일 결과 (디버깅/검증 용이)

## 디렉터리 구조

```
sungjwa_hunter_sim/
├── main.py                  # CLI 진입점
├── config/variables.json    # 8개 예측 불가 변수 + 기본 설정 (실시간 갱신 대상)
├── src/
│   ├── models.py            # Hunter / Constellation / GameState 데이터 모델
│   ├── variables.py         # VariableManager: JSON 로드/저장/실시간 갱신
│   ├── rng.py               # 예측 불가 변수가 적용된 난수 엔진(ChaosRNG)
│   ├── events.py            # 이벤트 생성기(변이/연쇄 포함)
│   ├── external_update.py   # [외부 업데이트] 질의 파서/핸들러
│   ├── ui.py                # 상태창/이벤트 로그 출력 포매터
│   └── simulator.py         # 턴 루프 엔진
└── tests/test_simulator.py  # 단위 테스트(unittest)
```

## 8개 예측 불가 변수

| 변수 | 기본값 | 역할 |
|------|--------|------|
| `randomness_intensity` | 1.8 | 무작위성 강도(난수 진폭) |
| `fate_deviation` | 0.5 | 운명 편차(결과 편향) |
| `constellation_mood` | 0.0 | 성좌 변덕(보상/개입 변동) |
| `probability_distortion` | 1.2 | 확률 왜곡(성공/실패 비선형) |
| `event_mutation_rate` | 0.3 | 이벤트 돌연변이율 |
| `crisis_escalation` | 1.1 | 위기 가속도(턴 누적) |
| `luck_factor` | 1.0 | 행운 계수(치명타/대성공) |
| `chaos_resonance` | 0.7 | 혼돈 공명(연쇄 이벤트) |

## 사용법

요구사항: Python 3.10+ (외부 의존성 없음)

```bash
cd sungjwa_hunter_sim

# 기본 자동 진행
python3 main.py

# 시드 고정 + 턴 수 지정 (재현 가능)
python3 main.py --seed 42 --turns 8

# 턴 사이마다 외부 업데이트 질의를 입력받는 대화형 모드
python3 main.py --interactive

# 단발성 외부 업데이트 질의만 처리하고 종료
python3 main.py --query "[외부 업데이트] 질의: randomness_intensity=2.6, luck_factor=1.5"

# 현재 8개 변수 상태 조회
python3 main.py --query "[외부 업데이트] 질의: 상태"

# 수정 가능한 키 목록 조회
python3 main.py --query "[외부 업데이트] 질의: 목록"

# 종료 시 최종 상태를 JSON으로 덤프
python3 main.py --seed 1 --json-out result.json
```

### 외부 업데이트 Q&A 형식

```
입력:  [외부 업데이트] 질의: randomness_intensity=2.4, luck_factor=1.7
출력:  [외부 업데이트] 응답: 적용됨 → randomness_intensity=2.4, luck_factor=1.7

입력:  [외부 업데이트] 질의: 상태
출력:  [외부 업데이트] 응답: 예측 불가 변수 8종 → randomness_intensity=1.8, ...
```

- 다중 할당은 쉼표(`,`) 또는 세미콜론(`;`)으로 구분합니다.
- 예측 불가 변수는 `min`/`max` 범위로 자동 보정됩니다.
- `hunter.hp`, `constellation.favor`, `simulation.max_turns` 같은 중첩 키도 수정 가능합니다.
- 대화형 모드에서는 `[외부 업데이트] 질의:` 접두사를 생략하고 `키=값`만 입력해도 됩니다.

대화형 모드 입력 규칙: 엔터(빈 입력)는 다음 턴 진행, `q`(또는 `종료`)는 시뮬레이션 종료.

### 주요 옵션

| 옵션 | 설명 |
|------|------|
| `--config PATH` | 변수 JSON 경로 (기본 `config/variables.json`) |
| `--seed N` | 난수 시드 고정 |
| `--turns N` | 최대 턴 수 |
| `--delay SEC` | 턴 사이 지연(초) |
| `--interactive` | 턴 사이 외부 업데이트 질의 입력 |
| `--query "..."` | 단발성 질의 처리 후 종료 |
| `--no-persist` | 외부 업데이트를 JSON 파일에 저장하지 않음 |
| `--json-out PATH` | 종료 시 최종 상태 JSON 저장 |

## 테스트

```bash
cd sungjwa_hunter_sim
python3 -m unittest discover -s tests -v
```
