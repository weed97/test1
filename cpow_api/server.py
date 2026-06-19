#!/usr/bin/env python3
"""CPoW World API — standalone FastAPI server (no Eldoria RPG routes)."""

from __future__ import annotations

import cpow_api._bootstrap  # noqa: F401

from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from cpow_api.areas import (
    handle_area_adventure,
    handle_area_allied_create,
    handle_area_create,
    handle_area_cross_destroy,
    handle_area_defend,
    handle_area_diplomacy_set,
    handle_area_diplomacy_status,
    handle_area_dominance,
    handle_area_expand,
    handle_area_extract_core,
    handle_area_found,
    handle_area_imbue,
    handle_area_join,
    handle_area_list,
    handle_area_migrate,
    handle_area_mutate,
    handle_area_npc_allocate,
    handle_area_npc_task,
    handle_area_npc_tick,
    handle_area_powers,
    handle_area_restore_core,
    handle_area_siege_active,
    handle_area_siege_repulse,
    handle_area_siege_status,
    handle_area_spawn_npc,
    handle_area_state,
    handle_area_vote,
    handle_governance_compose,
    handle_governance_cosponsor,
    handle_governance_draft,
    handle_governance_state,
    handle_governance_tick,
    handle_governance_vote,
    handle_identity_register,
    handle_identity_status,
)
from cpow_api.auth import handle_auth_login, handle_auth_me, handle_auth_register
from cpow_api.auth_deps import optional_user, require_authenticated_user
from cpow_api.collab import (
    handle_collab_create,
    handle_collab_join,
    handle_collab_pulse,
    handle_collab_state,
)
from cpow_api.world import (
    handle_world_boss_loot,
    handle_world_build_validate,
    handle_world_catalog,
    handle_world_cell,
    handle_world_drops,
    handle_world_inventory,
    handle_world_mine,
    handle_world_pickup,
)
from cpow_api.stream import world_stream_websocket
from cpow_api.route_helpers import authed_call, authed_call_400, authed_call_404
from cpow_api.xr import _store as _xr_store
from cpow_api.xr import handle_xr_connect, handle_xr_creation, handle_xr_world

API_VERSION = 1
APP_NAME = "CPoW World API"

app = FastAPI(title=APP_NAME, version=str(API_VERSION))
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


class HealthResponse(BaseModel):
    api_version: int
    status: str
    package_root: str


@app.get("/v1/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        api_version=API_VERSION,
        status="ok",
        package_root=str(repo_root()),
    )


# --- XR ---


class XRCreationRequest(BaseModel):
    session_id: Optional[str] = None
    intent: dict[str, Any] = Field(default_factory=dict)


class XRConnectRequest(BaseModel):
    session_id: str
    source_id: str
    target_id: str
    pose: dict[str, Any] = Field(default_factory=dict)


@app.post("/v1/xr/session/new")
def xr_session_new() -> dict[str, str]:
    sid = _xr_store.create_session()
    return {"ok": True, "session_id": sid}


@app.post("/v1/xr/creation")
def xr_creation(body: XRCreationRequest) -> dict[str, Any]:
    try:
        return handle_xr_creation(body.model_dump())
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/v1/xr/connect")
def xr_connect(body: XRConnectRequest) -> dict[str, Any]:
    try:
        return handle_xr_connect(body.model_dump())
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/xr/world")
def xr_world(session_id: str) -> dict[str, Any]:
    return handle_xr_world(session_id)


# --- Collaborative open world ---


class CollabJoinRequest(BaseModel):
    world_id: Optional[str] = None
    creator_id: str = "anonymous"


class CollabCreateRequest(BaseModel):
    world_id: str
    creator_id: str = "anonymous"
    creativity_score: float = 1.0
    type: Optional[str] = None
    heat_intensity: Optional[float] = None
    label: Optional[str] = None
    material: Optional[str] = None
    intent: dict[str, Any] = Field(default_factory=dict)
    object: dict[str, Any] = Field(default_factory=dict)


class CollabPulseRequest(BaseModel):
    world_id: str
    force: bool = False


@app.post("/v1/collab/join")
def collab_join(body: CollabJoinRequest) -> dict[str, Any]:
    return handle_collab_join(body.model_dump())


