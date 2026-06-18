"""오픈월드 API — 바이옴·채굴·건축."""

from __future__ import annotations

from typing import Any

from cpow_engine.world.service import get_world_service


def _should_submit_area_object(payload: dict[str, Any]) -> bool:
    if payload.get("submit_to_area") is False:
        return False
    deposit = str(payload.get("deposit_mode", "inventory")).lower()
    return deposit in ("area_object", "both")


def _maybe_submit_mined_resource(payload: dict[str, Any], out: dict[str, Any]) -> dict[str, Any]:
    if not _should_submit_area_object(payload):
        return out
    if not out.get("ok") or not out.get("resource"):
        return out
    from cpow_api.areas import attach_mined_resource_to_area

    creation = attach_mined_resource_to_area(payload, out)
    out["creation"] = creation
    if creation.get("object_id"):
        out["object_id"] = creation["object_id"]
    return out


def handle_world_catalog() -> dict[str, Any]:
    return get_world_service().catalog()


def handle_world_cell(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload.get("area_id", ""))
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    return get_world_service().inspect_cell(
        area_id,
        x=float(payload.get("x", 0.0)),
        z=float(payload.get("z", 0.0)),
        depth_y=int(payload.get("depth_y", 48)),
        cell_size=int(payload.get("cell_size", 64)),
        advance_tick=bool(payload.get("advance_tick", False)),
    )


def handle_world_inventory(area_id: str, actor_id: str) -> dict[str, Any]:
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    return get_world_service().get_inventory(area_id, actor_id)


def handle_world_drops(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload.get("area_id", ""))
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    return get_world_service().drops_in_aoi(
        area_id,
        float(payload.get("x", 0.0)),
        float(payload.get("z", 0.0)),
        float(payload.get("radius_m", 128.0)),
    )


def handle_world_pickup(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload.get("area_id", ""))
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    return get_world_service().pickup_drop(area_id, payload)


def handle_world_mine(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload.get("area_id", ""))
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    out = get_world_service().mine(area_id, payload)
    return _maybe_submit_mined_resource({**payload, "area_id": area_id}, out)


def handle_world_build_validate(payload: dict[str, Any]) -> dict[str, Any]:
    return get_world_service().validate_build(payload)


def handle_world_boss_loot(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload.get("area_id", ""))
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    out = get_world_service().boss_loot(area_id, payload)
    return _maybe_submit_mined_resource({**payload, "area_id": area_id}, out)
