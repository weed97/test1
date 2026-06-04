"""Phase 1 A-route (ally_village) full clear simulation — regression guard."""

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

# Scripted optimal A-route after prologue events (turn 3+)
ALLY_ROUTE_ACTIONS: list[tuple[str, str]] = [
    ("explore", "black_smoke"),
    ("explore", "rumor_delay"),
    ("explore", "rumor_delay"),
    ("talk lilian", "rumors"),
    ("talk torren", "rumors"),
    ("talk elder maren", "elder_request"),
    ("talk elder maren", "elder_accept"),
    ("investigate forest", "mountain_1"),
    ("investigate forest", "mountain_2"),
    ("talk grey cloak", "warden"),
    ("talk elder maren", "branch_A"),
    ("talk lilian", "merchant"),
    ("explore", "knight_arrival"),
    ("explore forest", "climax_village"),
    ("explore ashpoint", "climax_village"),
]


def _setup_ally_session(root: Path, *, seed: int = 42) -> tuple[GameSession, MainStoryEngine]:
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


class Phase1AllyClearRouteTests(unittest.TestCase):
    def test_full_ally_village_clear_to_phase2(self) -> None:
        with isolated_game_root() as root:
            session, engine = _setup_ally_session(root)
            milestones: dict[str, int] = {}

            for i, (action, _note) in enumerate(ALLY_ROUTE_ACTIONS, start=1):
                session.run_turn(action)
                flags = session.state["flags"]
                ms = flags["main_story"]
                for key in (
                    "black_smoke_seen",
                    "phase1_rumors_spread",
                    "phase1_elder_request",
                    "phase1_elder_accepted",
                    "story_phase1_chosen",
                    "phase1_climax_ready",
                    "phase1_climax_done",
                ):
                    if flags.get(key) and key not in milestones:
                        milestones[key] = i
                if flags.get("phase1_climax_done"):
                    break

            flags = session.state["flags"]
            ms = flags["main_story"]

            self.assertIn("black_smoke_seen", milestones, "smoke not seen")
            self.assertIn("phase1_rumors_spread", milestones, "rumors did not spread")
            self.assertIn("phase1_elder_accepted", milestones, "elder accept missing")
            self.assertIn("story_phase1_chosen", milestones, "branch A not chosen")
            self.assertTrue(flags.get("phase1_climax_done"), "climax not completed")
            self.assertEqual(ms.get("phase"), 2, "should enter phase 2 after climax")
            self.assertIn("ally_village", ms.get("choices_made", []))
            self.assertLessEqual(milestones.get("phase1_climax_done", 99), len(ALLY_ROUTE_ACTIONS))

    def test_smoke_turn_synced_with_event_log(self) -> None:
        with isolated_game_root() as root:
            session, engine = _setup_ally_session(root)
            session.run_turn("explore")
            flags = session.state["flags"]
            ms = flags["main_story"]
            self.assertTrue(flags.get("black_smoke_seen"))
            smoke_turn = int(ms.get("smoke_seen_turn", 0))
            self.assertGreaterEqual(smoke_turn, 3)
            self.assertLessEqual(smoke_turn, 5)


if __name__ == "__main__":
    unittest.main()
