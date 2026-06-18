"""확장 물리 — 전기·유체·복사·구조·환경장·상변화."""

import unittest

from cpow_engine.engine import SimulationEngine
from cpow_engine.models import PropertyDef
from cpow_engine.physics.balance_config import PhysicsBalanceConfig
from cpow_engine.physics.crossover import CrossoverPhysics
from cpow_engine.physics.extended_physics import ExtendedPhysicsEngine
from cpow_engine.physics.factories import (
    create_charge_object,
    create_fluid_object,
    create_radiant_object,
    create_structural_object,
)
from cpow_engine.physics.fields import FieldPhysics
from cpow_engine.physics.phase import PhaseChangePhysics
from cpow_engine.physics.properties import (
    charge_of,
    fluid_pressure_of,
    phase_of,
    structural_stress_of,
)


class TestExtendedPhysics(unittest.TestCase):
    def test_electrostatic_between_connected_charges(self) -> None:
        a = create_charge_object("u1", "양전하", 80.0)
        b = create_charge_object("u2", "음전하", -60.0)
        objects = {a.id: a, b.id: b}
        a.connections.append(b.id)

        engine = ExtendedPhysicsEngine()
        results = engine.resolve(objects)
        types = {r.effect_type for r in results}
        self.assertIn("electrostatic", types)

    def test_fluid_pressure_equalization(self) -> None:
        high = create_fluid_object("u1", "고압", 200.0, viscosity=0.5)
        low = create_fluid_object("u2", "저압", 50.0, viscosity=0.5)
        objects = {high.id: high, low.id: low}
        high.connections.append(low.id)

        results = ExtendedPhysicsEngine().resolve(objects)
        self.assertTrue(any(r.effect_type == "fluid_flow" for r in results))

    def test_radiation_to_neighbor(self) -> None:
        src = create_radiant_object("u1", "복사", 120.0)
        tgt = create_structural_object("u2", "수신", 10.0)
        objects = {src.id: src, tgt.id: tgt}
        src.connections.append(tgt.id)

        results = ExtendedPhysicsEngine().resolve(objects)
        self.assertTrue(any(r.effect_type == "radiation" for r in results))

    def test_structural_load_on_support(self) -> None:
        beam = create_structural_object("u1", "보", 250.0)
        support = create_structural_object("u2", "기둥", 500.0)
        objects = {beam.id: beam, support.id: support}
        beam.connections.append(support.id)

        results = ExtendedPhysicsEngine().resolve(objects)
        self.assertTrue(any(r.effect_type == "structural_load" for r in results))


class TestFieldPhysics(unittest.TestCase):
    def test_gravity_increases_stress(self) -> None:
        beam = create_structural_object("u1", "보", 80.0)
        objects = {beam.id: beam}
        before = structural_stress_of(beam)

        field = FieldPhysics()
        interactions = field.resolve(objects)
        field.apply_feedback(objects, interactions)

        self.assertTrue(any(i.effect_type == "gravity" for i in interactions))
        self.assertGreater(structural_stress_of(beam), before)

    def test_ambient_pressure_on_fluid(self) -> None:
        tank = create_fluid_object("u1", "탱크", 90.0)
        objects = {tank.id: tank}
        before = fluid_pressure_of(tank)

        field = FieldPhysics()
        interactions = field.resolve(objects, energy_pool=500.0)
        field.apply_feedback(objects, interactions)

        self.assertTrue(any(i.effect_type == "ambient_pressure" for i in interactions))
        self.assertNotEqual(fluid_pressure_of(tank), before)


class TestPhaseChange(unittest.TestCase):
    def test_melt_when_temperature_exceeds_melting_point(self) -> None:
        metal = create_structural_object(
            "u1",
            "납",
            5.0,
            melting_point=40.0,
        )
        metal.properties.append(
            PropertyDef(name="heat_intensity", value=60.0, unit="joules_per_tick")
        )
        objects = {metal.id: metal}
        self.assertEqual(phase_of(metal), "solid")

        events = PhaseChangePhysics().apply(objects, [])
        self.assertTrue(any(e.effect_type == "phase_melt" for e in events))
        self.assertEqual(phase_of(metal), "liquid")


class TestCrossoverExtended(unittest.TestCase):
    def test_charge_hub_crossover(self) -> None:
        hub = create_structural_object("u1", "허브", 1.0)
        a = create_charge_object("u1", "A", 50.0)
        b = create_charge_object("u2", "B", -30.0)
        objects = {hub.id: hub, a.id: a, b.id: b}
        a.connections.append(hub.id)
        b.connections.append(hub.id)

        results = CrossoverPhysics().resolve(objects, energy_pool=0.0)
        self.assertIn("charge_crossover", {r.effect_type for r in results})


class TestSimulationIntegration(unittest.TestCase):
    def test_tick_includes_extended_and_field_interactions(self) -> None:
        engine = SimulationEngine()
        a = create_charge_object("u1", "전하A", 40.0)
        b = create_charge_object("u2", "전하B", -35.0)
        beam = create_structural_object("u1", "보", 120.0)
        tank = create_fluid_object("u1", "유체", 150.0)
        for obj in (a, b, beam, tank):
            engine.create_object(obj)
        engine.connect_objects(a.id, b.id)
        engine.connect_objects(beam.id, tank.id)

        delta, _ = engine.tick()
        effect_types = {i.effect_type for i in delta.interactions}
        extended_or_field = effect_types & {
            "electrostatic",
            "fluid_flow",
            "structural_load",
            "gravity",
            "ambient_pressure",
        }
        self.assertGreater(len(extended_or_field), 0)
        self.assertGreater(int(delta.state_changes.get("extended_count", 0)), 0)
        self.assertGreater(int(delta.state_changes.get("field_count", 0)), 0)

    def test_extended_physics_can_be_disabled(self) -> None:
        cfg = PhysicsBalanceConfig(extended_physics_enabled=False)
        engine = ExtendedPhysicsEngine(config=cfg)
        a = create_charge_object("u1", "A", 90.0)
        b = create_charge_object("u2", "B", -90.0)
        objects = {a.id: a, b.id: b}
        a.connections.append(b.id)
        self.assertEqual(engine.resolve(objects), [])


if __name__ == "__main__":
    unittest.main()
