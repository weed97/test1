"""Spatial simulation — Godot tile coords ↔ world state ↔ fantasy zones."""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

FRONTIER_ZONES = frozenset({"ashpoint", "forest", "tower"})
_FACING = frozenset({"north", "south", "east", "west"})


@lru_cache(maxsize=4)
def load_world_maps(base_dir: str) -> dict[str, Any]:
    path = Path(base_dir) / "config" / "world_maps.json"
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def ensure_world_position(world: dict[str, Any], *, base_dir: str | Path) -> None:
    """Fill map_id / zone_id / x,y from config spawn if missing."""
    cfg = load_world_maps(str(base_dir))
    maps: dict[str, Any] = cfg.get("maps", {})
    if world.get("map_id") and world.get("zone_id"):
        world["x"] = int(world.get("x", 0))
        world["y"] = int(world.get("y", 0))
        return
    default_id = "ashpoint_01"
    if default_id not in maps:
        return
    m = maps[default_id]
    spawn = m.get("spawn", {})
    world.setdefault("map_id", default_id)
    world.setdefault("zone_id", m.get("zone_id", "ashpoint"))
    world.setdefault("x", int(spawn.get("x", 0)))
    world.setdefault("y", int(spawn.get("y", 0)))
    world.setdefault("facing", spawn.get("facing", "south"))
    world.setdefault("location", m.get("location_label", world.get("location", "")))


def _clamp_tile(x: int, y: int, m: dict[str, Any]) -> tuple[int, int]:
    w = int(m.get("width", 1))
    h = int(m.get("height", 1))
    return max(0, min(w - 1, x)), max(0, min(h - 1, y))


def _point_in_rect(px: int, py: int, rect: dict[str, Any]) -> bool:
    rx, ry = int(rect["x"]), int(rect["y"])
    rw, rh = int(rect["w"]), int(rect["h"])
    return rx <= px < rx + rw and ry <= py < ry + rh


def _zone_from_location_label(location: str) -> str:
    loc = location.lower()
    if any(x in loc for x in ("관측", "tower", "석탑")):
        return "tower"
    if any(x in loc for x in ("숲", "forest")):
        return "forest"
    return "ashpoint"


def resolve_zone_from_world(world: dict[str, Any]) -> str:
    """Zone for event_engine — spatial sync + legacy location overrides for tests."""
    inferred = _zone_from_location_label(world.get("location", ""))
    zid = world.get("zone_id", "")
    if zid in FRONTIER_ZONES and inferred == zid:
        return zid
    if zid in FRONTIER_ZONES and inferred != zid:
        return inferred
    if zid in FRONTIER_ZONES:
        return zid
    return inferred


def pois_at_tile(
    cfg: dict[str, Any], map_id: str, x: int, y: int
) -> list[dict[str, Any]]:
    found: list[dict[str, Any]] = []
    for poi in cfg.get("pois", []):
        if poi.get("map_id") != map_id:
            continue
        dx = x - int(poi.get("x", 0))
        dy = y - int(poi.get("y", 0))
        r = int(poi.get("radius", 1))
        if dx * dx + dy * dy <= r * r:
            found.append(poi)
    return found


def check_map_transition(
    cfg: dict[str, Any], map_id: str, x: int, y: int
) -> dict[str, Any] | None:
    maps = cfg.get("maps", {})
    m = maps.get(map_id)
    if not m:
        return None
    for ex in m.get("exits", []):
        rect = ex.get("rect", {})
        if _point_in_rect(x, y, rect):
            target = ex.get("target_map")
            if not target or target not in maps:
                continue
            spawn = ex.get("target_spawn", maps[target].get("spawn", {}))
            return {
                "exit_id": ex.get("id"),
                "from_map": map_id,
                "to_map": target,
                "x": int(spawn.get("x", 0)),
                "y": int(spawn.get("y", 0)),
                "facing": spawn.get("facing", "south"),
            }
    return None