@app.post("/v1/collab/create")
def collab_create(body: CollabCreateRequest) -> dict[str, Any]:
    try:
        return handle_collab_create(body.model_dump(exclude_none=True))
    except (KeyError, ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/v1/collab/world")
def collab_world(world_id: str) -> dict[str, Any]:
    return handle_collab_state(world_id)


@app.post("/v1/collab/pulse")
def collab_pulse(body: CollabPulseRequest) -> dict[str, Any]:
    return handle_collab_pulse(body.model_dump())


# --- Created areas ---


class AreaFoundRequest(BaseModel):
    founder_id: str = "anonymous"
    label: str = "이름 없는 에리어"
    mode: str = "creation_adventure"
    template: Optional[str] = None


class AreaJoinRequest(BaseModel):
    area_id: str
    creator_id: str = "anonymous"
    role: Optional[str] = None


class AreaCreateRequest(BaseModel):
    area_id: str
    creator_id: str = "anonymous"
    creativity_score: float = 1.0
    type: Optional[str] = None
    heat_intensity: Optional[float] = None
    label: Optional[str] = None
    material: Optional[str] = None
    intent: dict[str, Any] = Field(default_factory=dict)
    object: dict[str, Any] = Field(default_factory=dict)


class AreaAdventureRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"
    action: str = "explore"
    target_object_id: Optional[str] = None
    label: Optional[str] = None
    x: Optional[float] = None
    z: Optional[float] = None
    depth_y: Optional[int] = None
    tool_type: Optional[str] = None
    tool_tier: Optional[int] = None
    ore_id: Optional[str] = None
    consumable: Optional[str] = None
    cell_size: Optional[int] = None


class WorldCellRequest(BaseModel):
    area_id: str
    x: float = 0.0
    z: float = 0.0
    depth_y: int = 48
    cell_size: int = 64
    advance_tick: bool = False


class WorldMineRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"
    x: float = 0.0
    z: float = 0.0
    depth_y: int = 48
    cell_size: int = 64
    tool_type: str = "pickaxe"
    tool_tier: int = 1
    ore_id: Optional[str] = None
    consumable: Optional[str] = None
    deposit_mode: str = "inventory"
    spawn_world_drop: bool = True
    submit_to_area: bool = False


class WorldDropsRequest(BaseModel):
    area_id: str
    x: float = 0.0
    z: float = 0.0
    radius_m: float = 128.0


class WorldPickupRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"
    drop_id: str


class WorldBuildValidateRequest(BaseModel):
    area_id: str = ""
    biome_id: str = "plains"
    blueprint_id: str
    placed_modules: dict[str, int] = Field(default_factory=dict)
    placed_materials: dict[str, int] = Field(default_factory=dict)
    civilization_level: int = 0


class AreaMutateRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"
    object_id: str
    operation: str = "modify"
    property_name: str = "heat_intensity"
    value: Optional[float] = None
    factor: float = 1.0
    delta: float = 0.0
    text_value: Optional[str] = None
    label: Optional[str] = None
    creativity_score: float = 1.0


class AuthRegisterRequest(BaseModel):
    user_id: str
    password: str = Field(min_length=8)


class AuthLoginRequest(BaseModel):
    user_id: str
    password: str


@app.post("/v1/auth/register")
def auth_register(body: AuthRegisterRequest) -> dict[str, Any]:
    return handle_auth_register(body.model_dump())


@app.post("/v1/auth/login")
def auth_login(body: AuthLoginRequest) -> dict[str, Any]:
    return handle_auth_login(body.model_dump())


@app.get("/v1/auth/me")
def auth_me(auth_user: str = Depends(require_authenticated_user)) -> dict[str, Any]:
    return handle_auth_me(auth_user)


@app.post("/v1/areas/found")
def area_found(
    body: AreaFoundRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(
        handle_area_found, body, auth_user, "founder_id", exclude_none=True,
    )


@app.post("/v1/areas/join")
def area_join(
    body: AreaJoinRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(
        handle_area_join, body, auth_user, "creator_id", exclude_none=True,
    )


@app.post("/v1/areas/create")
def area_create(
    body: AreaCreateRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_400(
        handle_area_create, body, auth_user, "creator_id", exclude_none=True,
    )


@app.post("/v1/areas/adventure")
def area_adventure(
    body: AreaAdventureRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(
        handle_area_adventure, body, auth_user, "actor_id", exclude_none=True,
    )


@app.post("/v1/areas/mutate")
def area_mutate(
    body: AreaMutateRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_400(
        handle_area_mutate, body, auth_user, "actor_id", exclude_none=True,
    )


class AreaVoteRequest(BaseModel):
    area_id: str
    voter_id: str = "anonymous"
    proposal_id: str
    approve: bool = True


@app.post("/v1/areas/vote")
def area_vote(
    body: AreaVoteRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_area_vote, body, auth_user, "voter_id")


class AreaDefendRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"
    power_spend: float = 15.0


class AreaExtractCoreRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"


class AreaRestoreCoreRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"
    label: Optional[str] = None


class AreaMigrateRequest(BaseModel):
    area_id: str
    actor_id: str = "anonymous"


@app.post("/v1/areas/defend")
def area_defend(
    body: AreaDefendRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_area_defend, body, auth_user, "actor_id")


@app.post("/v1/areas/extract_core")
def area_extract_core(
    body: AreaExtractCoreRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_area_extract_core, body, auth_user, "actor_id")


@app.post("/v1/areas/restore_core")
def area_restore_core(
    body: AreaRestoreCoreRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(
        handle_area_restore_core, body, auth_user, "actor_id", exclude_none=True,
    )


@app.post("/v1/areas/migrate")
def area_migrate(
    body: AreaMigrateRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_area_migrate, body, auth_user, "actor_id")


@app.get("/v1/areas/powers")
def area_powers(area_id: str, user_id: str) -> dict[str, Any]:
    try:
        return handle_area_powers(area_id, user_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/areas/imbue")
def area_imbue(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_imbue, body, auth_user, "actor_id")


@app.post("/v1/areas/spawn_npc")
def area_spawn_npc(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_spawn_npc, body, auth_user, "owner_id")


@app.post("/v1/areas/npc/allocate")
def area_npc_allocate(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_npc_allocate, body, auth_user, "owner_id")


@app.post("/v1/areas/npc/task")
def area_npc_task(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_npc_task, body, auth_user, "owner_id")


@app.post("/v1/areas/npc/tick")
def area_npc_tick(body: dict[str, Any]) -> dict[str, Any]:
    try:
        return handle_area_npc_tick(body)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/areas/expand")
def area_expand(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_expand, body, auth_user, "actor_id")


@app.get("/v1/areas/dominance")
def area_dominance(area_id_a: str, area_id_b: str) -> dict[str, Any]:
    try:
        return handle_area_dominance(area_id_a, area_id_b)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/areas/diplomacy")
def area_diplomacy_set(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_diplomacy_set, body, auth_user, "actor_id")


@app.get("/v1/areas/diplomacy")
def area_diplomacy_status(area_id: str, target_area_id: str) -> dict[str, Any]:
    try:
        return handle_area_diplomacy_status(area_id, target_area_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/areas/cross_destroy")
def area_cross_destroy(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_cross_destroy, body, auth_user, "actor_id")


@app.post("/v1/areas/allied_create")
def area_allied_create(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_allied_create, body, auth_user, "creator_id")


@app.get("/v1/areas/siege")
def area_siege_status(attacker_area_id: str, defender_area_id: str) -> dict[str, Any]:
    try:
        return handle_area_siege_status(attacker_area_id, defender_area_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/v1/areas/siege/active")
def area_siege_active(area_id: str) -> dict[str, Any]:
    try:
        return handle_area_siege_active(area_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/v1/areas/siege/repulse")
def area_siege_repulse(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call_404(handle_area_siege_repulse, body, auth_user, "actor_id")


@app.post("/v1/governance/draft")
def governance_draft(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_governance_draft, body, auth_user, "author_id")


@app.post("/v1/governance/compose")
def governance_compose(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_governance_compose, body, auth_user, "user_id")


@app.post("/v1/governance/cosponsor")
def governance_cosponsor(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_governance_cosponsor, body, auth_user, "user_id")


@app.post("/v1/governance/vote")
def governance_vote(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(handle_governance_vote, body, auth_user, "user_id")


@app.post("/v1/governance/tick")
def governance_tick() -> dict[str, Any]:
    return handle_governance_tick()


@app.get("/v1/governance/state")
def governance_state() -> dict[str, Any]:
    return handle_governance_state()


@app.post("/v1/identity/register")
def identity_register(
    body: dict[str, Any],
    auth_user: str = Depends(require_authenticated_user),
) -> dict[str, Any]:
    return handle_identity_register(body, auth_user_id=auth_user)


@app.get("/v1/identity/status")
def identity_status(user_id: str) -> dict[str, Any]:
    return handle_identity_status(user_id)


@app.get("/v1/world/catalog")
def world_catalog() -> dict[str, Any]:
    return handle_world_catalog()


@app.post("/v1/world/cell")
def world_cell(body: WorldCellRequest) -> dict[str, Any]:
    return handle_world_cell(body.model_dump())


@app.post("/v1/world/mine")
def world_mine(
    body: WorldMineRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(
        handle_world_mine, body, auth_user, "actor_id", exclude_none=True,
    )


@app.get("/v1/world/inventory")
def world_inventory(area_id: str, actor_id: str = "anonymous") -> dict[str, Any]:
    return handle_world_inventory(area_id, actor_id)


@app.post("/v1/world/drops")
def world_drops(body: WorldDropsRequest) -> dict[str, Any]:
    return handle_world_drops(body.model_dump())


@app.post("/v1/world/pickup")
def world_pickup(
    body: WorldPickupRequest,
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(
        handle_world_pickup, body, auth_user, "actor_id", exclude_none=True,
    )


@app.websocket("/v1/world/stream")
async def world_stream(ws: WebSocket) -> None:
    await world_stream_websocket(ws)


@app.post("/v1/world/build/validate")
def world_build_validate(body: WorldBuildValidateRequest) -> dict[str, Any]:
    return handle_world_build_validate(body.model_dump())


@app.post("/v1/world/boss_loot")
def world_boss_loot(
    body: dict[str, Any],
    auth_user: str | None = Depends(optional_user),
) -> dict[str, Any]:
    return authed_call(
        handle_world_boss_loot, body, auth_user, "actor_id", exclude_none=True,
    )


@app.get("/v1/areas/list")
def area_list() -> dict[str, Any]:
    return handle_area_list()


@app.get("/v1/areas/state")
def area_state(area_id: str) -> dict[str, Any]:
    try:
        return handle_area_state(area_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
