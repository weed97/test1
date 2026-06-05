"""Phase 1 × Phase 2 → Phase 3 full matrix (5 × 3 = 15 ending routes)."""

from __future__ import annotations

import itertools
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase1_route_helpers import PHASE1_ROUTE_SPECS  # noqa: E402
from tests.phase2_route_helpers import PHASE2_ROUTE_SPECS  # noqa: E402
from tests.phase3_route_helpers import (  # noqa: E402
    phase3_spec_for,
    run_phase3_route_clear,
    setup_phase3_session,
)

CROSS_ROUTE_PAIRS = list(
    itertools.product(PHASE1_ROUTE_SPECS.keys(), PHASE2_ROUTE_SPECS.keys())
)


class Phase3CrossRouteTests(unittest.TestCase):
    def test_cross_route_matrix(self) -> None:
        self.assertEqual(len(CROSS_ROUTE_PAIRS), 15)
        for p1_id, p2_id in CROSS_ROUTE_PAIRS:
            with self.subTest(phase1=p1_id, phase2=p2_id):
                with isolated_game_root() as root:
                    session, _ = setup_phase3_session(
                        root, phase1_choice=p1_id, phase2_choice=p2_id
                    )
                    spec = phase3_spec_for(p1_id, p2_id)
                    _milestones, flags, ms = run_phase3_route_clear(session, spec)
                    self.assertTrue(flags.get("phase3_climax_done"), f"{p1_id}+{p2_id}")
                    self.assertTrue(ms.get("resolved_ending"), f"{p1_id}+{p2_id}")
                    self.assertIn(p1_id, ms.get("choices_made", []))
                    self.assertIn(p2_id, ms.get("choices_made", []))
                    self.assertIn(spec["final_choice_id"], ms.get("choices_made", []))


if __name__ == "__main__":
    unittest.main()
