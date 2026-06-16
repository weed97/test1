#!/usr/bin/env python3
"""협동 오픈월드 API — 다인 창조 + 노이즈 감쇄 + 빌드 펄스."""

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


def _submission_response(
    world: CollaborativeWorld,
    world_id: str,
    result: Any,
    *,
    pulse: Any | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": result.ok,
        "world_id": world_id,
        "reason": result.reason,
        "tick": result.tick,
        "world_version": result.world_version,
        "noise_level": world.world_noise_level(),
        "queued": result.queued,
        "pulse_number": result.pulse_number,
        "pending_count": result.pending_count,
        "contributors_in_pulse": result.contributors_in_pulse,
        "seconds_until_pulse": result.seconds_until_pulse,
    }
    if result.cooldown_remaining > 0:
        out["cooldown_remaining"] = round(result.cooldown_remaining, 2)
    if result.verdict:
        out["magnitude"] = result.verdict.magnitude
        out["applied_damping"] = result.verdict.applied_damping
    if result.ok and result.object_id and not result.queued:
        out["object_id"] = result.object_id
        if result.object_id in world.state.objects:
            out["object"] = world.state.objects[result.object_id].to_dict()
    elif result.ok and result.queued:
        out["object_id"] = result.object_id
    if pulse and pulse.advanced:
        out["pulse_committed"] = True
        out["pulse_applied_count"] = pulse.applied_count
        if pulse.score:
            out["energy"] = pulse.score.energy
            out["creativity_score"] = pulse.score.creativity_score
        out["interactions"] = (
            [i.to_dict() for i in pulse.delta.interactions] if pulse.delta else []
        )
    out["world"] = world.to_public_dict()
    return out


def handle_collab_join(payload: dict[str, Any]) -> dict[str, Any]:
    world_id = str(payload.get("world_id", ""))
    if not world_id:
        world_id = _store.create_world()
    world = _store.get_or_create(world_id)
    creator_id = str(payload.get("creator_id", "anonymous"))
    pulse = world.maybe_advance_pulse()
    return {
        "ok": True,
        "world_id": world_id,
        "creator_id": creator_id,
        "pulse_committed": pulse.advanced,
        "world": world.to_public_dict(),
    }


def _build_object(payload: dict[str, Any], creator_id: str) -> CreativeObject:
    if "intent" in payload:
        intent = XRCreationIntent.from_dict(payload["intent"])
        return intent_to_creative_object(intent)
    if "object" in payload:
        return CreativeObject.from_dict(payload["object"])
    if payload.get("type") == "heat":
        return create_heat_object(
            creator_id,
            str(payload.get("label", "협동 열원")),
            float(payload.get("heat_intensity", 80.0)),
        )
    return create_material_object(
        creator_id,
        str(payload.get("label", "협동 재료")),
        str(payload.get("material", "iron")),
    )


def handle_collab_create(payload: dict[str, Any]) -> dict[str, Any]:
    world_id = str(payload["world_id"])
    creator_id = str(payload.get("creator_id", "anonymous"))
    world = _store.get_or_create(world_id)

    creativity = float(payload.get("creativity_score", 1.0))
    obj = _build_object(payload, creator_id)
    result = world.submit_creation(creator_id, obj, creativity_score=creativity)
    pulse = world.maybe_advance_pulse()
    return _submission_response(world, world_id, result, pulse=pulse)


def handle_collab_pulse(payload: dict[str, Any]) -> dict[str, Any]:
    world_id = str(payload["world_id"])
    world = _store.get_or_create(world_id)
    force = bool(payload.get("force", False))
    pulse = world.advance_pulse(force=force)
    return {
        "ok": pulse.advanced,
        "world_id": world_id,
        "reason": pulse.reason,
        "pulse_number": pulse.pulse_number,
        "applied_count": pulse.applied_count,
        "seconds_until_next": pulse.seconds_until_next,
        "results": [
            {
                "ok": r.ok,
                "creator_id": r.creator_id,
                "object_id": r.object_id,
                "reason": r.reason,
            }
            for r in pulse.results
        ],
        "world": world.to_public_dict(),
        "state": world.state.to_dict() if pulse.advanced else None,
    }


def handle_collab_state(world_id: str) -> dict[str, Any]:
    world = _store.get_or_create(world_id)
    pulse = world.maybe_advance_pulse()
    return {
        "ok": True,
        "pulse_committed": pulse.advanced,
        "world": world.to_public_dict(),
        "state": world.state.to_dict(),
    }
