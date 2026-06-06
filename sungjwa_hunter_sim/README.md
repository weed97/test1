# 성좌 헌터 시뮬레이션 — 외부 시뮬레이터

순수 Python(표준 라이브러리만 사용)으로 작성된 **성좌 헌터** 턴제 시뮬레이터입니다.
8개의 **예측 불가 변수**가 모든 판정에 풀(full)로 반영되며, `[외부 업데이트] 질의`
형식의 Q&A로 JSON 변수를 **실시간 업데이트**할 수 있습니다.

## 주요 기능

- **8개 예측 불가 변수 풀 적용** — 난수·확률·이벤트·위기·연쇄가 모두 변수의 영향을 받음
- **게이트 몬스터 예외 변수 유닛** — 몬스터마다 전투 동안에만 적용되는 `exception_variables`로 국소적 확률장 왜곡
- **성좌 헌터 로스터** — 여러 명의 헌터+성좌 프리셋 중 선택해 플레이
- **외부 업데이트 Q&A** — `[외부 업데이트] 질의: <키>=<값>` → `[외부 업데이트] 응답: ...`
- **JSON 기반 실시간 변수 업데이트** — `config/variables.json`을 즉시 읽고/쓰기
- **자동 출력** — 매 턴 헌터 상태창 → 이벤트 발생 → 이벤트 로그 자동 렌더링
- **재현성** — `--seed` 고정 시 동일 결과

## 디렉터리 구조

```
sungjwa_hunter_sim/
├── main.py                  # CLI 진입점
├── config/variables.json    # 8개 변수 + 헌터 로스터 + 게이트 몬스터 (실시간 갱신)
├── src/
│   ├── models.py            # Hunter / Constellation / MonsterUnit / HunterPreset / GameState
│   ├── variables.py         # VariableManager: JSON 로드/저장/실시간 갱신
│   ├── rng.py               # ChaosRNG: 예측 불가 변수 엔진 + 예외 변수 스코프 + 몬스터 선택
│   ├── units.py             # 게이트 몬스터 / 헌터 로스터 로더
│   ├── events.py            # 이벤트 생성기(게이트 몬스터 듀얼/변이/연쇄 포함)
│   ├── external_update.py   # [외부 업데이트] 질의 파서/핸들러
│   ├── ui.py                # 상태창/이벤트 로그 출력 포매터
│   └── simulator.py         # 턴 루프 엔진
└── tests/                   # unittest (변수/외부업데이트/시뮬/몬스터/로스터/호환성)
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

## 게이트 몬스터 예외 변수 유닛

`config/variables.json`의 `gate_monsters` 배열에 정의합니다. 각 몬스터는 자체 스탯
(`hp`/`attack`/`defense`/`reward_*`)과 **예외 변수(`exception_variables`)**를 가집니다.
예외 변수는 **해당 몬스터와의 전투 동안에만** 8개 예측 불가 변수 위에 덧씌워졌다가
전투가 끝나면 원래 값으로 복원됩니다(`ChaosRNG.exception_scope`).

```json
{
  "id": "shadow_assassin", "name": "그림자 암살자", "grade": "C",
  "hp": 70, "attack": 27, "defense": 7, "reward_coins": 120, "reward_exp": 85,
  "trait": "기습",
  "exception_variables": {"fate_deviation": -0.9, "randomness_intensity": 2.7}
}
```

- 등급(`grade`)은 `F < E < D < C < B < A < S` 순이며, **턴이 진행될수록 고등급 몬스터 출현 확률**이 올라갑니다.
- 목록 확인: `python3 main.py --list-monsters`

## 성좌 헌터 로스터

`config/variables.json`의 `hunter_roster` 배열에 헌터+성좌 프리셋을 정의합니다.

```json
{
  "id": "yoo_jonghyuk",
  "hunter": {"name": "유중혁", "title": "회귀자", "level": 3, "hp": 160, "attack": 24, ...},
  "constellation": {"name": "구원의 마왕", "favor": 10, "patronage": "냉혹한 심판자"}
}
```

- 선택: `python3 main.py --hunter yoo_jonghyuk`
- 목록 확인: `python3 main.py --list-hunters`
- 선택하지 않으면 기존 단일 `hunter`/`constellation` 설정을 그대로 사용합니다(**완전 호환**).

## 사용법

요구사항: Python 3.10+ (외부 의존성 없음)

```bash
cd sungjwa_hunter_sim

# 기본 자동 진행
python3 main.py

# 로스터에서 헌터 선택 + 시드 고정
python3 main.py --hunter kim_dokja --seed 42 --turns 8

# 로스터 / 게이트 몬스터 목록 확인
python3 main.py --list-hunters
python3 main.py --list-monsters

# 대화형 모드 (턴 사이 외부 업데이트 질의)
python3 main.py --interactive

# 단발성 외부 업데이트 질의
python3 main.py --query "[외부 업데이트] 질의: randomness_intensity=2.6, luck_factor=1.5"
python3 main.py --query "[외부 업데이트] 질의: 상태"

# 종료 시 최종 상태 JSON 덤프 (defeated_monsters 포함)
python3 main.py --seed 1 --json-out result.json
```

### 외부 업데이트 Q&A 형식

```
입력:  [외부 업데이트] 질의: randomness_intensity=2.4, luck_factor=1.7
출력:  [외부 업데이트] 응답: 적용됨 → randomness_intensity=2.4, luck_factor=1.7
```

- 다중 할당은 쉼표(`,`) 또는 세미콜론(`;`)으로 구분합니다.
- 예측 불가 변수는 `min`/`max` 범위로 자동 보정됩니다.
- `hunter.hp`, `constellation.favor`, `simulation.selected_hunter` 같은 중첩 키도 수정 가능합니다.

### 주요 옵션

| 옵션 | 설명 |
|------|------|
| `--config PATH` | 변수 JSON 경로 |
| `--seed N` | 난수 시드 고정 |
| `--turns N` | 최대 턴 수 |
| `--delay SEC` | 턴 사이 지연(초) |
| `--hunter ID` | 로스터에서 성좌 헌터 선택 |
| `--interactive` | 턴 사이 외부 업데이트 질의 입력 |
| `--query "..."` | 단발성 질의 처리 후 종료 |
| `--list-hunters` | 헌터 로스터 출력 후 종료 |
| `--list-monsters` | 게이트 몬스터 유닛 출력 후 종료 |
| `--no-persist` | 외부 업데이트를 JSON 파일에 저장하지 않음 |
| `--json-out PATH` | 종료 시 최종 상태 JSON 저장 |

## 테스트

```bash
cd sungjwa_hunter_sim
python3 -m unittest discover -s tests -v
```
