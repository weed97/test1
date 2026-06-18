#!/usr/bin/env python3
"""CPoW XR API — Godot XR 클라이언트 ↔ cpow_engine 브릿지."""

from __future__ import annotations

import uuid
from typing import Any

from cpow_engine.engine import SimulationEngine
from cpow_engine.xr import XRCreationIntent, intent_to_creative_object


class CPoWXRStore:
    """세션별 CPoW 시뮬레이션 엔진 (인메모리)."""

    def __init__(self) -> None:
        self._engines: dict[str, SimulationEngine] = {}

    def get_or_create(self, session_id: str) -> SimulationEngine:
        if session_id not in self._engines:
            self._engines[session_id] = SimulationEngine()
        return self._engines[session_id]

    def create_session(self) -> str:
        sid = uuid.uuid4().hex[:16]
        self._engines[sid] = SimulationEngine()
        return sid


_store = CPoWXRStore()


def handle_xr_creation(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload.get("session_id", ""))
    if not session_id:
        session_id = _store.create_session()

    intent = XRCreationIntent.from_dict(payload.get("intent", payload))
    engine = _store.get_or_create(session_id)
    obj = intent_to_creative_object(intent)
    engine.create_object(obj)
    delta, score = engine.tick()

    energy = score.energy if score else 0.0
    return {
        "ok": True,
        "session_id": session_id,
        "object": obj.to_dict(),
        "energy": energy,
        "energy_minted": energy,
        "tick": engine.state.tick,
        "energy_pool": engine.state.energy_pool,
        "interactions": [i.to_dict() for i in delta.interactions],
        "creativity_score": score.creativity_score if score else 0.0,
    }


def handle_xr_connect(payload: dict[str, Any]) -> dict[str, Any]:
    session_id = str(payload["session_id"])
    source_id = str(payload["source_id"])
    target_id = str(payload["target_id"])

    engine = _store.get_or_create(session_id)
    if source_id not in engine.state.objects or target_id not in engine.state.objects:
        return {"ok": False, "error": "object not found"}

    engine.connect_objects(source_id, target_id)
    delta, score = engine.tick()

    return {
        "ok": True,
        "session_id": session_id,
        "source_id": source_id,
        "target_id": target_id,
        "energy": score.energy if score else 0.0,
        "energy_pool": engine.state.energy_pool,
        "interactions": [i.to_dict() for i in delta.interactions],
    }


def handle_xr_world(session_id: str) -> dict[str, Any]:
    engine = _store.get_or_create(session_id)
    return {
        "ok": True,
        "session_id": session_id,
        "state": engine.state.to_dict(),
    }
