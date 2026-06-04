"""Shared helpers for Phase 2 three-route clear simulations (after Phase 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tests.phase1_route_helpers import (
    PHASE1_ROUTE_SPECS,
    run_phase1_route_clear,
    setup_phase1_session,
)
from tests.phase2_alliance_specs import (  # noqa: E402
    ALLIANCE_BRANCH_SEEDS,
    ALLIANCE_ROUTE_BY_PHASE1,
)
from utils.game_session import GameSession
from utils.main_story_engine import MainStoryEngine
from utils.world_tension import set_tension

PHASE2_COMMON_PREFIX: list[str] = [
    "talk elder maren",
    "investigate forest",
    "explore forest",
]

PHASE2_ROUTE_SPECS: dict[str, dict[str, Any]] = {
    "path_alliance": {
        **ALLIANCE_ROUTE_BY_PHASE1["ally_village"],
        "choice_id": "path_alliance",
    },
    "path_neutral": {
        "choice_id": "path_neutral",
        "phase1_choice": "stay_neutral",
        "branch_seed": "story_choice_neutral",
        "branch_action": "talk lilian",
        "climax_seed": "phase2_climax_neutral",
        "climax_actions": ["explore forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
    "path_betrayal": {
        "choice_id": "path_betrayal",
        "phase1_choice": "exploit_chaos",
        "branch_seed": "story_choice_betrayal",
        "branch_action": "investigate forest",
        "climax_seed": "phase2_climax_betrayal",
        "climax_actions": ["investigate forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
}


def phase2_spec_for(phase1_choice: str, phase2_choice: str) -> dict[str, Any]:
    """Build Phase 2 run spec; alliance branch/climax follow Phase 1 choice."""
    if phase2_choice == "path_alliance":
        return {
            **ALLIANCE_ROUTE_BY_PHASE1[phase1_choice],
            "choice_id": "path_alliance",
            "phase1_choice": phase1_choice,
        }
    spec = dict(PHASE2_ROUTE_SPECS[phase2_choice])
    spec["phase1_choice"] = phase1_choice
    return spec


PHASE2_MILESTONE_FLAGS = (
    "phase2_opening_done",
    "phase2_escalation_done",
    "story_phase2_chosen",
    "phase2_climax_ready",
    "phase2_climax_done",
)

STORY_CHOICE_SEEDS = (
    *ALLIANCE_BRANCH_SEEDS,
    "story_choice_neutral",
    "story_choice_betrayal",
)


def setup_phase2_session(
    root: Path,
    *,
    phase1_choice: str = "ally_village",
    seed: int = 42,
) -> tuple[GameSession, MainStoryEngine]:
    """Complete Phase 1 for the given branch, then return session in Phase 2."""
    session, engine = setup_phase1_session(root, seed=seed)
    p1_spec = PHASE1_ROUTE_SPECS[phase1_choice]
    run_phase1_route_clear(session, p1_spec)
    ms = session.state["flags"]["main_story"]
    if int(ms.get("phase", 1)) < 2:
        story = engine.story_def(ms["id"])
        if story:
            engine._begin_phase2(session.state, story, ms)
    session.manager.save(session.state)
    session.manager.refresh_state(session.state)
    return session, engine


def _set_location(session: GameSession, action: str, *, default: str = "ashpoint") -> None:
    if "forest" in action or "investigate" in action:
        session.state["world"]["location"] = "북쪽 숲 — 연기가 보이는 외곽"
    else:
        session.state["world"]["location"] = default
    session.manager.save(session.state)


def _isolate_branch_seed(session: GameSession, branch_seed: str) -> None:
    session.state["flags"]["pending_events"] = [branch_seed]
    session.manager.save(session.state)


def _record_milestones(
    milestones: dict[str, int],
    turn: int,
    flags: dict[str, Any],
) -> None:
    for key in PHASE2_MILESTONE_FLAGS:
        if flags.get(key) and key not in milestones:
            milestones[key] = turn


def run_phase2_route_clear(
    session: GameSession,
    spec: dict[str, Any],
    *,
    on_step: Callable[[int, str, dict[str, Any], dict[str, Any]], None] | None = None,
    start_turn: int = 0,
) -> tuple[dict[str, int], dict[str, Any], dict[str, Any]]:
    """Run Phase 2 opening, escalation, branch, and climax."""
    milestones: dict[str, int] = {}
    turn = start_turn

    for action in PHASE2_COMMON_PREFIX:
        _set_location(session, action)
        turn += 1
        session.run_turn(action)
        flags = session.state["flags"]
        ms = flags["main_story"]
        if on_step:
            on_step(turn, action, flags, ms)
        _record_milestones(milestones, turn, flags)

    if not session.state["flags"].get("phase2_escalation_done"):
        set_tension(session.state, 50)
        session.manager.save(session.state)
        _set_location(session, "explore forest")
        for _ in range(4):
            if session.state["flags"].get("phase2_escalation_done"):
                break
            turn += 1
            session.run_turn("explore")
            flags = session.state["flags"]
            ms = flags["main_story"]
            if on_step:
                on_step(turn, "explore", flags, ms)
            _record_milestones(milestones, turn, flags)

    if spec.get("branch_time"):
        session.state["world"]["time_of_day"] = spec["branch_time"]
        session.manager.save(session.state)
    _isolate_branch_seed(session, spec["branch_seed"])
    if spec["branch_action"].startswith("talk"):
        _set_location(session, spec["branch_action"])
    else:
        _set_location(session, spec["branch_action"])

    turn += 1
    session.run_turn(spec["branch_action"])
    flags = session.state["flags"]
    ms = flags["main_story"]
    if on_step:
        on_step(turn, spec["branch_action"], flags, ms)
    _record_milestones(milestones, turn, flags)

    if not session.state["flags"].get("phase2_climax_ready"):
        set_tension(session.state, 50)
        session.manager.save(session.state)
        _set_location(session, "explore forest")
        for _ in range(3):
            if session.state["flags"].get("phase2_climax_ready"):
                break
            turn += 1
            session.run_turn("explore")
            flags = session.state["flags"]
            ms = flags["main_story"]
            if on_step:
                on_step(turn, "explore", flags, ms)
            _record_milestones(milestones, turn, flags)

    session.state["flags"]["pending_events"] = [spec["climax_seed"]]
    session.state["world"]["location"] = spec.get("climax_location", "ashpoint")
    session.manager.save(session.state)

    for action in spec["climax_actions"]:
        _set_location(session, action, default=spec.get("climax_location", "ashpoint"))
        turn += 1
        session.run_turn(action)
        flags = session.state["flags"]
        ms = flags["main_story"]
        if on_step:
            on_step(turn, action, flags, ms)
        _record_milestones(milestones, turn, flags)
        if flags.get("phase2_climax_done"):
            break

    flags = session.state["flags"]
    return milestones, flags, flags["main_story"]
