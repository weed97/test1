"""World clock — minute_of_day and period sync."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.world_clock import (  # noqa: E402
    advance_world_minutes,
    ensure_world_clock,
    format_clock,
    minute_to_time_of_day,
)


class WorldClockTests(unittest.TestCase):
    def test_minute_to_period(self) -> None:
        self.assertEqual(minute_to_time_of_day(8 * 60), "morning")
        self.assertEqual(minute_to_time_of_day(14 * 60), "afternoon")
        self.assertEqual(minute_to_time_of_day(22 * 60), "night")

    def test_advance_minutes_rolls_day(self) -> None:
        world = {"day": 1, "time_of_day": "night", "minute_of_day": 22 * 60}
        advance_world_minutes(world, 240)
        self.assertEqual(world["day"], 2)
        self.assertEqual(world["minute_of_day"], 2 * 60)
        self.assertEqual(world["time_of_day"], "night")

    def test_ensure_migrates_legacy(self) -> None:
        world = {"time_of_day": "afternoon", "day": 3}
        ensure_world_clock(world)
        self.assertIn("minute_of_day", world)
        self.assertEqual(world["time_of_day"], "afternoon")
        self.assertEqual(format_clock(world["minute_of_day"]), "14:00")


if __name__ == "__main__":
    unittest.main()
