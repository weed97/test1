"""XR intent bridge tests."""

import unittest

from cpow_engine.engine import SimulationEngine
from cpow_engine.xr import (
    XRCreationIntent,
    XRDeviceInfo,
    XRSpatialPose,
    connection_distance,
    intent_to_creative_object,
)


class TestXRIntents(unittest.TestCase):
    def test_pinch_spawn_heat(self) -> None:
        intent = XRCreationIntent(
            creator_id="xr_user",
            gesture="heat_pinch",
            pose=XRSpatialPose(1.0, 2.0, 0.5, scale=1.2),
            property_hint="heat_intensity",
            intensity=0.8,
            label="손 열원",
        )
        obj = intent_to_creative_object(intent)
        prop = obj.get_property("heat_intensity")
        assert prop is not None
        self.assertGreater(prop.value, 0)

    def test_material_sculpt(self) -> None:
        intent = XRCreationIntent(
            creator_id="xr_user",
            gesture="material_sculpt",
            pose=XRSpatialPose(0, 0, 0, scale=2.0),
            label="iron",
        )
        obj = intent_to_creative_object(intent)
        self.assertTrue(any(p.name == "thermal_conductivity" for p in obj.properties))

    def test_spatial_pose_in_properties(self) -> None:
        intent = XRCreationIntent(
            creator_id="u1",
            gesture="pinch_spawn",
            pose=XRSpatialPose(3.0, 4.0, 5.0),
            property_hint="xr_energy",
        )
        obj = intent_to_creative_object(intent)
        self.assertTrue(any(p.name == "spatial_x" for p in obj.properties))

    def test_connection_distance(self) -> None:
        intent = XRCreationIntent(
            creator_id="u1",
            gesture="draw_connection",
            pose=XRSpatialPose(0, 0, 0),
            target_pose=XRSpatialPose(3, 4, 0),
        )
        dist = connection_distance(intent)
        assert dist is not None
        self.assertAlmostEqual(dist, 5.0)

    def test_intent_roundtrip(self) -> None:
        intent = XRCreationIntent(
            creator_id="u1",
            gesture="pinch_spawn",
            pose=XRSpatialPose(1, 2, 3),
            device=XRDeviceInfo("quest3", hand_tracking=True),
        )
        restored = XRCreationIntent.from_dict(intent.to_dict())
        self.assertEqual(restored.creator_id, "u1")
        self.assertEqual(restored.device.device_type, "quest3")  # type: ignore[union-attr]

    def test_pinch_strength_scales_heat(self) -> None:
        weak = XRCreationIntent(
            creator_id="u1",
            gesture="heat_pinch",
            pose=XRSpatialPose(0, 0, 0),
            property_hint="heat_intensity",
            intensity=1.0,
            pinch_strength=0.3,
        )
        strong = XRCreationIntent(
            creator_id="u1",
            gesture="heat_pinch",
            pose=XRSpatialPose(0, 0, 0),
            property_hint="heat_intensity",
            intensity=1.0,
            pinch_strength=1.0,
        )
        w = intent_to_creative_object(weak).get_property("heat_intensity")
        s = intent_to_creative_object(strong).get_property("heat_intensity")
        assert w is not None and s is not None
        self.assertGreater(s.value, w.value)

    def test_xr_intent_through_engine(self) -> None:
        engine = SimulationEngine()
        intent = XRCreationIntent(
            creator_id="xr_user",
            gesture="heat_pinch",
            pose=XRSpatialPose(0, 1, 0),
            property_hint="heat_intensity",
            intensity=1.0,
        )
        obj = intent_to_creative_object(intent)
        engine.create_object(obj)
        delta, score = engine.tick()
        self.assertGreater(engine.state.energy_pool, 0)
        self.assertIsNotNone(score)


if __name__ == "__main__":
    unittest.main()
