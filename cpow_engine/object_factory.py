"""API payload → CreativeObject — areas·collab 공통."""

from __future__ import annotations

from typing import Any

from cpow_engine.models import CreativeObject
from cpow_engine.physics import create_heat_object, create_material_object
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
    if "intent" in payload:
        intent = XRCreationIntent.from_dict(payload["intent"])
        obj = intent_to_creative_object(intent)
        return obj, str(payload.get("type", default_type))
    if "object" in payload:
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
    return (
        create_heat_object(
            creator_id,
            str(payload.get("label", default_heat_label)),
            float(payload.get("heat_intensity", 80.0)),
        ),
        "heat",
    )
