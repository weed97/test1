# CPoW Phase 2 — 가치화 정교화

**목표**: "이 오브젝트가 창의적인가?" 판단 로직을 엔진 안에서 다듬기.

## 구현 항목

| 항목 | 모듈 | 상태 |
|------|------|------|
| 복잡도·엔트로피 가중치 튜닝 | `config/cpow_scoring.json`, `cpow/cpow/__init__.py` | ✅ |
| JSON 스키마 검증 | `config/cpow_schema.json`, `schema/` | ✅ |
| 봇 시뮬레이션 | `bot_sim/` | ✅ |
| fantasy_simulator 어댑터 | `adapters/fantasy.py` | ✅ |
| sungjwa_hunter_sim 어댑터 | `adapters/sungjwa.py` | ✅ |

## 가중치 설정

`cpow_engine/config/cpow_scoring.json` — 코드 재배포 없이 튜닝:

- `weights.entropy_*` — 오브젝트 다양성·연결 밀도
- `weights.complexity_*` — 속성 수·연결·상호작용 밀도
- `bot_signals.*` — 균일 간격·payload 반복·행동 단조

```python
from cpow_engine.cpow import CPoWEngine
from cpow_engine.cpow.scoring_config import load_scoring_weights

cpow = CPoWEngine(weights=load_scoring_weights())
```

`CPoWScore`에 `complexity_score` 필드 추가 — 에너지에 `(1 + complexity)` 곱.

## 스키마 검증

```python
from cpow_engine.schema import validate_creative_object
from cpow_engine.models import CreativeObject

result = validate_creative_object(CreativeObject(...).to_dict())
assert result.ok, result.errors
```

검증 대상: `CreativeObject`, `ActionRecord`, `WorldDelta` (`cpow_schema.json`).

## 어댑터

### Eldoria (`fantasy_simulator`)

```python
from cpow_engine.adapters import FantasyTurnAdapter

adapter = FantasyTurnAdapter()
result = adapter.from_turn("hero_1", "explore", turn_payload)
# → ActionRecord + create_heat_object / create_material_object
```

### 성좌 헌터 (`sungjwa_hunter_sim`)

```python
from cpow_engine.adapters import SungjwaEventAdapter

adapter = SungjwaEventAdapter()
result = adapter.from_event("kim_dokja", event_dict)
```

## 봇 시뮬레이션

```bash
python3 -m cpow_engine.bot_sim
```

또는:

```python
from cpow_engine.bot_sim import run_bot_simulation

report = run_bot_simulation(steps=25)
print(report.to_dict())
```

| 시나리오 | 모델링 | 취약점 |
|----------|--------|--------|
| `macro_clicker` | 균일 1초 간격·동일 payload | bot_risk 높음 — 잘 탐지 |
| `fingerprint_spam` | 동일 fingerprint 반복 | creativity↓, creation_bonus 잔존 |
| `diversity_farmer` | 행동 타입 로테이션·고유 오브젝트 | bot_risk 우회 가능 — **주의** |

## 테스트

```bash
python3 -m unittest discover -s cpow_engine/tests -v
```

Phase 2 전용: `test_schema.py`, `test_adapters.py`, `test_bot_sim.py`

## 다음 (Phase 3)

엔진 점수 → 온체인 브릿지. Phase 2 완료 전 L1 착수 금지 — [CPOW_ROADMAP.md](CPOW_ROADMAP.md).
