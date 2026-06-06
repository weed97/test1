"""게이트 몬스터 / 성좌 헌터 로스터 단위 테스트.

    python -m unittest discover -s tests -v
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import units  # noqa: E402
from src.rng import ChaosRNG  # noqa: E402
from src.simulator import Simulator  # noqa: E402
from src.variables import VariableManager  # noqa: E402

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "variables.json")


def fresh_config() -> str:
    with open(CONFIG, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, tmp, ensure_ascii=False, indent=2)
    tmp.close()
    return tmp.name


class TestMonsters(unittest.TestCase):
    def setUp(self):
        self.path = fresh_config()
        self.vars = VariableManager(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_load_monsters(self):
        monsters = units.load_monsters(self.vars)
        self.assertGreaterEqual(len(monsters), 1)
        ids = {m.id for m in monsters}
        self.assertIn("nameless_calamity", ids)

    def test_monsters_have_exception_variables(self):
        monsters = {m.id: m for m in units.load_monsters(self.vars)}
        calamity = monsters["nameless_calamity"]
        self.assertIn("randomness_intensity", calamity.exception_variables)
        self.assertGreater(calamity.exception_variables["randomness_intensity"], 3.0)

    def test_exception_scope_overrides_then_restores(self):
        rng = ChaosRNG(self.vars, seed=1)
        base = rng._u("randomness_intensity")
        with rng.exception_scope({"randomness_intensity": 4.6}):
            self.assertEqual(rng._u("randomness_intensity"), 4.6)
        # 스코프 종료 후 원복
        self.assertEqual(rng._u("randomness_intensity"), base)

    def test_pick_monster_returns_unit(self):
        rng = ChaosRNG(self.vars, seed=2)
        rng.monsters = units.load_monsters(self.vars)
        m = rng.pick_monster(turn=1)
        self.assertIsNotNone(m)
        self.assertIn(m, rng.monsters)

    def test_pick_monster_none_when_empty(self):
        rng = ChaosRNG(self.vars, seed=2)
        rng.monsters = []
        self.assertIsNone(rng.pick_monster(turn=1))


class TestHunterRoster(unittest.TestCase):
    def setUp(self):
        self.path = fresh_config()
        self.vars = VariableManager(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_load_roster(self):
        roster = units.load_hunter_roster(self.vars)
        self.assertIn("kim_dokja", roster)
        self.assertEqual(roster["yoo_jonghyuk"].hunter.name, "유중혁")

    def test_select_specific_hunter(self):
        hunter, const, used = units.select_hunter(self.vars, "jung_heewon")
        self.assertEqual(used, "jung_heewon")
        self.assertEqual(hunter.name, "정희원")
        self.assertEqual(const.name, "정의의 사도")

    def test_select_fallback_to_default(self):
        hunter, const, used = units.select_hunter(self.vars, None)
        self.assertIsNone(used)
        self.assertEqual(hunter.name, "무명")

    def test_select_unknown_falls_back(self):
        hunter, const, used = units.select_hunter(self.vars, "없는헌터")
        self.assertIsNone(used)

    def test_simulator_uses_selected_hunter(self):
        sim = Simulator(self.vars, seed=5, hunter_id="yoo_jonghyuk", output=lambda s: None)
        self.assertEqual(sim.state.hunter.name, "유중혁")
        self.assertGreater(len(sim.rng.monsters), 0)
        state = sim.run(max_turns=6)
        self.assertTrue(state.finished)


class TestCompatibility(unittest.TestCase):
    """기존 동작이 유지되는지(호환성) 확인."""

    def setUp(self):
        self.path = fresh_config()
        self.vars = VariableManager(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_run_without_hunter_id_still_works(self):
        sim = Simulator(self.vars, seed=42, output=lambda s: None)
        state = sim.run(max_turns=8)
        self.assertTrue(state.finished)
        self.assertGreaterEqual(len(state.log), 1)

    def test_state_dict_includes_defeated_monsters(self):
        sim = Simulator(self.vars, seed=3, output=lambda s: None)
        state = sim.run(max_turns=10)
        d = state.to_dict()
        self.assertIn("defeated_monsters", d)
        self.assertIsInstance(d["defeated_monsters"], list)


if __name__ == "__main__":
    unittest.main(verbosity=2)
