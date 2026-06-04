"""Shared helpers for Phase 2 three-route clear simulations (after Phase 1)."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from tests.phase1_route_helpers import (
    PHASE1_ROUTE_SPECS,
    run_phase1_route_clear,
    setup_phase1_session,
)
from utils.game_session import GameSession
from utils.main_story_engine import MainStoryEngine
from utils.world_tension import set_tension

PHASE2_COMMON_PREFIX: list[str] = [
    "talk elder maren",
    "investigate forest",
]

PHASE2_ROUTE_SPECS: dict[str, dict[str, Any]] = {
    "path_alliance": {
        "choice_id": "path_alliance",
        "phase1_choice": "ally_village",
        "branch_seed": "story_choice_alliance",
        "branch_action": "explore",
        "climax_seed": "phase2_climax_alliance",
        "climax_actions": ["explore forest"],
        "climax_location": "ashpoint",
    },
    "path_neutral": {
        "choice_id": "path_neutral",
        "phase1_choice": "stay_neutral",
        "branch_seed": "story_choice_neutral",
        "branch_action": "explore",
        "climax_seed": "phase2_climax_neutral",
        "climax_actions": ["explore forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
    "path_betrayal": {
        "choice_id": "path_betrayal",
        "phase1_choice": "exploit_chaos",
        "branch_seed": "story_choice_betrayal",
        "branch_action": "explore",
        "branch_location": "ashpoint",
        "climax_seed": "phase2_climax_betrayal",
        "climax_actions": ["investigate forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
}

PHASE2_MILESTONE_FLAGS = (
    "phase2_opening_done",
    "phase2_escalation_done",
    "story_phase2_chosen",
    "phase2_climax_ready",
    "phase2_climax_done",
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


def _set_pending(session: GameSession, seed_ids: list[str]) -> None:
    session.state["flags"]["pending_events"] = seed_ids
    session.manager.save(session.state)


def _boost_tension_for_phase2(session: GameSession, target: int = 50) -> None:
    set_tension(session.state, target)
    session.manager.save(session.state)


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
    session.state["world"]["location"] = "ashpoint"
    session.manager.save(session.state)

    for action in PHASE2_COMMON_PREFIX:
        if "forest" in action:
            session.state["world"]["location"] = "북쪽 숲 — 연기가 보이는 외곽"
        else:
            session.state["world"]["location"] = "ashpoint"
        session.manager.save(session.state)
        turn += 1
        session.run_turn(action)
        flags = session.state["flags"]
        ms = flags["main_story"]
        if on_step:
            on_step(turn, action, flags, ms)
        for key in PHASE2_MILESTONE_FLAGS:
            if flags.get(key) and key not in milestones:
                milestones[key] = turn

    _boost_tension_for_phase2(session, 50)
    pending = session.state["flags"].setdefault("pending_events", [])
    pending[:] = [sid for sid in pending if sid.startswith("story_choice_")]
    _set_pending(session, ["phase2_faction_raid"])
    turn += 1
    session.state["world"]["location"] = "북쪽 숲 — 연기가 보이는 외곽"
    session.manager.save(session.state)
    session.run_turn("explore")
    flags = session.state["flags"]
    ms = flags["main_story"]
    if on_step:
        on_step(turn, "explore", flags, ms)
    for key in PHASE2_MILESTONE_FLAGS:
        if flags.get(key) and key not in milestones:
            milestones[key] = turn

    pending = session.state["flags"].setdefault("pending_events", [])
    for sid in ("story_choice_alliance", "story_choice_neutral", "story_choice_betrayal"):
        while sid in pending:
            pending.remove(sid)
    _set_pending(session, [spec["branch_seed"]])
    session.state["world"]["location"] = spec.get("branch_location", "ashpoint")
    session.manager.save(session.state)

    turn += 1
    session.run_turn(spec["branch_action"])
    flags = session.state["flags"]
    ms = flags["main_story"]
    if on_step:
        on_step(turn, spec["branch_action"], flags, ms)
    for key in PHASE2_MILESTONE_FLAGS:
        if flags.get(key) and key not in milestones:
            milestones[key] = turn

    if not flags.get("phase2_climax_ready"):
        rep = flags.setdefault("faction_reputation", {})
        rep.setdefault("ashpoint_council", 25)
        flags["story_faction_clash_seen"] = True
        engine = MainStoryEngine(session.manager.base_dir)
        story = engine.story_def(ms["id"])
        if story and flags.get("story_phase2_chosen"):
            engine._update_phase2_climax_readiness(session.state, story, ms)
        session.manager.save(session.state)

    _set_pending(session, [spec["climax_seed"]])
    session.state["world"]["location"] = spec.get("climax_location", "ashpoint")
    session.manager.save(session.state)

    for action in spec["climax_actions"]:
        turn += 1
        session.run_turn(action)
        flags = session.state["flags"]
        ms = flags["main_story"]
        if on_step:
            on_step(turn, action, flags, ms)
        for key in PHASE2_MILESTONE_FLAGS:
            if flags.get(key) and key not in milestones:
                milestones[key] = turn
        if flags.get("phase2_climax_done"):
            break

    flags = session.state["flags"]
    return milestones, flags, flags["main_story"]
