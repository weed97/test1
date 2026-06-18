"""Phase 2 adapter tests."""

import unittest

from cpow_engine.adapters import FantasyTurnAdapter, SungjwaEventAdapter
from cpow_engine.cpow import CPoWEngine
from cpow_engine.engine import SimulationEngine
from cpow_engine.models import WorldDelta


class TestFantasyAdapter(unittest.TestCase):
    def test_explore_produces_heat_object(self) -> None:
        adapter = FantasyTurnAdapter()
        result = adapter.from_turn(
            "hero_1",
            "explore",
            {"world": {"tension": 10}, "session_id": "s1"},
        )
        self.assertEqual(result.source, "fantasy_simulator")
        self.assertEqual(len(result.objects), 1)
        self.assertEqual(len(result.actions), 1)
        prop = result.objects[0].get_property("heat_intensity")
        self.assertIsNotNone(prop)
        assert prop is not None
        self.assertGreater(prop.value, 0)

    def test_craft_produces_material(self) -> None:
        adapter = FantasyTurnAdapter()
        result = adapter.from_turn("hero_1", "craft", {"material": "steel"})
        mat = result.objects[0].get_property("material_type")
        self.assertIsNotNone(mat)
        assert mat is not None
        self.assertEqual(mat.unit, "steel")

    def test_scored_through_engine(self) -> None:
        adapter = FantasyTurnAdapter()
        engine = SimulationEngine()
        result = adapter.from_turn("hero_1", "fight", {})
        for obj in result.objects:
            engine.create_object(obj)
        action = result.primary_action()
        assert action is not None
        delta, score = engine.tick()
        self.assertIsNotNone(score)
        assert score is not None
        self.assertGreater(score.energy, 0)


class TestSungjwaAdapter(unittest.TestCase):
    def test_combat_event(self) -> None:
        adapter = SungjwaEventAdapter()
        result = adapter.from_event(
            "kim_dokja",
            {
                "turn": 3,
                "kind": "combat",
                "title": "게이트 전투",
                "description": "F급 게이트",
                "effects": {"exp": 50, "hp": -10},
            },
        )
        self.assertEqual(result.source, "sungjwa_hunter_sim")
        heat = result.objects[0].get_property("heat_intensity")
        self.assertIsNotNone(heat)
        assert heat is not None
        self.assertGreater(heat.value, 40)

    def test_favor_shift_material(self) -> None:
        adapter = SungjwaEventAdapter()
        result = adapter.from_event(
            "hunter",
            {
                "turn": 1,
                "kind": "blessing",
                "title": "성좌의 가호",
                "effects": {"favor": 12},
            },
        )
        self.assertEqual(result.actions[0].action_type, "constellation_shift")
        mat = result.objects[0].get_property("material_type")
        assert mat is not None
        self.assertEqual(mat.unit, "constellation_favor")


class TestPhase2Scoring(unittest.TestCase):
    def test_complexity_boosts_connected_object(self) -> None:
        cpow = CPoWEngine()
        engine = SimulationEngine()
        from cpow_engine.physics import create_heat_object, create_material_object

        heat = create_heat_object("u1", "a", 80)
        metal = create_material_object("u1", "b", "iron")
        engine.create_object(heat)
        engine.create_object(metal)
        engine.connect_objects(heat.id, metal.id)
        delta, score = engine.tick()
        self.assertIsNotNone(score)
        assert score is not None
        self.assertGreater(score.complexity_score, 0)

    def test_config_loads(self) -> None:
        from cpow_engine.cpow.scoring_config import load_scoring_weights

        w = load_scoring_weights()
        self.assertGreater(w.entropy_diversity, 0)


if __name__ == "__main__":
    unittest.main()
