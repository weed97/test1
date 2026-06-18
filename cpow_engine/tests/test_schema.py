"""JSON schema validation tests."""

import unittest

from cpow_engine.models import CreativeObject, PropertyDef
from cpow_engine.schema import SchemaValidator, validate_creative_object


class TestSchemaValidator(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = SchemaValidator()

    def test_valid_creative_object(self) -> None:
        obj = CreativeObject(
            creator_id="u1",
            label="heat",
            properties=[PropertyDef("heat_intensity", 50.0)],
        )
        result = self.validator.validate_creative_object(obj.to_dict())
        self.assertTrue(result.ok, result.errors)

    def test_missing_required_field(self) -> None:
        result = self.validator.validate_creative_object({"label": "x"})
        self.assertFalse(result.ok)
        paths = {e.path for e in result.errors}
        self.assertTrue(any("id" in p or "creator_id" in p for p in paths))

    def test_invalid_visual_slot(self) -> None:
        obj = CreativeObject(
            creator_id="u1",
            label="bad",
            properties=[],
        )
        data = obj.to_dict()
        data["visual"] = {"glb_url": "x.glb", "slot": "not_a_slot"}
        result = self.validator.validate_creative_object(data)
        self.assertFalse(result.ok)

    def test_action_record_minimal(self) -> None:
        result = self.validator.validate_action_record(
            {"actor_id": "u1", "action_type": "create_object"}
        )
        self.assertTrue(result.ok)

    def test_world_delta_tick(self) -> None:
        result = self.validator.validate_world_delta({"tick": 0, "interactions": []})
        self.assertTrue(result.ok)

    def test_validate_helper(self) -> None:
        obj = CreativeObject(creator_id="a", label="b", properties=[])
        self.assertTrue(validate_creative_object(obj.to_dict()).ok)


if __name__ == "__main__":
    unittest.main()
