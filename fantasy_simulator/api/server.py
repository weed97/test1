#!/usr/bin/env python3
"""Eldoria simulation API — Godot / Steam clients call this; rules stay in Python.

Run:
  cd fantasy_simulator
  pip install -r requirements-api.txt
  uvicorn api.server:app --host 127.0.0.1 --port 8765
"""

from __future__ import annotations

from typing import Any, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from api.session_store import SessionStore, package_root, turn_payload
from utils.field_agents import agents_manifest, ensure_ecology_seeds, ecology_enabled
from utils.settlement_build import (
    get_player_settlement,
    hire_workers,
    settlement_status,
    start_build,
    try_start_kingdom,
)
from utils.civilization_coupling import (
    civilization_world_status,
    init_player_civilization,
)
from utils.world_conflicts import conflicts_status, init_world_conflicts
from utils.progression import (
    equip_item,
    init_heroes_from_party,
    progression_status,
    unlock_skill,
)
from utils.spatial import maps_manifest
from utils.temporal import TemporalMode

API_VERSION = 1
APP_NAME = "Eldoria Simulation API"

app = FastAPI(title=APP_NAME, version=str(API_VERSION))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_store = SessionStore()

Mode = Literal["rule", "llm", "hybrid"]
Temporal = Literal["classic", "nex", "precision"]


class NewSessionRequest(BaseModel):
    seed: Optional[int] = None
    mode: Mode = "rule"
    temporal_mode: Temporal = "classic"
    game_mode: str = Field("story", pattern="^(story|ecology|hybrid)$")
    player_race: str = Field(
        "human",
        pattern="^(human|dwarf|elf|dark_elf|beastkin)$",
    )


class NewSessionResponse(BaseModel):
    api_version: int = API_VERSION
    session_id: str
    temporal_mode: str
    mode: str


class PositionBody(BaseModel):
    map_id: str
    x: int
    y: int
    facing: str = "south"
    allow_map_transition: bool = True


class PositionRequest(BaseModel):
    session_id: str
    position: PositionBody


class BuildRequest(BaseModel):
    session_id: str
    building_id: str
    map_id: str
    x: int
    y: int
    mode: str = Field("self", pattern="^(self|hire)$")


class HireRequest(BaseModel):
    session_id: str
    count: int = Field(1, ge=1, le=12)


class KingdomRequest(BaseModel):
    session_id: str
    map_id: str
    x: int
    y: int


class ProgressionUnlockRequest(BaseModel):
    session_id: str
    character_id: str
    skill_id: str


class ProgressionEquipRequest(BaseModel):
    session_id: str
    character_id: str
    item_id: str


class TurnRequest(BaseModel):
    session_id: str
    action: str = Field(..., min_length=1, max_length=512)
    temporal_mode: Optional[Temporal] = None
    time_scale: float = Field(1.0, ge=0.0, le=10.0)
    mode: Optional[Mode] = None
    enemy_id: Optional[str] = None
    position: Optional[PositionBody] = None


class HealthResponse(BaseModel):
    api_version: int
    status: str
    package_root: str


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        api_version=API_VERSION,
        status="ok",
        package_root=str(package_root()),
    )


@app.post("/v1/session/new", response_model=NewSessionResponse)
def new_session(body: NewSessionRequest) -> NewSessionResponse:
    session_id, session = _store.create(
        seed=body.seed,
        mode=body.mode,
        temporal_mode=body.temporal_mode,
    )
    session.state.setdefault("flags", {})["game_mode"] = body.game_mode
    if body.game_mode in ("ecology", "hybrid"):
        root = package_root()
        init_player_civilization(
            session.state, player_race=body.player_race, base_dir=root
        )
        ensure_ecology_seeds(session.state, base_dir=root)
        init_heroes_from_party(session.state, base_dir=root)
        get_player_settlement(session.state)
        init_world_conflicts(session.state, base_dir=root)
    session.manager.save(session.state)
    return NewSessionResponse(
        session_id=session_id,
        temporal_mode=body.temporal_mode,
        mode=body.mode,
    )


@app.get("/v1/settlement/status")
def settlement_status_route(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        **settlement_status(session.state, base_dir=package_root()),
    }


