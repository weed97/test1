"""Headless Phase 1 playtest scenarios for balance validation."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.main_story_engine import MainStoryEngine  # noqa: E402
from utils.world_tension import get_tension  # noqa: E402


def _fresh_session(root: Path, seed: int = 42) -> tuple[GameSession, MainStoryEngine]:
    session = GameSession.from_root(root, mode="rule", seed=seed)
    engine = MainStoryEngine(root)
    engine.select_story(session.state, "ashen_seal_cracking", turn=0)
    flags = session.state.setdefault("flags", {})
    flags["pending_events"] = []
    flags["quests"] = {"active": "smoke_on_the_mountain", "stage": 1, "completed": []}
    return session, engine


def _run_actions(session: GameSession, actions: list[str]) -> None:
    for action in actions:
        session.run_turn(action)


class Phase1PlaytestTests(unittest.TestCase):
    def test_no_early_phase2_on_high_tension(self) -> None:
        with isolated_game_root() as root:
            session, engine = _fresh_session(root)
            state = session.state
            flags = state["flags"]
            ms = engine.ensure_initialized(state)
            ms["progress"] = 20
            state["world"]["tension"] = 85
            lines = engine._check_phase1_exit(state, engine.story_def("ashen_seal_cracking"), ms)
            self.assertFalse(lines)
            self.assertEqual(ms["phase"], 1)

    def test_elder_decline_requires_two_mountain_visits(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "main_story": {"id": "ashen_seal_cracking", "phase": 1},
                    "phase1_elder_request": True,
                    "faction_reputation": {"ashpoint_council": 0},
                },
            }
            engine.ensure_initialized(state)
            lines1 = engine.record_mountain_visit(state)
            self.assertFalse(state["flags"].get("phase1_elder_declined"))
            self.assertTrue(any("눈치" in line for line in lines1))
            engine.record_mountain_visit(state)
            self.assertTrue(state["flags"].get("phase1_elder_declined"))

    def test_high_tension_stays_phase1_without_climax(self) -> None:
        with isolated_game_root() as root:
            session, engine = _fresh_session(root)
            flags = session.state["flags"]
            ms = engine.ensure_initialized(session.state)
            flags.update(
                {
                    "story_phase1_chosen": True,
                }
            )
            ms.update(
                {
                    "phase1_step": 4,
                    "phase1_subphase": "late",
                    "progress": 20,
                    "mountain_visits": 1,
                    "choices_made": ["ally_village"],
                    "factions_contacted": ["ashpoint_council"],
                }
            )
            session.state["world"]["tension"] = 70
            session.manager.save(session.state)
            for _ in range(5):
                session.run_turn("explore")
            self.assertEqual(session.state["flags"]["main_story"]["phase"], 1)
            self.assertFalse(session.state["flags"].get("phase1_climax_done"))

    def test_climax_completes_phase1(self) -> None:
        with isolated_game_root() as root:
            session, engine = _fresh_session(root)
            flags = session.state["flags"]
            ms = engine.ensure_initialized(session.state)
            flags.update({"story_phase1_chosen": True, "phase1_climax_ready": True})
            ms.update({"progress": 20, "choices_made": ["ally_village"]})
            flags["pending_events"] = ["phase1_climax_village"]
            session.state["world"]["location"] = "ashpoint"
            session.manager.save(session.state)
            session.run_turn("explore")
            self.assertTrue(session.state["flags"].get("phase1_climax_done"))
            self.assertEqual(session.state["flags"]["main_story"]["phase"], 2)

    def test_mountain_first_route_warns_before_decline(self) -> None:
        with isolated_game_root() as root:
            session, engine = _fresh_session(root)
            session.state["flags"]["phase1_elder_request"] = True
            engine.ensure_initialized(session.state)
            session.run_turn("investigate forest")
            self.assertFalse(session.state["flags"].get("phase1_elder_declined"))
            session.run_turn("investigate forest")
            self.assertTrue(session.state["flags"].get("phase1_elder_declined"))

    def test_climax_gate_achievable_after_branch(self) -> None:
        with isolated_game_root() as root:
            engine = MainStoryEngine(root)
            state = {
                "flags": {
                    "story_phase1_chosen": True,
                    "faction_reputation": {"ashpoint_council": 22},
                    "main_story": {
                        "id": "ashen_seal_cracking",
                        "phase": 1,
                        "mountain_visits": 2,
                        "choices_made": ["ally_village"],
                        "factions_contacted": ["ashpoint_council", "silver_cross_order"],
                    },
                },
                "world": {"tension": 28},
            }
            engine.ensure_initialized(state)
            story = engine.story_def("ashen_seal_cracking")
            assert story
            lines = engine._update_climax_readiness(state, story, state["flags"]["main_story"])
            self.assertTrue(state["flags"].get("phase1_climax_ready"))
            self.assertTrue(lines)


if __name__ == "__main__":
    unittest.main()
