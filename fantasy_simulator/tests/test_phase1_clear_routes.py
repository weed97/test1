"""Phase 1 full clear simulations for all five branch routes (A–E)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase1_route_helpers import (  # noqa: E402
    PHASE1_ROUTE_SPECS,
    run_phase1_route_clear,
    setup_phase1_session,
)


class Phase1ClearRouteTests(unittest.TestCase):
    def _assert_route_cleared(self, choice_id: str, milestones: dict[str, int], flags: dict, ms: dict) -> None:
        self.assertIn("black_smoke_seen", milestones, f"{choice_id}: smoke not seen")
        self.assertIn("phase1_rumors_spread", milestones, f"{choice_id}: rumors missing")
        self.assertIn("phase1_elder_accepted", milestones, f"{choice_id}: elder accept missing")
        self.assertIn("story_phase1_chosen", milestones, f"{choice_id}: branch not chosen")
        self.assertTrue(flags.get("phase1_climax_done"), f"{choice_id}: climax not done")
        self.assertEqual(ms.get("phase"), 2, f"{choice_id}: should enter phase 2")
        self.assertIn(choice_id, ms.get("choices_made", []), f"{choice_id}: wrong branch")

    def test_route_ally_village(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase1_session(root)
            milestones, flags, ms = run_phase1_route_clear(session, PHASE1_ROUTE_SPECS["ally_village"])
            self._assert_route_cleared("ally_village", milestones, flags, ms)

    def test_route_seek_truth(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase1_session(root)
            milestones, flags, ms = run_phase1_route_clear(session, PHASE1_ROUTE_SPECS["seek_truth"])
            self._assert_route_cleared("seek_truth", milestones, flags, ms)

    def test_route_pursue_power(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase1_session(root)
            milestones, flags, ms = run_phase1_route_clear(session, PHASE1_ROUTE_SPECS["pursue_power"])
            self._assert_route_cleared("pursue_power", milestones, flags, ms)

    def test_route_exploit_chaos(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase1_session(root)
            milestones, flags, ms = run_phase1_route_clear(session, PHASE1_ROUTE_SPECS["exploit_chaos"])
            self._assert_route_cleared("exploit_chaos", milestones, flags, ms)

    def test_route_stay_neutral(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase1_session(root)
            milestones, flags, ms = run_phase1_route_clear(session, PHASE1_ROUTE_SPECS["stay_neutral"])
            self._assert_route_cleared("stay_neutral", milestones, flags, ms)

    def test_all_routes_complete_within_turn_budget(self) -> None:
        max_turns = 20
        for choice_id, spec in PHASE1_ROUTE_SPECS.items():
            with isolated_game_root() as root:
                session, _ = setup_phase1_session(root)
                turn_count = 0

                def count_step(turn: int, _action: str, flags: dict, _ms: dict) -> None:
                    nonlocal turn_count
                    turn_count = turn
                    if flags.get("phase1_climax_done"):
                        pass

                milestones, flags, ms = run_phase1_route_clear(session, spec, on_step=count_step)
                self.assertTrue(flags.get("phase1_climax_done"), choice_id)
                self.assertLessEqual(
                    milestones.get("phase1_climax_done", turn_count),
                    max_turns,
                    f"{choice_id} took too many turns",
                )


if __name__ == "__main__":
    unittest.main()
