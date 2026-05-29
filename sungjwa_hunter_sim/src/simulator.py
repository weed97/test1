"""턴 루프 엔진 - 상태창 → 이벤트 → 로그를 자동 출력하며 진행한다.

[외부 업데이트] 질의를 통한 JSON 변수 실시간 업데이트를 턴 사이에 받을 수 있다
(interactive=True). 비대화형 모드에서는 시작 시점 변수로 끝까지 진행한다.

게이트 몬스터 유닛과 성좌 헌터 로스터를 로드해 전투/시작 상태에 반영한다.
"""

from __future__ import annotations

import sys
import time
from typing import Callable, List, Optional

from .events import EventEngine
from .external_update import ExternalUpdateHandler
from .models import GameState
from .rng import ChaosRNG
from . import ui
from . import units
from .variables import VariableManager

InputFn = Callable[[str], str]
OutputFn = Callable[[str], None]


class Simulator:
    def __init__(
        self,
        variables: VariableManager,
        *,
        seed: Optional[int] = None,
        hunter_id: Optional[str] = None,
        output: Optional[OutputFn] = None,
    ):
        self.vars = variables
        sim_cfg = variables.simulation_config()
        if seed is None:
            seed = sim_cfg.get("seed")
        self.rng = ChaosRNG(variables, seed=seed)
        # 게이트 몬스터 유닛 로드 → 전투 이벤트에서 사용
        self.rng.monsters = units.load_monsters(variables)
        self.events = EventEngine(self.rng)
        self.external = ExternalUpdateHandler(variables, persist=True)
        self.out: OutputFn = output or (lambda s: print(s))
        self.hunter_id = hunter_id
        self.state = self._build_state()

    def _build_state(self) -> GameState:
        hunter, const, used_id = units.select_hunter(self.vars, self.hunter_id)
        self.hunter_id = used_id
        return GameState(hunter=hunter, constellation=const)

    # ------------------------------------------------------------------ #
    def _emit(self, text: str) -> None:
        self.out(text)

    def step(self) -> List:
        """한 턴을 진행하고 발생한 이벤트 기록을 반환한다."""
        self.state.turn += 1
        self._emit("")
        self._emit(ui.render_status(self.state))
        self._emit(ui.render_uvars(self.rng.snapshot()))
        events = self.events.generate(self.state)
        for e in events:
            self.state.record(e)
        self._emit(ui.render_turn_log(events))
        return events

    def _check_end(self, max_turns: int) -> bool:
        h = self.state.hunter
        if not h.alive:
            self.state.finished = True
            self.state.outcome = "헌터가 쓰러졌다. 시나리오 탈락." if h.hp <= 0 else "정신이 붕괴했다. 광기에 잠식됨."
            return True
        if self.state.turn >= max_turns:
            self.state.finished = True
            self.state.outcome = "모든 턴을 견뎌내고 생존했다."
            return True
        return False

    # ------------------------------------------------------------------ #
    def run(
        self,
        max_turns: Optional[int] = None,
        *,
        delay: Optional[float] = None,
        interactive: bool = False,
        input_fn: Optional[InputFn] = None,
    ) -> GameState:
        sim_cfg = self.vars.simulation_config()
        if max_turns is None:
            max_turns = int(sim_cfg.get("max_turns", 10))
        if delay is None:
            delay = float(sim_cfg.get("delay_seconds", 0.0))

        self._emit(_banner(self.state, max_turns, self.hunter_id, len(self.rng.monsters)))

        while not self.state.finished:
            if interactive:
                self._interactive_prompt(input_fn)
            self.step()
            if delay > 0:
                time.sleep(delay)
            if self._check_end(max_turns):
                break

        self._emit("")
        self._emit(ui.render_summary(self.state))
        return self.state

    def _interactive_prompt(self, input_fn: Optional[InputFn]) -> None:
        reader = input_fn or _default_input
        try:
            line = reader(
                "\n[외부 업데이트] 질의를 입력하세요 (엔터=다음 턴, 'q'=종료)\n> "
            )
        except (EOFError, KeyboardInterrupt):
            self.state.finished = True
            self.state.outcome = "외부 종료 신호로 시뮬레이션을 중단했다."
            raise SystemExit(0)
        line = (line or "").strip()
        if line.lower() in ("q", "quit", "exit", "종료"):
            self.state.finished = True
            self.state.outcome = "사용자 요청으로 시뮬레이션을 종료했다."
            raise _StopSimulation()
        if not line:
            return
        if self.external.is_query(line) or "=" in line:
            if not self.external.is_query(line):
                line = f"[외부 업데이트] 질의: {line}"
            self._emit(self.external.handle(line))
        else:
            self._emit("[외부 업데이트] 응답: '[외부 업데이트] 질의: 키=값' 형식으로 입력하세요.")


class _StopSimulation(Exception):
    pass


def _banner(state: GameState, max_turns: int, hunter_id: Optional[str], monster_count: int) -> str:
    tag = f" (로스터: {hunter_id})" if hunter_id else ""
    return (
        "\n" + "═" * 60 + "\n"
        "  성좌 헌터 시뮬레이션 — 외부 시뮬레이터\n"
        f"  헌터: {state.hunter.name}{tag} / 성좌: [{state.constellation.name}]\n"
        f"  최대 {max_turns}턴 · 8개 예측 불가 변수 풀 적용 · 게이트 몬스터 {monster_count}종\n"
        + "═" * 60
    )


def _default_input(prompt: str) -> str:
    if not sys.stdin or not sys.stdin.isatty():
        line = sys.stdin.readline()
        return line.rstrip("\n") if line else ""
    return input(prompt)
