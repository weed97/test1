"""Shared helpers for Phase 1 five-route clear simulations."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from utils.game_session import GameSession
from utils.main_story_engine import MainStoryEngine

# Shared early-game sequence (prologue turns 1–2 already in event_log).
PHASE1_COMMON_PREFIX: list[str] = [
    "explore",
    "explore",
    "explore",
    "talk lilian",
    "talk torren",
    "talk elder maren",
    "talk elder maren",
    "investigate forest",
    "investigate forest",
    "talk grey cloak",
]

PHASE1_ROUTE_SPECS: dict[str, dict[str, Any]] = {
    "ally_village": {
        "choice_id": "ally_village",
        "branch_seed": "story_choice_council",
        "branch_action": "talk elder maren",
        "branch_time": None,
        "climax_seed": "phase1_climax_village",
        "climax_actions": ["explore forest"],
        "climax_location": "ashpoint",
    },
    "seek_truth": {
        "choice_id": "seek_truth",
        "branch_seed": "story_choice_warden",
        "branch_action": "talk grey cloak",
        "branch_time": None,
        "climax_seed": "phase1_climax_truth",
        "climax_actions": ["explore forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
    "pursue_power": {
        "choice_id": "pursue_power",
        "branch_seed": "story_choice_covenant",
        "branch_action": "explore",
        "branch_time": "evening",
        "climax_seed": "phase1_climax_power",
        "climax_actions": ["investigate forest", "explore forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
    "exploit_chaos": {
        "choice_id": "exploit_chaos",
        "branch_seed": "story_choice_opportunist",
        "branch_action": "explore",
        "branch_time": None,
        "climax_seed": "phase1_climax_chaos",
        "climax_actions": ["explore forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
    "stay_neutral": {
        "choice_id": "stay_neutral",
        "branch_seed": "story_choice_stay_neutral",
        "branch_action": "rest",
        "branch_time": None,
        "climax_seed": "phase1_climax_neutral",
        "climax_actions": ["explore forest"],
        "climax_location": "북쪽 숲 — 연기가 보이는 외곽",
    },
}

MILESTONE_FLAGS = (
    "black_smoke_seen",
    "phase1_rumors_spread",
    "phase1_elder_request",
    "phase1_elder_accepted",
    "story_phase1_chosen",
    "phase1_climax_ready",
    "phase1_climax_done",
)


def setup_phase1_session(root: Path, *, seed: int = 42) -> tuple[GameSession, MainStoryEngine]:
    session = GameSession.from_root(root, mode="rule", seed=seed)
    engine = MainStoryEngine(root)
    engine.select_story(session.state, "ashen_seal_cracking", turn=0)
    flags = session.state.setdefault("flags", {})
    flags["pending_events"] = ["black_smoke"]
    flags["quests"] = {"active": "smoke_on_the_mountain", "stage": 1, "completed": []}
    flags["quest_talked_npcs"] = []
    session.state["world"]["location"] = "ashpoint"
    session.manager.save(session.state)
    session.manager.refresh_state(session.state)
    return session, engine


def _set_pending(session: GameSession, seed_ids: list[str]) -> None:
    session.state["flags"]["pending_events"] = seed_ids
    session.manager.save(session.state)


def run_phase1_route_clear(
    session: GameSession,
    spec: dict[str, Any],
    *,
    on_step: Callable[[int, str, dict[str, Any], dict[str, Any]], None] | None = None,
) -> tuple[dict[str, int], dict[str, Any], dict[str, Any]]:
    """Run common prefix, branch, and climax. Returns milestones, flags, main_story."""
    milestones: dict[str, int] = {}
    turn = 0

    for action in PHASE1_COMMON_PREFIX:
        turn += 1
        session.run_turn(action)
        flags = session.state["flags"]
        ms = flags["main_story"]
        if on_step:
            on_step(turn, action, flags, ms)
        for key in MILESTONE_FLAGS:
            if flags.get(key) and key not in milestones:
                milestones[key] = turn

    if spec.get("branch_time"):
        session.state["world"]["time_of_day"] = spec["branch_time"]
    _set_pending(session, [spec["branch_seed"]])
    turn += 1
    session.run_turn(spec["branch_action"])
    flags = session.state["flags"]
    ms = flags["main_story"]
    if on_step:
        on_step(turn, spec["branch_action"], flags, ms)
    for key in MILESTONE_FLAGS:
        if flags.get(key) and key not in milestones:
            milestones[key] = turn

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
        for key in MILESTONE_FLAGS:
            if flags.get(key) and key not in milestones:
                milestones[key] = turn
        if flags.get("phase1_climax_done"):
            break

    flags = session.state["flags"]
    return milestones, flags, flags["main_story"]
