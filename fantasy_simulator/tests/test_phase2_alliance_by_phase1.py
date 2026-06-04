"""Phase 2 alliance route clears for each Phase 1 branch (A–E)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase2_alliance_specs import ALLIANCE_ROUTE_BY_PHASE1  # noqa: E402
from tests.phase2_route_helpers import run_phase2_route_clear, setup_phase2_session  # noqa: E402


class Phase2AllianceByPhase1Tests(unittest.TestCase):
    def test_alliance_routes_clear_per_phase1(self) -> None:
        for phase1_id, alliance_spec in ALLIANCE_ROUTE_BY_PHASE1.items():
            with self.subTest(phase1=phase1_id):
                with isolated_game_root() as root:
                    session, _ = setup_phase2_session(root, phase1_choice=phase1_id)
                    spec = {**alliance_spec, "choice_id": "path_alliance"}
                    _milestones, flags, ms = run_phase2_route_clear(session, spec)
                    self.assertTrue(flags.get("phase2_climax_done"), phase1_id)
                    self.assertEqual(ms.get("phase"), 3, phase1_id)
                    self.assertIn("path_alliance", ms.get("choices_made", []))
                    self.assertEqual(
                        flags.get("alliance_faction"),
                        alliance_spec["alliance_faction"],
                        phase1_id,
                    )


if __name__ == "__main__":
    unittest.main()
