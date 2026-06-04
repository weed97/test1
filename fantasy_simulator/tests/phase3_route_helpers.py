"""Shared helpers for Phase 3 ending-route clear simulations (after Phase 2)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tests.phase2_alliance_specs import ALLIANCE_ROUTE_BY_PHASE1
from tests.phase2_route_helpers import (
    PHASE2_ROUTE_SPECS,
    run_phase2_route_clear,
    setup_phase2_session,
)
from utils.game_session import GameSession
from utils.main_story_engine import MainStoryEngine
from utils.world_tension import set_tension

PHASE3_COMMON_PREFIX: list[str] = [
    "investigate forest",
    "talk elder maren",
    "explore forest",
]

PHASE3_ALLIANCE_CLIMAX: dict[str, str] = {
    "ally_village": "phase3_climax_alliance_council",
    "seek_truth": "phase3_climax_alliance_wardens",
    "pursue_power": "phase3_climax_alliance_covenant",
    "exploit_chaos": "phase3_climax_alliance_merchants",
    "stay_neutral": "phase3_climax_alliance_knights",
}

PHASE3_ROUTE_SPECS: dict[str, dict[str, Any]] = {
    "path_alliance": {
        "phase2_choice": "path_alliance",
        "phase1_choice": "ally_village",
        "final_choice_id": "final_reinforce",
        "branch_seed": "story_choice_final_reinforce",
        "branch_action": "talk elder maren",
        "climax_seed": PHASE3_ALLIANCE_CLIMAX["ally_village"],
        "climax_actions": ["investigate forest"],
        "climax_location": "관측탑",
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


def phase3_spec_for(
    phase2_choice: str,
    *,
    phase1_choice: str | None = None,
) -> dict[str, Any]:
    """Build Phase 3 run spec; alliance climax follows Phase 1 branch."""
    spec = dict(PHASE3_ROUTE_SPECS[phase2_choice])
    p1 = phase1_choice or spec.get("phase1_choice")
    if p1:
        spec["phase1_choice"] = p1
    if phase2_choice == "path_alliance" and p1:
        spec["climax_seed"] = PHASE3_ALLIANCE_CLIMAX[p1]
        p2 = ALLIANCE_ROUTE_BY_PHASE1[p1]
        spec["final_choice_id"] = "final_reinforce" if p1 == "ally_village" else spec.get(
            "final_choice_id", "final_chaos"
        )
        if p1 == "pursue_power":
            spec["final_choice_id"] = "final_break"
    return spec


def setup_phase3_session(
    root: Path,
    *,
    phase2_choice: str = "path_alliance",
    phase1_choice: str | None = None,
    seed: int = 42,
) -> tuple[GameSession, MainStoryEngine]:
    """Complete Phases 1–2, then return session in Phase 3."""
    p2_spec = PHASE2_ROUTE_SPECS[phase2_choice]
    p1 = phase1_choice or p2_spec["phase1_choice"]
    session, engine = setup_phase2_session(root, phase1_choice=p1, seed=seed)
    if phase2_choice == "path_alliance":
        run_phase2_route_clear(session, {**ALLIANCE_ROUTE_BY_PHASE1[p1], "choice_id": "path_alliance"})
    else:
        run_phase2_route_clear(session, p2_spec)
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
    pending = session.state["flags"].setdefault("pending_events", [])
    for sid in FINAL_CHOICE_SEEDS:
        while sid in pending:
            pending.remove(sid)
    if branch_seed not in pending:
        pending.append(branch_seed)
    session.manager.save(session.state)


def _record_milestones(
    milestones: dict[str, int],
    turn: int,
    flags: dict[str, Any],
) -> None:
    for key in PHASE3_MILESTONE_FLAGS:
        if flags.get(key) and key not in milestones:
            milestones[key] = turn


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
    tower = "관측탑"

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

    if not flags.get("phase3_crisis_done"):
        set_tension(session.state, 58)
        session.manager.save(session.state)
        _set_location(session, "explore forest", default=tower)
        for _ in range(4):
            if session.state["flags"].get("phase3_crisis_done"):
                break
            turn += 1
            session.run_turn("explore")
            flags = session.state["flags"]
            ms = flags["main_story"]
            if on_step:
                on_step(turn, "explore", flags, ms)
            _record_milestones(milestones, turn, flags)

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
        set_tension(session.state, 58)
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
        flags = session.state["flags"]

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
