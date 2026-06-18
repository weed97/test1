"""오픈월드 API — 바이옴·채굴·건축."""

from __future__ import annotations

from typing import Any

from cpow_engine.world.service import get_world_service


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


def handle_world_mine(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload.get("area_id", ""))
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    return get_world_service().mine(area_id, payload)


def handle_world_build_validate(payload: dict[str, Any]) -> dict[str, Any]:
    return get_world_service().validate_build(payload)


def handle_world_boss_loot(payload: dict[str, Any]) -> dict[str, Any]:
    area_id = str(payload.get("area_id", ""))
    if not area_id:
        return {"ok": False, "reason": "missing_area_id"}
    return get_world_service().boss_loot(area_id, payload)
