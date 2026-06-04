"""Phase 1 × Phase 2 cross-route smoke tests (representative matrix)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase1_route_helpers import PHASE1_ROUTE_SPECS  # noqa: E402
from tests.phase2_route_helpers import (  # noqa: E402
    PHASE2_ROUTE_SPECS,
    phase2_spec_for,
    run_phase2_route_clear,
    setup_phase2_session,
)

# One Phase 1 route per Phase 2 branch + two extra pairings.
CROSS_ROUTE_PAIRS = [
    ("ally_village", "path_alliance"),
    ("seek_truth", "path_neutral"),
    ("pursue_power", "path_betrayal"),
    ("exploit_chaos", "path_neutral"),
    ("stay_neutral", "path_alliance"),
]


class Phase2CrossRouteTests(unittest.TestCase):
    def test_cross_route_matrix(self) -> None:
        for p1_id, p2_id in CROSS_ROUTE_PAIRS:
            with self.subTest(phase1=p1_id, phase2=p2_id):
                self.assertIn(p1_id, PHASE1_ROUTE_SPECS)
                self.assertIn(p2_id, PHASE2_ROUTE_SPECS)
                with isolated_game_root() as root:
                    session, _ = setup_phase2_session(root, phase1_choice=p1_id)
                    p2_spec = phase2_spec_for(p1_id, p2_id)
                    _milestones, flags, ms = run_phase2_route_clear(session, p2_spec)
                    self.assertTrue(flags.get("phase2_climax_done"), f"{p1_id}+{p2_id}")
                    self.assertEqual(ms.get("phase"), 3)
                    self.assertIn(p1_id, ms.get("choices_made", []))
                    self.assertIn(p2_id, ms.get("choices_made", []))


if __name__ == "__main__":
    unittest.main()
