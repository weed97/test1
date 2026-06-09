"""Kingdom charter — founding costs, barrier, fortress, military."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root  # noqa: E402
from utils.game_session import GameSession  # noqa: E402
from utils.kingdom_system import (  # noqa: E402
    apply_siege_damage,
    build_interior,
    can_found_kingdom,
    complete_kingdom_founding,
    founding_cost_preview,
    get_kingdom_charter,
    kingdom_status,
    list_government_doctrines,
    recruit_military,
    set_kingdom_doctrine,
    tick_kingdom,
    upgrade_fortification,
)
from utils.settlement_build import (  # noqa: E402
    get_player_settlement,
    tick_player_build_projects,
    try_start_kingdom,
)


def _ready_for_kingdom(state: dict, root: Path) -> None:
    from utils.currency import grant

    ps = get_player_settlement(state)
    ps["construction_level"] = 5
    ps["hired_workers"] = 10
    ps["stockpile"] = {"wood": 2000, "stone": 3000, "iron": 1000, "crystal": 200}
    grant(state, gold=200_000, base_dir=root)
    for bid in ("hall", "blacksmith", "barracks", "market"):
        ps.setdefault("completed_buildings", []).append(
            {"building_id": bid, "label": bid}
        )


class KingdomSystemTests(unittest.TestCase):
    def _ecology_state(self, root: Path) -> dict:
        session = GameSession.from_root(root, mode="rule", seed=1)
        session.state.setdefault("flags", {})["game_mode"] = "ecology"
        session.state.setdefault("inventory", {})["wallet"] = {
            "copper": 0,
            "silver": 0,
            "gold": 0,
        }
        return session.state

    def test_founding_cost_is_massive(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            preview = founding_cost_preview(state, base_dir=root)
            self.assertGreaterEqual(preview["gold_cost_total"], 100_000)
            self.assertFalse(preview["can_found"])

    def test_can_found_when_ready(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            _ready_for_kingdom(state, root)
            ok, err = can_found_kingdom(state, base_dir=root)
            self.assertTrue(ok, err)

    def test_start_kingdom_deducts_ancillary_gold(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            _ready_for_kingdom(state, root)
            from utils.currency import party_gold

            before = party_gold(state, base_dir=root)
            r = try_start_kingdom(
                state,
                map_id="ashpoint_01",
                x=10,
                y=10,
                base_dir=root,
                kingdom_name="잿빛 왕국",
            )
            self.assertTrue(r["ok"], r)
            spent = r["costs"]["gold_spent_total"]
            self.assertGreaterEqual(spent, 100_000)
            self.assertEqual(party_gold(state, base_dir=root), before - spent)

    def test_kingdom_completion_creates_charter_with_barrier(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            _ready_for_kingdom(state, root)
            result = complete_kingdom_founding(
                state,
                map_id="ashpoint_01",
                x=5,
                y=5,
                name="테스트 왕국",
                base_dir=root,
            )
            self.assertTrue(result["ok"])
            charter = get_kingdom_charter(state)
            self.assertIsNotNone(charter)
            assert charter is not None
            self.assertEqual(charter["name"], "테스트 왕국")
            self.assertGreater(charter["barrier"]["max_hp"], 10_000)
            self.assertTrue(charter["barrier"]["physical_destroy_blocked"])

    def test_barrier_blocks_physical_destroy_until_broken(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            complete_kingdom_founding(
                state, map_id="m", x=1, y=1, name="K", base_dir=root
            )
            siege = apply_siege_damage(state, 5000, base_dir=root, siege_type="physical")
            self.assertTrue(siege.get("physical_destroy_blocked", False))
            charter = get_kingdom_charter(state)
            assert charter is not None
            self.assertFalse(charter.get("physically_destroyed", True))

    def test_upgrade_walls_and_recruit_wall_archer(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            _ready_for_kingdom(state, root)
            complete_kingdom_founding(
                state, map_id="m", x=1, y=1, name="K", base_dir=root
            )
            ps = get_player_settlement(state)
            ps["stockpile"] = {"wood": 500, "stone": 2000, "iron": 500, "crystal": 100}
            from utils.currency import grant

            grant(state, gold=500, silver=500, base_dir=root)
            w = upgrade_fortification(state, "walls", base_dir=root)
            self.assertTrue(w["ok"], w)
            ps["stockpile"]["food_store"] = 500
            charter = get_kingdom_charter(state)
            assert charter is not None
            charter["interior"]["food_store"] = 500
            r = recruit_military(state, "wall_archer", 2, base_dir=root)
            self.assertTrue(r["ok"], r)

    def test_tick_produces_food_and_trains(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            complete_kingdom_founding(
                state, map_id="m", x=1, y=1, name="K", base_dir=root
            )
            charter = get_kingdom_charter(state)
            assert charter is not None
            charter["interior"]["farmland_plots"] = 2
            charter["interior"]["food_store"] = 200
            from utils.currency import grant

            grant(state, silver=500, base_dir=root)
            charter["military"]["in_training"] = [{"unit": "scout", "beats_left": 1}]
            lines = tick_kingdom(state, base_dir=root)
            self.assertTrue(any("농경" in ln for ln in lines))
            self.assertEqual(charter["military"]["scout"], 1)

    def test_kingdom_status_includes_defense(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            complete_kingdom_founding(
                state, map_id="m", x=1, y=1, name="K", base_dir=root
            )
            st = kingdom_status(state, base_dir=root)
            self.assertTrue(st["is_kingdom"])
            self.assertIsNotNone(st["defense_summary"])
            self.assertTrue(st["defense_summary"]["physical_destroy_blocked"])

    def test_government_doctrines_catalog(self) -> None:
        with isolated_game_root() as root:
            docs = list_government_doctrines(base_dir=root)
            ids = {d["id"] for d in docs}
            self.assertIn("martial_ascendancy", ids)
            self.assertIn("plutocracy", ids)
            self.assertIn("scholarship", ids)

    def test_founding_with_martial_doctrine(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            result = complete_kingdom_founding(
                state,
                map_id="m",
                x=1,
                y=1,
                name="강철 왕국",
                doctrine_id="martial_ascendancy",
                custom_decree="약자는 훈련장에, 강자는 성벽에!",
                base_dir=root,
            )
            self.assertTrue(result["ok"])
            charter = get_kingdom_charter(state)
            assert charter is not None
            self.assertEqual(charter["monarchy"]["doctrine_id"], "martial_ascendancy")
            self.assertIn("강자", result["monarchy"]["decree_text"])

    def test_change_doctrine_costs_gold(self) -> None:
        with isolated_game_root() as root:
            state = self._ecology_state(root)
            complete_kingdom_founding(
                state, map_id="m", x=1, y=1, name="K", base_dir=root
            )
            from utils.currency import grant, party_gold, wallet_to_copper, get_wallet

            grant(state, gold=50_000, base_dir=root)
            before = wallet_to_copper(get_wallet(state, base_dir=root), base_dir=root)
            r = set_kingdom_doctrine(
                state, "plutocracy", base_dir=root, custom_decree="부자가 법이다."
            )
            self.assertTrue(r["ok"], r)
            after = wallet_to_copper(get_wallet(state, base_dir=root), base_dir=root)
            self.assertLess(after, before)
            charter = get_kingdom_charter(state)
            assert charter is not None
            self.assertEqual(charter["monarchy"]["doctrine_id"], "plutocracy")


if __name__ == "__main__":
    unittest.main()
