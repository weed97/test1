"""이벤트 생성기 - 8개 예측 불가 변수가 풀로 반영된 시나리오 이벤트.

각 이벤트는 헌터/성좌 상태에 효과(effects)를 적용하고 EventRecord 를 만든다.
event_mutation_rate 로 변형 이벤트가, chaos_resonance 로 연쇄 이벤트가 발생한다.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .models import EventRecord, GameState
from .rng import ChaosRNG

# 이벤트 정의: (kind, title, base_chance_of_success, handler)
# handler 는 (state, rng, multiplier) -> (description, effects, mutated_text|None)


def _apply(state: GameState, effects: Dict[str, int]) -> None:
    h = state.hunter
    c = state.constellation
    h.hp += effects.get("hp", 0)
    h.stamina += effects.get("stamina", 0)
    h.sanity += effects.get("sanity", 0)
    h.coins += effects.get("coins", 0)
    h.attack += effects.get("attack", 0)
    h.defense += effects.get("defense", 0)
    h.luck += effects.get("luck", 0)
    c.favor += effects.get("favor", 0)
    if effects.get("exp", 0):
        h.gain_exp(effects["exp"])
    h.clamp()
    c.clamp()


# ---------------------------------------------------------------------- #
# 개별 이벤트 핸들러
# ---------------------------------------------------------------------- #
def _ev_combat(state: GameState, rng: ChaosRNG, mult: float):
    enemy = rng.choice(["굶주린 화신", "탈주한 화신", "심연의 사도", "광인 도깨비", "배교한 성좌의 첨병"])
    win = rng.roll(0.62)
    crit = rng.critical()
    if win:
        dmg = rng.scaled_int(int(8 * mult))
        coins = rng.scaled_int(int(40 * mult))
        exp = rng.scaled_int(int(35 * mult))
        if crit:
            coins *= 2
            exp *= 2
            desc = f"'{enemy}'을(를) 상대로 회심의 일격! 압도적으로 제압했다."
        else:
            desc = f"'{enemy}'와(과) 격돌하여 승리했다."
        effects = {"hp": -dmg, "stamina": -rng.scaled_int(8), "coins": coins, "exp": exp, "favor": 5}
    else:
        dmg = rng.scaled_int(int(22 * mult))
        desc = f"'{enemy}'의 반격에 큰 피해를 입고 후퇴했다."
        effects = {"hp": -dmg, "stamina": -rng.scaled_int(12), "sanity": -rng.scaled_int(4), "favor": -2}
    return desc, effects, crit


def _ev_blessing(state: GameState, rng: ChaosRNG, mult: float):
    intervene = rng.roll(0.5)
    if intervene:
        coins = rng.scaled_int(80)
        favor = rng.scaled_int(12)
        desc = f"성좌 [{state.constellation.name}]이(가) 강림하여 가호를 내렸다."
        effects = {"coins": coins, "favor": favor, "sanity": rng.scaled_int(10), "hp": rng.scaled_int(15)}
    else:
        desc = f"성좌 [{state.constellation.name}]이(가) 변덕을 부려 시선을 거두었다."
        effects = {"favor": -rng.scaled_int(6), "sanity": -rng.scaled_int(3)}
    return desc, effects, False


def _ev_scenario(state: GameState, rng: ChaosRNG, mult: float):
    name = rng.choice(["멸망의 예고편", "왕의 길", "심판의 시간", "거인의 꿈", "최후의 방주"])
    clear = rng.roll(0.55)
    if clear:
        exp = rng.scaled_int(int(60 * mult))
        coins = rng.scaled_int(int(50 * mult))
        desc = f"메인 시나리오 '{name}'을(를) 클리어했다."
        effects = {"exp": exp, "coins": coins, "favor": rng.scaled_int(8), "stamina": -rng.scaled_int(15)}
    else:
        dmg = rng.scaled_int(int(18 * mult))
        desc = f"시나리오 '{name}' 도중 위기에 빠졌다."
        effects = {"hp": -dmg, "sanity": -rng.scaled_int(8), "stamina": -rng.scaled_int(18)}
    return desc, effects, False


def _ev_rest(state: GameState, rng: ChaosRNG, mult: float):
    desc = "안전지대에서 숨을 고르며 정비했다."
    effects = {"hp": rng.scaled_int(18), "stamina": rng.scaled_int(20), "sanity": rng.scaled_int(12)}
    return desc, effects, False


def _ev_anomaly(state: GameState, rng: ChaosRNG, mult: float):
    desc = "설명할 수 없는 균열이 나타나 현실이 일그러졌다."
    sign = 1 if rng.roll(0.5, lucky=True) else -1
    effects = {
        "sanity": -rng.scaled_int(int(10 * mult)),
        "coins": sign * rng.scaled_int(60),
        "luck": sign,
    }
    return desc, effects, False


EventHandler = Callable[[GameState, ChaosRNG, float], Tuple[str, Dict[str, int], bool]]

EVENT_TABLE: List[Tuple[str, str, float, EventHandler]] = [
    ("전투", "화신과의 조우", 0.30, _ev_combat),
    ("성좌개입", "성좌의 시선", 0.18, _ev_blessing),
    ("시나리오", "메인 시나리오", 0.22, _ev_scenario),
    ("정비", "안전지대", 0.15, _ev_rest),
    ("이상현상", "예측 불가 균열", 0.15, _ev_anomaly),
]

# 돌연변이 접두 묘사
_MUTATION_FLAVOR = [
    "[변이] 이벤트가 예상치 못한 형태로 뒤틀렸다 — ",
    "[변이] 확률장이 붕괴하며 양상이 달라졌다 — ",
    "[변이] 개연성이 비틀리며 변수가 폭주했다 — ",
]


class EventEngine:
    def __init__(self, rng: ChaosRNG):
        self.rng = rng

    def _pick(self) -> Tuple[str, str, float, EventHandler]:
        weights = [w for (_, _, w, _) in EVENT_TABLE]
        idx_items = list(range(len(EVENT_TABLE)))
        idx = self.rng.weighted_choice(idx_items, weights)
        return EVENT_TABLE[idx]

    def generate(self, state: GameState, chained: bool = False) -> List[EventRecord]:
        """한 턴의 이벤트(및 연쇄 이벤트)를 생성·적용하고 기록 목록을 반환한다."""
        records: List[EventRecord] = []
        kind, title, _w, handler = self._pick()
        mult = self.rng.crisis_multiplier(state.turn)

        desc, effects, crit = handler(state, self.rng, mult)
        mutated = self.rng.mutates()
        if mutated:
            flavor = self.rng.choice(_MUTATION_FLAVOR)
            desc = flavor + desc
            # 변형: 효과를 무작위로 증폭
            effects = {k: self.rng.scaled_int(int(v * 1.6)) if v else v for k, v in effects.items()}
            title = f"{title}(변이)"

        _apply(state, effects)
        records.append(
            EventRecord(
                turn=state.turn,
                kind=kind,
                title=title,
                description=desc,
                effects=effects,
                mutated=mutated,
                chained=chained,
            )
        )

        # 연쇄 이벤트 (chaos_resonance). 무한 연쇄 방지 위해 chained 호출은 1단계만.
        if not chained and state.hunter.alive and self.rng.chains():
            records.extend(self.generate(state, chained=True))
        return records
