"""object_factory — areas/collab 기본 타입 분기."""

import unittest

from cpow_engine.object_factory import build_object_from_payload


class TestObjectFactory(unittest.TestCase):
    def test_area_default_is_heat(self) -> None:
        obj, kind = build_object_from_payload({"label": "불"}, "alice")
        self.assertEqual(kind, "heat")
        self.assertIsNotNone(obj.get_property("heat_intensity"))

    def test_collab_default_is_material(self) -> None:
        obj, kind = build_object_from_payload(
            {"label": "광석"},
            "bob",
            default_type="material",
            default_material_label="협동 재료",
        )
        self.assertEqual(kind, "material")
        self.assertIsNotNone(obj.get_property("material_type"))

    def test_empty_object_dict_ignored(self) -> None:
        obj, kind = build_object_from_payload({"object": {}, "label": "불"}, "u")
        self.assertEqual(kind, "heat")
        self.assertIsNotNone(obj.get_property("heat_intensity"))


if __name__ == "__main__":
    unittest.main()
