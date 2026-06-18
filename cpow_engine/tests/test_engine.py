"""CPoW engine tests."""

import time
import unittest

from cpow_engine.cpow import CPoWEngine
from cpow_engine.engine import SimulationEngine
from cpow_engine.models import ActionRecord, CreativeObject, PropertyDef
from cpow_engine.physics import (
    DefinitionPhysicsEngine,
    create_heat_object,
    create_material_object,
)
from cpow_engine.shared_state import ConflictStrategy, SharedStateSync, StatePatch


class TestPhysicsEngine(unittest.TestCase):
    def test_heat_emission_without_target(self) -> None:
        engine = DefinitionPhysicsEngine()
        heat = create_heat_object("u1", "열원", 50.0)
        results = engine.resolve_interactions({heat.id: heat})
        self.assertTrue(any(r.effect_type == "energy_emission" for r in results))

    def test_heat_transfer_with_connection(self) -> None:
        engine = DefinitionPhysicsEngine()
        heat = create_heat_object("u1", "열원", 100.0)
        metal = create_material_object("u1", "철", "iron", thermal_conductivity=0.8)
        heat.connections.append(metal.id)
        results = engine.resolve_interactions({heat.id: heat, metal.id: metal})
        transfers = [r for r in results if r.effect_type == "heat_transfer"]
        self.assertEqual(len(transfers), 1)
        self.assertGreater(transfers[0].energy_delta, 0)

    def test_no_hardcoded_fire_class(self) -> None:
        obj = CreativeObject(
            creator_id="u1",
            label="custom",
            properties=[PropertyDef("heat_intensity", 30.0)],
        )
        roles = DefinitionPhysicsEngine().detect_roles(obj)
        self.assertIn("heat_source", roles)


class TestCPoWEngine(unittest.TestCase):
    def test_unique_creation_scores_higher(self) -> None:
        cpow = CPoWEngine()
        state = SimulationEngine().state
        obj = create_heat_object("u1", "unique", 10.0)
        state.objects[obj.id] = obj

        action = ActionRecord("u1", "create_object", {"object_id": obj.id})
        from cpow_engine.models import WorldDelta

        score1 = cpow.score_action(action, WorldDelta(tick=1), state)
        score2 = cpow.score_action(action, WorldDelta(tick=2), state)
        self.assertGreater(score1.creativity_score, score2.creativity_score)

    def test_repetition_penalty(self) -> None:
        cpow = CPoWEngine()
        state = SimulationEngine().state
        from cpow_engine.models import WorldDelta

        for i in range(10):
            action = ActionRecord("bot", "farm", {"index": i})
            cpow.score_action(action, WorldDelta(tick=i), state)

        action = ActionRecord("bot", "farm", {"index": 10})
        score = cpow.score_action(action, WorldDelta(tick=10), state)
        self.assertLess(score.repetition_penalty, 1.0)

    def test_bot_detection_uniform_intervals(self) -> None:
        cpow = CPoWEngine()
        state = SimulationEngine().state
        from cpow_engine.models import WorldDelta

        base_time = time.time()
        for i in range(20):
            action = ActionRecord(
                "bot",
                "click",
                {"x": 1, "y": 2},
                timestamp=base_time + i * 1.0,
            )
            cpow.score_action(action, WorldDelta(tick=i), state)

        action = ActionRecord(
            "bot", "click", {"x": 1, "y": 2}, timestamp=base_time + 20.0
        )
        self.assertTrue(cpow.is_likely_bot(action))


class TestSharedState(unittest.TestCase):
    def test_merge_conflicting_properties(self) -> None:
        sync = SharedStateSync()
        from cpow_engine.models import SimulationState

        base = SimulationState(version=1)
        heat = create_heat_object("a", "열원", 100.0)
        base.objects[heat.id] = heat

        modified_a = create_heat_object("a", "열원", 200.0)
        modified_a.id = heat.id
        modified_b = create_heat_object("b", "열원", 50.0)
        modified_b.id = heat.id

        patch_a = StatePatch("a", 1, {heat.id: modified_a})
        patch_b = StatePatch("b", 1, {heat.id: modified_b})

        result = sync.apply_patches(base, [patch_a, patch_b])
        merged = result.state.objects[heat.id]
        prop = merged.get_property("heat_intensity")
        assert prop is not None
        self.assertAlmostEqual(prop.value, 125.0)

    def test_no_conflict_for_new_objects(self) -> None:
        sync = SharedStateSync()
        from cpow_engine.models import SimulationState

        base = SimulationState(version=0)
        new_obj = create_heat_object("a", "new", 30.0)
        patch = StatePatch("a", 0, {new_obj.id: new_obj})
        result = sync.apply_patches(base, [patch])
        self.assertIn(new_obj.id, result.state.objects)


class TestSimulationEngine(unittest.TestCase):
    def test_full_mvp_flow(self) -> None:
        engine = SimulationEngine()
        heat = create_heat_object("u1", "열원", 100.0)
        metal = create_material_object("u1", "철", "iron")
        engine.create_object(heat)
        engine.create_object(metal)
        engine.connect_objects(heat.id, metal.id)

        delta, score = engine.tick()
        self.assertGreater(engine.state.energy_pool, 0)
        self.assertTrue(len(delta.interactions) > 0)
        self.assertIsNotNone(score)

    def test_entropy_increases_with_diversity(self) -> None:
        engine = SimulationEngine()
        for i in range(3):
            obj = create_heat_object("u1", f"obj_{i}", float(10 + i * 20))
            engine.create_object(obj)
        engine.tick()
        self.assertGreater(engine.state.entropy, 0.5)


if __name__ == "__main__":
    unittest.main()