def sync_position(
    state: dict[str, Any],
    *,
    map_id: str,
    x: int,
    y: int,
    facing: str = "south",
    base_dir: str | Path,
    allow_map_transition: bool = True,
) -> dict[str, Any]:
    """Apply Godot-reported tile position to world state (simulation authority)."""
    cfg = load_world_maps(str(base_dir))
    maps: dict[str, Any] = cfg.get("maps", {})
    world = state.setdefault("world", {})
    ensure_world_position(world, base_dir=base_dir)

    if map_id not in maps:
        return {"ok": False, "error": f"unknown map_id: {map_id}"}

    m = maps[map_id]
    tx, ty = _clamp_tile(int(x), int(y), m)
    fac = facing if facing in _FACING else "south"

    transition: dict[str, Any] | None = None
    if allow_map_transition:
        transition = check_map_transition(cfg, map_id, tx, ty)
    if transition:
        map_id = str(transition["to_map"])
        m = maps[map_id]
        tx, ty = _clamp_tile(
            int(transition["x"]), int(transition["y"]), m
        )
        fac = str(transition.get("facing", fac))

    prev_map = world.get("map_id")
    prev_zone = world.get("zone_id")
    prev_x, prev_y = int(world.get("x", -1)), int(world.get("y", -1))

    world["map_id"] = map_id
    world["zone_id"] = m.get("zone_id", "ashpoint")
    world["x"] = tx
    world["y"] = ty
    world["facing"] = fac
    world["location"] = m.get("location_label", m.get("display_name", map_id))

    pois = pois_at_tile(cfg, map_id, tx, ty)
    poi_ids = [p["id"] for p in pois]

    flags = state.setdefault("flags", {})
    spatial_flags = flags.setdefault("spatial", {})
    spatial_flags["last_map_id"] = map_id
    spatial_flags["last_poi_ids"] = poi_ids
    if transition:
        spatial_flags["last_transition"] = transition.get("exit_id")

    zone_changed = prev_zone != world["zone_id"]
    map_changed = prev_map != map_id
    tile_changed = prev_x != tx or prev_y != ty

    return {
        "ok": True,
        "position": position_snapshot(world),
        "zone_id": world["zone_id"],
        "zone_changed": zone_changed,
        "map_changed": map_changed,
        "tile_changed": tile_changed,
        "transition": transition,
        "pois": [
            {"id": p["id"], "label": p.get("label"), "explore_action": p.get("explore_action")}
            for p in pois
        ],
    }


def position_snapshot(world: dict[str, Any]) -> dict[str, Any]:
    return {
        "map_id": world.get("map_id"),
        "zone_id": world.get("zone_id"),
        "x": int(world.get("x", 0)),
        "y": int(world.get("y", 0)),
        "facing": world.get("facing", "south"),
        "location": world.get("location"),
        "godot_pixels": {
            "x": int(world.get("x", 0)),
            "y": int(world.get("y", 0)),
        },
    }


def godot_pixel_position(world: dict[str, Any], *, tile_pixels: int = 16) -> dict[str, int]:
    """Tile coords → Godot world pixels (top-left of tile)."""
    return {
        "x": int(world.get("x", 0)) * tile_pixels,
        "y": int(world.get("y", 0)) * tile_pixels,
    }


def maps_manifest(base_dir: str | Path) -> dict[str, Any]:
    """Payload for GET /v1/world/maps — Godot loads scenes + bounds."""
    cfg = load_world_maps(str(base_dir))
    out_maps: dict[str, Any] = {}
    for mid, m in cfg.get("maps", {}).items():
        out_maps[mid] = {
            "zone_id": m.get("zone_id"),
            "display_name": m.get("display_name"),
            "width": m.get("width"),
            "height": m.get("height"),
            "godot_scene": m.get("godot_scene"),
            "spawn": m.get("spawn"),
            "exits": m.get("exits"),
            "tile_size": cfg.get("godot_pixel_per_tile", cfg.get("tile_size", 16)),
        }
    return {
        "version": cfg.get("version", 1),
        "tile_size": cfg.get("tile_size", 16),
        "godot_pixel_per_tile": cfg.get("godot_pixel_per_tile", 16),
        "maps": out_maps,
        "pois": cfg.get("pois", []),
    }
