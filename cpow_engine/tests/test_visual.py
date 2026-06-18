"""ObjectVisual metadata tests."""

import unittest

from cpow_engine.models import CreativeObject, ObjectVisual, PropertyDef
from cpow_engine.visual import extract_visual, visual_from_properties, with_visual


class TestObjectVisual(unittest.TestCase):
    def test_round_trip_dict(self) -> None:
        visual = ObjectVisual(
            glb_url="https://cdn.example/weapons/katana.glb",
            slot="weapon",
            attach_bone="RightHand",
            offset={"position": [0.0, 0.1, 0.0]},
        )
        obj = CreativeObject(creator_id="u1", label="katana", visual=visual)
        data = obj.to_dict()
        restored = CreativeObject.from_dict(data)
        self.assertIsNotNone(restored.visual)
        assert restored.visual is not None
        self.assertEqual(restored.visual.glb_url, visual.glb_url)
        self.assertEqual(restored.visual.slot, "weapon")
        self.assertEqual(restored.visual.attach_bone, "RightHand")

    def test_omit_visual_when_empty(self) -> None:
        obj = CreativeObject(creator_id="u1", label="heat")
        self.assertNotIn("visual", obj.to_dict())

    def test_invalid_slot_defaults_to_world_prop(self) -> None:
        visual = ObjectVisual.from_dict({"glb_url": "x.glb", "slot": "invalid"})
        assert visual is not None
        self.assertEqual(visual.slot, "world_prop")

    def test_legacy_property_inference(self) -> None:
        obj = CreativeObject(
            creator_id="u1",
            label="boots",
            properties=[
                PropertyDef("visual_glb_url", 1.0, "https://cdn.example/boots.glb"),
                PropertyDef("visual_slot", 1.0, "movement"),
            ],
        )
        inferred = visual_from_properties(obj)
        assert inferred is not None
        self.assertEqual(inferred.glb_url, "https://cdn.example/boots.glb")
        self.assertEqual(inferred.slot, "movement")

    def test_extract_prefers_explicit_visual(self) -> None:
        obj = CreativeObject(
            creator_id="u1",
            label="sword",
            properties=[
                PropertyDef("visual_glb_url", 1.0, "legacy.glb"),
            ],
            visual=ObjectVisual(glb_url="explicit.glb", slot="weapon"),
        )
        extracted = extract_visual(obj)
        assert extracted is not None
        self.assertEqual(extracted.glb_url, "explicit.glb")

    def test_with_visual_helper(self) -> None:
        obj = CreativeObject(creator_id="u1", label="avatar")
        with_visual(
            obj,
            "user://avatars/player.vrm",
            slot="avatar",
        )
        self.assertEqual(obj.visual.slot, "avatar")


if __name__ == "__main__":
    unittest.main()
