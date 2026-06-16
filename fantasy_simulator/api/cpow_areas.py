#!/usr/bin/env python3
"""창조 에리어 API — 창조모드·모험모드·창조모험."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cpow_engine.areas import AreaRegistry, ContributorRole, SimulationMode
from cpow_engine.models import CreativeObject
from cpow_engine.physics import create_heat_object, create_material_object
from cpow_engine.xr import XRCreationIntent, intent_to_creative_object


_registry = AreaRegistry()


def _build_object(payload: dict[str, Any], creator_id: str) -> tuple[CreativeObject, str]:
    if "intent" in payload:
        intent = XRCreationIntent.from_dict(payload["intent"])
        obj = intent_to_creative_object(intent)
        return obj, str(payload.get("type", "heat"))
    if "object" in payload:
        return CreativeObject.from_dict(payload["object"]), str(
            payload.get("type", "heat")
        )
    if payload.get("type") == "material":
        return (
            create_material_object(
                creator_id,
                str(payload.get("label", "재료")),
                str(payload.get("material", "iron")),
            ),
            "material",
        )
    return (
        create_heat_object(
            creator_id,
            str(payload.get("label", "열원")),
            float(payload.get("heat_intensity", 80.0)),
        ),
        "heat",
    )


def handle_area_found(payload: dict[str, Any]) -> dict[str, Any]:
    founder_id = str(payload.get("founder_id", "anonymous"))
    label = str(payload.get("label", "이름 없는 에리어"))
    mode = SimulationMode.from_str(str(payload.get("mode", "creation_adventure")))
    template = payload.get("template")
    area = _registry.found(
        founder_id,
        label,
        mode=mode,
        template=str(template) if template else None,
    )
    return {"ok": True, "area": area.to_public_dict()}


def handle_area_join(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload["area_id"])
    creator_id = str(payload.get("creator_id", "anonymous"))
    role_raw = payload.get("role")
    role = ContributorRole.from_str(str(role_raw)) if role_raw else None
    area = _registry.join(area_id, creator_id, role=role)
    return {
        "ok": True,
        "area_id": area_id,
        "creator_id": creator_id,
        "role": area.role_of(creator_id).value,
        "area": area.to_public_dict(),
    }


def handle_area_create(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    creator_id = str(payload.get("creator_id", "anonymous"))
    creativity = float(payload.get("creativity_score", 1.0))
    obj, creation_type = _build_object(payload, creator_id)
    result = area.submit_creation(
        creator_id, obj,
        creation_type=creation_type,
        creativity_score=creativity,
    )
    pulse = area.maybe_advance_pulse()
    out: dict[str, Any] = {
        "ok": result.ok,
        "area_id": area.area_id,
        "mode": area.mode.value,
        "role": area.role_of(creator_id).value,
        "reason": result.reason,
        "queued": result.queued,
        "seconds_until_pulse": result.seconds_until_pulse,
        "pending_count": result.pending_count,
    }
    if result.ok and result.object_id and not result.queued:
        out["object_id"] = result.object_id
        out["object"] = area.world.state.objects[result.object_id].to_dict()
    if pulse.advanced:
        out["pulse_committed"] = True
        out["economy"] = area.economy.to_dict()
    out["area"] = area.to_public_dict()
    return out


def handle_area_adventure(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    action_type = str(payload.get("action", "explore"))
    result = area.submit_adventure(
        actor_id,
        action_type,
        target_object_id=str(payload.get("target_object_id", "")),
        label=str(payload.get("label", "")),
    )
    pulse = area.maybe_advance_pulse()
    return {
        "ok": result.ok,
        "area_id": area.area_id,
        "mode": area.mode.value,
        "action": result.action_type,
        "reason": result.reason,
        "energy_delta": result.energy_delta,
        "pulse_committed": pulse.advanced,
        "area": area.to_public_dict(),
    }


def handle_area_state(area_id: str) -> dict[str, Any]:
    area = _registry.get_or_raise(area_id)
    pulse = area.maybe_advance_pulse()
    return {
        "ok": True,
        "pulse_committed": pulse.advanced,
        "area": area.to_public_dict(),
        "state": area.world.state.to_dict(),
    }


def handle_area_list() -> dict[str, Any]:
    areas = _registry.list_areas()
    return {
        "ok": True,
        "count": len(areas),
        "areas": [a.to_public_dict() for a in areas],
    }


def handle_area_mutate(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    object_id = str(payload["object_id"])
    operation = str(payload.get("operation", "modify"))
    result = area.submit_mutation(
        actor_id,
        object_id,
        operation,
        property_name=str(payload.get("property_name", "heat_intensity")),
        value=float(payload["value"]) if "value" in payload else None,
        factor=float(payload.get("factor", 1.0)),
        delta=float(payload.get("delta", 0.0)),
        text_value=str(payload.get("text_value", payload.get("label", ""))),
        creativity_score=float(payload.get("creativity_score", 1.0)),
    )
    pulse = area.maybe_advance_pulse()
    out: dict[str, Any] = {
        "ok": result.ok,
        "area_id": area.area_id,
        "role": area.role_of(actor_id).value,
        "operation": result.operation,
        "object_id": result.object_id,
        "reason": result.reason,
        "queued": result.queued,
        "previous_value": result.previous_value,
        "new_value": result.new_value,
        "energy_delta": result.energy_delta,
        "pulse_committed": pulse.advanced,
    }
    if result.ok and not result.queued and result.object_id in area.world.state.objects:
        out["object"] = area.world.state.objects[result.object_id].to_dict()
    out["area"] = area.to_public_dict()
    return out
