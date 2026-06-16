#!/usr/bin/env python3
"""협동 오픈월드 API — 다인 창조 + 노이즈 감쇄."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path
from typing import Any

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from cpow_engine.collab import CollaborativeWorld
from cpow_engine.models import CreativeObject
from cpow_engine.physics import create_heat_object, create_material_object
from cpow_engine.xr import XRCreationIntent, intent_to_creative_object


class CollabWorldStore:
    def __init__(self) -> None:
        self._worlds: dict[str, CollaborativeWorld] = {}

    def get_or_create(self, world_id: str) -> CollaborativeWorld:
        if world_id not in self._worlds:
            self._worlds[world_id] = CollaborativeWorld(world_id)
        return self._worlds[world_id]

    def create_world(self) -> str:
        wid = f"world_{uuid.uuid4().hex[:12]}"
        self._worlds[wid] = CollaborativeWorld(wid)
        return wid


_store = CollabWorldStore()


def handle_collab_join(payload: dict[str, Any]) -> dict[str, Any]:
    world_id = str(payload.get("world_id", ""))
    if not world_id:
        world_id = _store.create_world()
    world = _store.get_or_create(world_id)
    creator_id = str(payload.get("creator_id", "anonymous"))
    return {
        "ok": True,
        "world_id": world_id,
        "creator_id": creator_id,
        "world": world.to_public_dict(),
    }


def handle_collab_create(payload: dict[str, Any]) -> dict[str, Any]:
    world_id = str(payload["world_id"])
    creator_id = str(payload.get("creator_id", "anonymous"))
    world = _store.get_or_create(world_id)

    creativity = float(payload.get("creativity_score", 1.0))

    if "intent" in payload:
        intent = XRCreationIntent.from_dict(payload["intent"])
        obj = intent_to_creative_object(intent)
    elif "object" in payload:
        obj = CreativeObject.from_dict(payload["object"])
    elif payload.get("type") == "heat":
        obj = create_heat_object(
            creator_id,
            str(payload.get("label", "협동 열원")),
            float(payload.get("heat_intensity", 80.0)),
        )
    else:
        obj = create_material_object(
            creator_id,
            str(payload.get("label", "협동 재료")),
            str(payload.get("material", "iron")),
        )

    result = world.submit_creation(creator_id, obj, creativity_score=creativity)
    delta, score = world.advance_tick()
    out: dict[str, Any] = {
        "ok": result.ok,
        "world_id": world_id,
        "reason": result.reason,
        "tick": result.tick,
        "world_version": result.world_version,
        "noise_level": world.world_noise_level(),
    }
    if result.verdict:
        out["magnitude"] = result.verdict.magnitude
        out["applied_damping"] = result.verdict.applied_damping
    if result.ok and result.object_id:
        out["object_id"] = result.object_id
        out["object"] = world.state.objects[result.object_id].to_dict()
    if score:
        out["energy"] = score.energy
        out["creativity_score"] = score.creativity_score
    out["interactions"] = [i.to_dict() for i in delta.interactions] if delta else []
    return out


def handle_collab_state(world_id: str) -> dict[str, Any]:
    world = _store.get_or_create(world_id)
    return {
        "ok": True,
        "world": world.to_public_dict(),
        "state": world.state.to_dict(),
    }
