"""API payload → CreativeObject — areas·collab 공통."""

from __future__ import annotations

from typing import Any

from cpow_engine.models import CreativeObject
from cpow_engine.physics import create_heat_object, create_material_object
from cpow_engine.physics.factories import (
    create_charge_object,
    create_fluid_object,
    create_radiant_object,
    create_structural_object,
)
from cpow_engine.xr import XRCreationIntent, intent_to_creative_object


def build_object_from_payload(
    payload: dict[str, Any],
    creator_id: str,
    *,
    default_type: str = "heat",
    default_heat_label: str = "열원",
    default_material_label: str = "재료",
) -> tuple[CreativeObject, str]:
    """창조 요청 페이로드를 CreativeObject와 creation_type으로 변환."""
    if payload.get("intent"):
        intent = XRCreationIntent.from_dict(payload["intent"])
        obj = intent_to_creative_object(intent)
        return obj, str(payload.get("type", default_type))
    if payload.get("object"):
        return CreativeObject.from_dict(payload["object"]), str(
            payload.get("type", default_type)
        )

    obj_type = str(payload.get("type", default_type)).lower()
    if obj_type == "material":
        return (
            create_material_object(
                creator_id,
                str(payload.get("label", default_material_label)),
                str(payload.get("material", "iron")),
            ),
            "material",
        )
    if obj_type == "charge":
        return (
            create_charge_object(
                creator_id,
                str(payload.get("label", "전하")),
                float(payload.get("electric_charge", 10.0)),
            ),
            "charge",
        )
    if obj_type == "fluid":
        return (
            create_fluid_object(
                creator_id,
                str(payload.get("label", "유체")),
                float(payload.get("fluid_pressure", 120.0)),
                viscosity=float(payload.get("viscosity", 1.0)),
            ),
            "fluid",
        )
    if obj_type == "radiant":
        return (
            create_radiant_object(
                creator_id,
                str(payload.get("label", "복사원")),
                float(payload.get("radiation_intensity", 50.0)),
            ),
            "radiant",
        )
    if obj_type == "structural":
        return (
            create_structural_object(
                creator_id,
                str(payload.get("label", "구조체")),
                float(payload.get("mass", 100.0)),
                material=str(payload.get("material", "steel")),
                melting_point=float(payload.get("melting_point", 1500.0)),
                conductivity=float(payload.get("thermal_conductivity", 0.5)),
            ),
            "structural",
        )
    return (
        create_heat_object(
            creator_id,
            str(payload.get("label", default_heat_label)),
            float(payload.get("heat_intensity", 80.0)),
        ),
        "heat",
    )
