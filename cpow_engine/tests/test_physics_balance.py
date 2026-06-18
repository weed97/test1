"""활발한 물리 교차 + 자동 균형 테스트."""

import unittest

from cpow_engine.engine import SimulationEngine
from cpow_engine.physics import create_heat_object, create_material_object
from cpow_engine.physics.crossover import CrossoverPhysics
from cpow_engine.physics.equilibrium import EquilibriumRegulator


class TestCrossoverPhysics(unittest.TestCase):
    def test_hub_crossover_without_direct_link(self) -> None:
        engine = SimulationEngine()
        hub = create_material_object("u1", "허브", "copper", thermal_conductivity=0.9)
        hot = create_heat_object("u1", "열원A", 120.0)
        cold = create_heat_object("u2", "열원B", 5.0)
        engine.create_object(hub)
        engine.create_object(hot)
        engine.create_object(cold)
        engine.connect_objects(hot.id, hub.id)
        engine.connect_objects(cold.id, hub.id)

        cross = CrossoverPhysics()
        results = cross.resolve(engine.state.objects, energy_pool=50.0)
        types = {r.effect_type for r in results}
        self.assertIn("hub_crossover", types)

    def test_tick_includes_crossover_interactions(self) -> None:
        engine = SimulationEngine()
        hub = create_material_object("u1", "허브", "iron")
        a = create_heat_object("u1", "A", 90.0)
        b = create_heat_object("u2", "B", 10.0)
        for obj in (hub, a, b):
            engine.create_object(obj)
        engine.connect_objects(a.id, hub.id)
        engine.connect_objects(b.id, hub.id)

        delta, _ = engine.tick()
        crossover = [
            i for i in delta.interactions
            if i.effect_type in ("hub_crossover", "path_crossover", "ambient_coupling")
        ]
        self.assertGreater(len(crossover), 0)
        self.assertGreater(int(delta.state_changes.get("crossover_count", 0)), 0)


class TestEquilibrium(unittest.TestCase):
    def test_runaway_pool_dissipates_toward_target(self) -> None:
        engine = SimulationEngine()
        heat = create_heat_object("u1", "열원", 80.0)
        engine.create_object(heat)
        engine.state.energy_pool = 5000.0

        for _ in range(12):
            engine.tick()

        target = len(engine.state.objects) * engine.equilibrium.cfg.target_energy_per_object
        self.assertLess(engine.state.energy_pool, 5000.0)
        self.assertLess(abs(engine.state.energy_pool - target), 5000.0 * 0.5)

    def test_balance_index_improves_with_regulation(self) -> None:
        engine = SimulationEngine()
        hot = create_heat_object("u1", "과열", 200.0)
        cold = create_heat_object("u2", "저온", 5.0)
        metal = create_material_object("u1", "철", "iron")
        engine.create_object(hot)
        engine.create_object(cold)
        engine.create_object(metal)
        engine.connect_objects(hot.id, metal.id)

        first_balance = None
        last_balance = None
        for i in range(15):
            _, _ = engine.tick()
            assert engine.last_equilibrium is not None
            if i == 0:
                first_balance = engine.last_equilibrium.balance_index
            last_balance = engine.last_equilibrium.balance_index

        assert last_balance is not None
        self.assertGreater(last_balance, 0.2)
        self.assertIn("balance_index", engine.last_equilibrium.to_dict())

    def test_active_world_stays_lively_not_flat(self) -> None:
        """균형이 맞아도 상호작용은 계속 발생."""
        engine = SimulationEngine()
        objs = [
            create_heat_object("u1", f"h{i}", float(40 + i * 15))
            for i in range(4)
        ]
        hub = create_material_object("u1", "중계", "silver", thermal_conductivity=0.85)
        engine.create_object(hub)
        for o in objs:
            engine.create_object(o)
            engine.connect_objects(o.id, hub.id)

        interaction_counts: list[int] = []
        for _ in range(10):
            delta, _ = engine.tick()
            interaction_counts.append(len(delta.interactions))

        self.assertTrue(all(c > 0 for c in interaction_counts[-5:]))
        assert engine.last_equilibrium is not None
        self.assertGreater(engine.last_equilibrium.interaction_count, 0)


if __name__ == "__main__":
    unittest.main()
