"""Shared helpers for Phase 3 ending-route clear simulations (after Phase 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tests.phase2_route_helpers import (
    phase2_spec_for,
    run_phase2_route_clear,
    setup_phase2_session,
)
from tests.phase3_alliance_specs import ALLIANCE_ROUTE_BY_PHASE1_PHASE3, FINAL_CHOICE_BRANCH
from utils.game_session import GameSession
from utils.main_story_engine import MainStoryEngine
from utils.world_tension import get_tension, set_tension

PHASE3_COMMON_PREFIX: list[str] = [
    "investigate forest",
    "talk elder maren",
    "explore forest",
]

PHASE3_ROUTE_SPECS: dict[str, dict[str, Any]] = {
    "path_alliance": {
        **ALLIANCE_ROUTE_BY_PHASE1_PHASE3["ally_village"],
    },
    "path_neutral": {
        "phase2_choice": "path_neutral",
        "phase1_choice": "stay_neutral",
        "final_choice_id": "final_chaos",
        "branch_seed": "story_choice_final_chaos",
        "branch_action": "explore",
        "climax_seed": "phase3_climax_neutral",
        "climax_actions": ["investigate forest"],
        "climax_location": "관측탑",
    },
    "path_betrayal": {
        "phase2_choice": "path_betrayal",
        "phase1_choice": "exploit_chaos",
        "final_choice_id": "final_break",
        "branch_seed": "story_choice_final_break",
        "branch_action": "investigate forest",
        "branch_tension_min": 55,
        "climax_seed": "phase3_climax_betrayal",
        "climax_actions": ["investigate forest"],
        "climax_location": "관측탑",
    },
}

PHASE3_MILESTONE_FLAGS = (
    "phase3_opening_done",
    "phase3_crisis_done",
    "story_phase3_chosen",
    "phase3_climax_ready",
    "phase3_climax_done",
)

FINAL_CHOICE_SEEDS = (
    "story_choice_final_reinforce",
    "story_choice_final_break",
    "story_choice_final_chaos",
)


def phase3_spec_for(phase1_choice: str, phase2_choice: str) -> dict[str, Any]:
    """Build Phase 3 run spec from Phase 1 + Phase 2 path choices."""
    if phase2_choice == "path_alliance":
        return dict(ALLIANCE_ROUTE_BY_PHASE1_PHASE3[phase1_choice])
    spec = dict(PHASE3_ROUTE_SPECS[phase2_choice])
    spec["phase1_choice"] = phase1_choice
    return spec


def setup_phase3_session(
    root: Path,
    *,
    phase2_choice: str = "path_alliance",
    phase1_choice: str | None = None,
    seed: int = 42,
) -> tuple[GameSession, MainStoryEngine]:
    """Complete Phases 1–2, then return session in Phase 3."""
    p1 = phase1_choice or PHASE3_ROUTE_SPECS[phase2_choice]["phase1_choice"]
    session, engine = setup_phase2_session(root, phase1_choice=p1, seed=seed)
    run_phase2_route_clear(session, phase2_spec_for(p1, phase2_choice))
    ms = session.state["flags"]["main_story"]
    if int(ms.get("phase", 1)) < 3:
        story = engine.story_def(ms["id"])
        if story:
            engine._begin_phase3(session.state, story, ms)
    session.manager.save(session.state)
    session.manager.refresh_state(session.state)
    return session, engine


def _set_location(session: GameSession, action: str, *, default: str = "ashpoint") -> None:
    if "forest" in action or "investigate" in action:
        if "tower" in default.lower() or "관측" in default:
            session.state["world"]["location"] = default
        else:
            session.state["world"]["location"] = "북쪽 숲 — 연기가 보이는 외곽"
    else:
        session.state["world"]["location"] = default
    session.manager.save(session.state)


def _isolate_final_choice(session: GameSession, branch_seed: str) -> None:
    session.state["flags"]["pending_events"] = [branch_seed]
    session.manager.save(session.state)


def _record_milestones(
    milestones: dict[str, int],
    turn: int,
    flags: dict[str, Any],
) -> None:
    for key in PHASE3_MILESTONE_FLAGS:
        if flags.get(key) and key not in milestones:
            milestones[key] = turn


def _ensure_phase3_climax_ready(session: GameSession, flags: dict[str, Any], ms: dict[str, Any]) -> None:
    if flags.get("phase3_climax_ready"):
        return
    set_tension(session.state, 58)
    session.state["world"]["time_of_day"] = "night"
    session.manager.save(session.state)
    tower = "관측탑"
    _set_location(session, "explore forest", default=tower)
    for _ in range(6):
        if session.state["flags"].get("phase3_climax_ready"):
            return
        session.run_turn("explore")
    flags = session.state["flags"]
    ms = flags["main_story"]
    if not flags.get("story_seal_near_break"):
        flags["story_seal_near_break"] = True
        engine = MainStoryEngine(session.manager.base_dir)
        story = engine.story_def(ms["id"])
        if story:
            engine._advance_phase3_from_flag(session.state, story, ms, "story_seal_near_break")
    engine = MainStoryEngine(session.manager.base_dir)
    story = engine.story_def(ms["id"])
    if story:
        engine._update_phase3_climax_readiness(session.state, story, ms)
    session.manager.save(session.state)


def run_phase3_route_clear(
    session: GameSession,
    spec: dict[str, Any],
    *,
    on_step: Callable[[int, str, dict[str, Any], dict[str, Any]], None] | None = None,
    start_turn: int = 0,
) -> tuple[dict[str, int], dict[str, Any], dict[str, Any]]:
    """Run Phase 3 opening, crisis, final choice, climax, and ending."""
    milestones: dict[str, int] = {}
    turn = start_turn
    tower = spec.get("climax_location", "관측탑")

    for action in PHASE3_COMMON_PREFIX:
        loc = tower if action == "investigate forest" else "ashpoint"
        _set_location(session, action, default=loc)
        turn += 1
        session.run_turn(action)
        flags = session.state["flags"]
        ms = flags["main_story"]
        if on_step:
            on_step(turn, action, flags, ms)
        _record_milestones(milestones, turn, flags)

    if not session.state["flags"].get("phase3_crisis_done"):
        set_tension(session.state, 58)
        session.state["world"]["time_of_day"] = "night"
        session.manager.save(session.state)
        _set_location(session, "explore", default="ashpoint")
        for _ in range(5):
            if session.state["flags"].get("phase3_crisis_done"):
                break
            turn += 1
            session.run_turn("explore")
            flags = session.state["flags"]
            ms = flags["main_story"]
            if on_step:
                on_step(turn, "explore", flags, ms)
            _record_milestones(milestones, turn, flags)

    branch_meta = FINAL_CHOICE_BRANCH.get(spec["final_choice_id"], {})
    tension_min = spec.get("branch_tension_min") or branch_meta.get("branch_tension_min")
    if tension_min and get_tension(session.state) < int(tension_min):
        set_tension(session.state, int(tension_min))
        session.manager.save(session.state)

    _isolate_final_choice(session, spec["branch_seed"])
    _set_location(session, spec["branch_action"], default="ashpoint")

    turn += 1
    session.run_turn(spec["branch_action"])
    flags = session.state["flags"]
    ms = flags["main_story"]
    if on_step:
        on_step(turn, spec["branch_action"], flags, ms)
    _record_milestones(milestones, turn, flags)

    if not flags.get("phase3_climax_ready"):
        _ensure_phase3_climax_ready(session, flags, ms)
        flags = session.state["flags"]
        ms = flags["main_story"]

    session.state["flags"]["pending_events"] = [spec["climax_seed"]]
    session.state["world"]["location"] = spec.get("climax_location", tower)
    session.manager.save(session.state)

    for action in spec["climax_actions"]:
        _set_location(session, action, default=spec.get("climax_location", tower))
        turn += 1
        session.run_turn(action)
        flags = session.state["flags"]
        ms = flags["main_story"]
        if on_step:
            on_step(turn, action, flags, ms)
        _record_milestones(milestones, turn, flags)
        if flags.get("phase3_climax_done") or ms.get("resolved_ending"):
            break

    flags = session.state["flags"]
    return milestones, flags, flags["main_story"]
