"""Phase 3 full clear simulations — ending resolution per Phase 2 path."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase3_route_helpers import (  # noqa: E402
    PHASE3_ROUTE_SPECS,
    run_phase3_route_clear,
    setup_phase3_session,
)


class Phase3ClearRouteTests(unittest.TestCase):
    def _assert_route_cleared(
        self,
        path2_id: str,
        spec: dict[str, Any],
        milestones: dict[str, int],
        flags: dict,
        ms: dict,
    ) -> None:
        self.assertTrue(flags.get("phase3_opening_done"), f"{path2_id}: opening missing")
        self.assertTrue(flags.get("phase3_crisis_done"), f"{path2_id}: crisis missing")
        self.assertTrue(flags.get("story_phase3_chosen"), f"{path2_id}: final choice missing")
        self.assertTrue(flags.get("phase3_climax_done"), f"{path2_id}: climax missing")
        self.assertTrue(ms.get("resolved_ending"), f"{path2_id}: ending not resolved")
        self.assertIn(spec["final_choice_id"], ms.get("choices_made", []))
        self.assertIn(path2_id, ms.get("choices_made", []))

    def test_route_path_alliance_ending(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase3_session(root, phase2_choice="path_alliance")
            spec = PHASE3_ROUTE_SPECS["path_alliance"]
            milestones, flags, ms = run_phase3_route_clear(session, spec)
            self._assert_route_cleared("path_alliance", spec, milestones, flags, ms)

    def test_route_path_neutral_ending(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase3_session(root, phase2_choice="path_neutral")
            spec = PHASE3_ROUTE_SPECS["path_neutral"]
            milestones, flags, ms = run_phase3_route_clear(session, spec)
            self._assert_route_cleared("path_neutral", spec, milestones, flags, ms)

    def test_route_path_betrayal_ending(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase3_session(root, phase2_choice="path_betrayal")
            spec = PHASE3_ROUTE_SPECS["path_betrayal"]
            milestones, flags, ms = run_phase3_route_clear(session, spec)
            self._assert_route_cleared("path_betrayal", spec, milestones, flags, ms)

    def test_all_routes_resolve_within_turn_budget(self) -> None:
        max_phase3_turns = 22
        for path2_id, spec in PHASE3_ROUTE_SPECS.items():
            with isolated_game_root() as root:
                session, _ = setup_phase3_session(root, phase2_choice=path2_id)
                phase3_turns = 0

                def count_step(_turn: int, _action: str, flags: dict, ms: dict) -> None:
                    nonlocal phase3_turns
                    phase3_turns += 1
                    if ms.get("resolved_ending"):
                        pass

                _milestones, flags, ms = run_phase3_route_clear(session, spec, on_step=count_step)
                self.assertTrue(ms.get("resolved_ending"), path2_id)
                self.assertLessEqual(phase3_turns, max_phase3_turns, f"{path2_id} phase3 too long")


if __name__ == "__main__":
    unittest.main()
