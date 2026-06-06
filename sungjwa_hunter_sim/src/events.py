"""이벤트 생성기 - 8개 예측 불가 변수가 풀로 반영된 시나리오 이벤트.

각 이벤트는 헌터/성좌 상태에 효과(effects)를 적용하고 EventRecord 를 만든다.
event_mutation_rate 로 변형 이벤트가, chaos_resonance 로 연쇄 이벤트가 발생한다.
전투(게이트) 이벤트는 게이트 몬스터 유닛을 소환하고, 그 몬스터의 예외 변수를
전투 동안에만 8개 변수 위에 덧씌워 판정한다.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Tuple

from .models import EventRecord, GameState
from .rng import ChaosRNG


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
    monster = rng.pick_monster(state.turn)

    if monster is None:
        # 게이트 몬스터 미정의 시 폴백 (구버전 호환)
        enemy = rng.choice(["굶주린 화신", "탈주한 화신", "심연의 사도", "광인 도깨비"])
        win = rng.roll(0.62)
        crit = rng.critical()
        if win:
            dmg = rng.scaled_int(int(8 * mult))
            effects = {"hp": -dmg, "stamina": -rng.scaled_int(8),
                       "coins": rng.scaled_int(40), "exp": rng.scaled_int(35), "favor": 5}
            desc = f"'{enemy}'와(과) 격돌하여 승리했다."
        else:
            dmg = rng.scaled_int(int(22 * mult))
            effects = {"hp": -dmg, "stamina": -rng.scaled_int(12),
                       "sanity": -rng.scaled_int(4), "favor": -2}
            desc = f"'{enemy}'의 반격에 큰 피해를 입고 후퇴했다."
        return desc, effects, crit

    # ---- 게이트 몬스터 듀얼: 예외 변수를 전투 구간에만 적용 ----
    h = state.hunter
    with rng.exception_scope(monster.exception_variables):
        hunter_power = h.attack + h.defense * 0.4 + h.luck * 0.5
        monster_power = monster.power()
        base_chance = hunter_power / max(1.0, hunter_power + monster_power)
        win = rng.roll(base_chance)
        crit = rng.critical()

        ev_note = ", ".join(f"{k}={v:g}" for k, v in monster.exception_variables.items())
        gate = f"[{monster.grade}급 게이트] '{monster.name}'(특성: {monster.trait}) 출현"
        if ev_note:
            gate += f" ◇예외변수 {ev_note}◇"

        if win:
            taken = rng.scaled_int(int((monster.attack * 0.6) * mult))
            coins = rng.scaled_int(monster.reward_coins)
            exp = rng.scaled_int(monster.reward_exp)
            if crit:
                coins *= 2
                exp = int(exp * 1.8)
                desc = f"{gate} — 회심의 일격으로 단숨에 토벌!"
            else:
                desc = f"{gate} — 격전 끝에 토벌 성공."
            effects = {
                "hp": -taken,
                "stamina": -rng.scaled_int(int(8 + monster.attack * 0.2)),
                "coins": coins,
                "exp": exp,
                "favor": rng.scaled_int(max(3, int(monster.reward_exp * 0.06))),
            }
            state.defeated_monsters.append(monster.id)
        else:
            taken = rng.scaled_int(int(monster.attack * mult))
            desc = f"{gate} — 토벌 실패, 큰 피해를 입고 후퇴했다."
            effects = {
                "hp": -taken,
                "stamina": -rng.scaled_int(int(10 + monster.attack * 0.3)),
                "sanity": -rng.scaled_int(int(4 + monster.power() * 0.05)),
                "favor": -rng.scaled_int(3),
            }
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
    ("전투", "게이트 토벌", 0.32, _ev_combat),
    ("성좌개입", "성좌의 시선", 0.18, _ev_blessing),
    ("시나리오", "메인 시나리오", 0.20, _ev_scenario),
    ("정비", "안전지대", 0.15, _ev_rest),
    ("이상현상", "예측 불가 균열", 0.15, _ev_anomaly),
]

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

        if not chained and state.hunter.alive and self.rng.chains():
            records.extend(self.generate(state, chained=True))
        return records