@app.post("/v1/settlement/build")
def settlement_build(body: BuildRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if not ecology_enabled(session.state):
        raise HTTPException(status_code=400, detail="ecology or hybrid mode required")
    result = start_build(
        session.state,
        body.building_id,
        map_id=body.map_id,
        x=body.x,
        y=body.y,
        mode=body.mode,  # type: ignore[arg-type]
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "build failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/settlement/hire")
def settlement_hire(body: HireRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    result = hire_workers(session.state, body.count, base_dir=package_root())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "hire failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/settlement/kingdom")
def settlement_kingdom(body: KingdomRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    result = try_start_kingdom(
        session.state,
        map_id=body.map_id,
        x=body.x,
        y=body.y,
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "kingdom failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.get("/v1/progression/status")
def progression_status_route(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        **progression_status(session.state, base_dir=package_root()),
    }


@app.post("/v1/progression/unlock_skill")
def progression_unlock(body: ProgressionUnlockRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if not ecology_enabled(session.state):
        raise HTTPException(status_code=400, detail="ecology or hybrid mode required")
    result = unlock_skill(
        session.state,
        body.character_id,
        body.skill_id,
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "unlock failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/progression/equip")
def progression_equip(body: ProgressionEquipRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if not ecology_enabled(session.state):
        raise HTTPException(status_code=400, detail="ecology or hybrid mode required")
    result = equip_item(
        session.state,
        body.character_id,
        body.item_id,
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "equip failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.get("/v1/ecology/wars")
def ecology_wars(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "ecology_enabled": ecology_enabled(session.state),
        **conflicts_status(session.state, base_dir=package_root()),
    }


@app.get("/v1/ecology/civilizations")
def ecology_civilizations(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "ecology_enabled": ecology_enabled(session.state),
        **civilization_world_status(session.state, base_dir=package_root()),
    }


@app.get("/v1/world/agents")
def world_agents(
    session_id: str,
    map_id: str | None = None,
    instance_id: str | None = None,
) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    mid = map_id or session.state.get("world", {}).get("map_id", "ashpoint_01")
    root = package_root()
    agents = agents_manifest(
        session.state, mid, base_dir=root, instance_id=instance_id
    )
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "map_id": mid,
        "ecology_enabled": ecology_enabled(session.state),
        "agents": agents,
        "schema": "ecology_agent",
    }


@app.get("/v1/world/maps")
def world_maps() -> dict[str, Any]:
    return {"api_version": API_VERSION, **maps_manifest(package_root())}


@app.post("/v1/world/position")
def world_position(body: PositionRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    pos = body.position
    meta = session.apply_position(
        map_id=pos.map_id,
        x=pos.x,
        y=pos.y,
        facing=pos.facing,
        allow_map_transition=pos.allow_map_transition,
    )
    if not meta.get("ok"):
        raise HTTPException(status_code=400, detail=meta.get("error", "sync failed"))
    world = session.state.get("world", {})
    return {
        "api_version": API_VERSION,
        "session_id": body.session_id,
        **meta,
        "world": {
            "location": world.get("location"),
            "zone_id": world.get("zone_id"),
            "tension": world.get("tension"),
        },
    }


@app.get("/v1/session/{session_id}/status")
def session_status(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "report": session.status_report(),
        "world": session.state.get("world", {}),
    }


@app.post("/v1/turn")
def run_turn(body: TurnRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")

    temporal: TemporalMode = (
        body.temporal_mode
        if body.temporal_mode is not None
        else session.default_temporal_mode
    )
    if body.mode is not None:
        session.mode = body.mode

    pos_dict = None
    if body.position is not None:
        pos_dict = body.position.model_dump()

    result = session.run_turn(
        action=body.action,
        enemy_id=body.enemy_id,
        temporal_mode=temporal,
        time_scale=body.time_scale,
        position=pos_dict,
    )
    payload = turn_payload(session, result)
    payload["session_id"] = body.session_id
    return payload


@app.delete("/v1/session/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    if not _store.delete(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return {"status": "deleted", "session_id": session_id}
