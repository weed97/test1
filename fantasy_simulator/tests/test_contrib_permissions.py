"""Contribution tier permissions and growth goals."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.contrib_permissions import (  # noqa: E402
    award_contribution,
    can,
    evaluate_growth_goals,
    get_world_building,
    next_growth_goal,
    resolve_tier,
    sync_tier_from_score,
    tier_progress,
    validate_submission,
)


class ContribPermissionsTests(unittest.TestCase):
    def _flags(self) -> dict:
        return {"world_building": get_world_building({})}

    def test_observer_cannot_submit_rumor(self) -> None:
        flags = self._flags()
        self.assertFalse(can(flags, "submit_rumor"))

    def test_scribe_tier_allows_rumor_after_score(self) -> None:
        flags = self._flags()
        wb = flags["world_building"]
        wb["contribution_score"] = 100
        sync_tier_from_score(flags)
        self.assertEqual(wb["contributor_tier"], "scribe")
        self.assertTrue(can(flags, "submit_rumor"))

    def test_validate_rejects_over_detail(self) -> None:
        flags = self._flags()
        wb = flags["world_building"]
        wb["contribution_score"] = 100
        sync_tier_from_score(flags)
        ok, issues = validate_submission(
            flags,
            {
                "kind": "rumor",
                "field_count": 4,
                "dialogue_lines": 10,
                "branch_count": 0,
                "detail_level": 2,
            },
        )
        self.assertFalse(ok)
        self.assertTrue(any("대사" in i for i in issues))

    def test_award_approved_rumor_increases_score_and_tier(self) -> None:
        flags = self._flags()
        wb = flags["world_building"]
        wb["contribution_score"] = 100
        sync_tier_from_score(flags)
        entry = award_contribution(
            flags,
            {
                "id": "rumor_1",
                "kind": "rumor",
                "field_count": 4,
                "dialogue_lines": 1,
                "branch_count": 0,
                "detail_level": 2,
            },
            approved=True,
            quality_score=1.0,
        )
        self.assertEqual(entry["status"], "approved")
        self.assertGreater(wb["contribution_score"], 100)
        self.assertTrue(can(flags, "submit_rumor"))

    def test_workshop_goal_unlocks_on_flag(self) -> None:
        flags = self._flags()
        wb = flags["world_building"]
        wb["workshop_unlocked"] = True
        done = evaluate_growth_goals(flags)
        self.assertTrue(any(g["id"] == "first_workshop_visit" for g in done))
        self.assertIn("first_workshop_visit", wb["completed_goals"])

    def test_next_growth_goal_returns_first_incomplete(self) -> None:
        flags = self._flags()
        goal = next_growth_goal(flags)
        self.assertIsNotNone(goal)
        self.assertEqual(goal["id"], "first_workshop_visit")

    def test_tier_progress_fraction(self) -> None:
        flags = self._flags()
        flags["world_building"]["contribution_score"] = 50
        prog = tier_progress(flags)
        self.assertEqual(prog["current_tier"], "observer")
        self.assertEqual(prog["next_tier"], "scribe")
        self.assertGreater(prog["progress_fraction"], 0.0)

    def test_resolve_tier_worldwright(self) -> None:
        tier = resolve_tier(9000)
        self.assertEqual(tier["id"], "worldwright")
        self.assertEqual(tier["detail_level"], 5)


if __name__ == "__main__":
    unittest.main()
