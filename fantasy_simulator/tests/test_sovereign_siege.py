"""Sovereign siege tick — simplified net DPS."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.sovereign_siege import (  # noqa: E402
    coalition_net_dps_milli,
    load_arthur_coalition_config,
    sovereign_siege_status,
    tick_sovereign_coalition_siege,
)


class SovereignSiegeTests(unittest.TestCase):
    def test_net_dps_and_tick(self) -> None:
        with isolated_game_root() as root:
            coalition = load_arthur_coalition_config(root)
            self.assertEqual(coalition_net_dps_milli(coalition_cfg=coalition), 40_000)
            state: dict = {"flags": {"ecology": {}}}
            tick_sovereign_coalition_siege(state, base_dir=root)
            status = sovereign_siege_status(state, base_dir=root)
            self.assertEqual(status["seconds_to_kill_at_anchor"], 25_000)
            self.assertIn("hp_milli", status)


if __name__ == "__main__":
    unittest.main()
