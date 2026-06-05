"""Phase 3 alliance ending clears for each Phase 1 branch (A–E)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from tests.phase3_alliance_specs import ALLIANCE_ROUTE_BY_PHASE1_PHASE3  # noqa: E402
from tests.phase3_route_helpers import (  # noqa: E402
    phase3_spec_for,
    run_phase3_route_clear,
    setup_phase3_session,
)


class Phase3AllianceByPhase1Tests(unittest.TestCase):
    def test_alliance_endings_clear_per_phase1(self) -> None:
        for phase1_id, alliance_spec in ALLIANCE_ROUTE_BY_PHASE1_PHASE3.items():
            with self.subTest(phase1=phase1_id):
                with isolated_game_root() as root:
                    session, _ = setup_phase3_session(
                        root, phase1_choice=phase1_id, phase2_choice="path_alliance"
                    )
                    spec = phase3_spec_for(phase1_id, "path_alliance")
                    _milestones, flags, ms = run_phase3_route_clear(session, spec)
                    self.assertTrue(flags.get("phase3_climax_done"), phase1_id)
                    self.assertTrue(ms.get("resolved_ending"), phase1_id)
                    self.assertEqual(
                        flags.get("alliance_faction"),
                        _expected_faction(phase1_id),
                        phase1_id,
                    )
                    self.assertEqual(spec["climax_seed"], alliance_spec["climax_seed"])
                    self.assertIn(spec["final_choice_id"], ms.get("choices_made", []))


def _expected_faction(phase1_id: str) -> str:
    from tests.phase2_alliance_specs import ALLIANCE_ROUTE_BY_PHASE1

    return ALLIANCE_ROUTE_BY_PHASE1[phase1_id]["alliance_faction"]


if __name__ == "__main__":
    unittest.main()
