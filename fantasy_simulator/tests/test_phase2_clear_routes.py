"""Phase 2 full clear simulations for alliance / neutral / betrayal routes."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase2_route_helpers import (  # noqa: E402
    PHASE2_ROUTE_SPECS,
    run_phase2_route_clear,
    setup_phase2_session,
)


class Phase2ClearRouteTests(unittest.TestCase):
    def _assert_route_cleared(
        self,
        choice_id: str,
        milestones: dict[str, int],
        flags: dict,
        ms: dict,
    ) -> None:
        self.assertTrue(flags.get("phase2_opening_done"), f"{choice_id}: opening missing")
        self.assertTrue(flags.get("phase2_escalation_done"), f"{choice_id}: escalation missing")
        self.assertTrue(flags.get("story_phase2_chosen"), f"{choice_id}: branch not chosen")
        self.assertTrue(flags.get("phase2_climax_done"), f"{choice_id}: climax not done")
        self.assertEqual(ms.get("phase"), 3, f"{choice_id}: should enter phase 3")
        self.assertIn(choice_id, ms.get("choices_made", []), f"{choice_id}: wrong branch")

    def test_route_path_alliance(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase2_session(root, phase1_choice="ally_village")
            milestones, flags, ms = run_phase2_route_clear(
                session, PHASE2_ROUTE_SPECS["path_alliance"]
            )
            self._assert_route_cleared("path_alliance", milestones, flags, ms)

    def test_route_path_neutral(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase2_session(root, phase1_choice="stay_neutral")
            milestones, flags, ms = run_phase2_route_clear(
                session, PHASE2_ROUTE_SPECS["path_neutral"]
            )
            self._assert_route_cleared("path_neutral", milestones, flags, ms)

    def test_route_path_betrayal(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase2_session(root, phase1_choice="exploit_chaos")
            milestones, flags, ms = run_phase2_route_clear(
                session, PHASE2_ROUTE_SPECS["path_betrayal"]
            )
            self._assert_route_cleared("path_betrayal", milestones, flags, ms)

    def test_all_routes_complete_within_turn_budget(self) -> None:
        max_phase2_turns = 18
        for choice_id, spec in PHASE2_ROUTE_SPECS.items():
            with isolated_game_root() as root:
                session, _ = setup_phase2_session(root, phase1_choice=spec["phase1_choice"])
                phase2_turns = 0

                def count_step(_turn: int, _action: str, flags: dict, _ms: dict) -> None:
                    nonlocal phase2_turns
                    phase2_turns += 1
                    if flags.get("phase2_climax_done"):
                        pass

                milestones, flags, _ms = run_phase2_route_clear(session, spec, on_step=count_step)
                self.assertTrue(flags.get("phase2_climax_done"), choice_id)
                self.assertLessEqual(
                    phase2_turns,
                    max_phase2_turns,
                    f"{choice_id} phase2 took too many turns",
                )


if __name__ == "__main__":
    unittest.main()
