"""Phase 1 A-route (ally_village) clear simulation — kept for backward compatibility."""

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


class Phase1AllyClearRouteTests(unittest.TestCase):
    def test_full_ally_village_clear_to_phase2(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase1_session(root)
            milestones, flags, ms = run_phase1_route_clear(session, PHASE1_ROUTE_SPECS["ally_village"])
            self.assertIn("black_smoke_seen", milestones)
            self.assertIn("phase1_elder_accepted", milestones)
            self.assertTrue(flags.get("phase1_climax_done"))
            self.assertEqual(ms.get("phase"), 2)
            self.assertIn("ally_village", ms.get("choices_made", []))

    def test_smoke_turn_synced_with_event_log(self) -> None:
        with isolated_game_root() as root:
            session, _ = setup_phase1_session(root)
            session.run_turn("explore")
            flags = session.state["flags"]
            ms = flags["main_story"]
            self.assertTrue(flags.get("black_smoke_seen"))
            smoke_turn = int(ms.get("smoke_seen_turn", 0))
            self.assertGreaterEqual(smoke_turn, 3)
            self.assertLessEqual(smoke_turn, 5)


if __name__ == "__main__":
    unittest.main()
