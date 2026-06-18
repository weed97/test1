"""확장 물리 역할 — 전기·유체·복사·구조."""

from __future__ import annotations

from cpow_engine.models import CreativeObject
from cpow_engine.physics import AttributeRole


class ChargeSource(AttributeRole):
    role_name = "charge_source"

    def can_apply(self, obj: CreativeObject) -> bool:
        return obj.get_property("electric_charge") is not None

    def extract(self, obj: CreativeObject) -> dict[str, float]:
        prop = obj.get_property("electric_charge")
        assert prop is not None
        return {"charge": prop.value, "polarity": 1.0 if prop.value >= 0 else -1.0}


class FluidBody(AttributeRole):
    role_name = "fluid_body"

    def can_apply(self, obj: CreativeObject) -> bool:
        return obj.get_property("fluid_pressure") is not None

    def extract(self, obj: CreativeObject) -> dict[str, float]:
        pressure = obj.get_property("fluid_pressure")
        viscosity = obj.get_property("viscosity")
        return {
            "pressure": pressure.value if pressure else 0.0,
            "viscosity": viscosity.value if viscosity else 1.0,
        }


class RadiantSource(AttributeRole):
    role_name = "radiant_source"

    def can_apply(self, obj: CreativeObject) -> bool:
        return obj.get_property("radiation_intensity") is not None

    def extract(self, obj: CreativeObject) -> dict[str, float]:
        prop = obj.get_property("radiation_intensity")
        assert prop is not None
        return {"intensity": prop.value}


class StructuralBody(AttributeRole):
    role_name = "structural_body"

    def can_apply(self, obj: CreativeObject) -> bool:
        return obj.get_property("mass") is not None

    def extract(self, obj: CreativeObject) -> dict[str, float]:
        mass = obj.get_property("mass")
        stress = obj.get_property("structural_stress")
        return {
            "mass": mass.value if mass else 1.0,
            "stress": stress.value if stress else 0.0,
        }
