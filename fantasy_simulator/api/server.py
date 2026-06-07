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

from api.session_store import SessionStore, package_root, sim_tick_payload, turn_payload
from utils.field_agents import (
    agents_manifest,
    ensure_ecology_seeds,
    ecology_enabled,
    init_world_sovereign,
)
from utils.kingdom_system import (
    build_interior,
    kingdom_status,
    list_government_doctrines,
    recruit_military,
    set_kingdom_doctrine,
    set_kingdom_laws,
    upgrade_fortification,
)
from utils.kingdom_war import (
    kingdom_wars_status,
    simulate_siege_round,
    start_siege_war,
)
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
    grant_item,
    init_heroes_from_party,
    progression_status,
    unlock_skill,
    use_item,
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
    game_mode: str = Field("hybrid", pattern="^(story|ecology|hybrid)$")
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
    kingdom_name: str = "플레이어 왕국"
    doctrine_id: str = "feudal_balance"
    custom_decree: str = ""


class KingdomDoctrineRequest(BaseModel):
    session_id: str
    doctrine_id: str
    custom_decree: str = ""


class KingdomLawsRequest(BaseModel):
    session_id: str
    laws: dict[str, Any]


class KingdomFortifyRequest(BaseModel):
    session_id: str
    upgrade_type: str = Field(..., pattern="^(walls|tower|barrier_ritual)$")


class KingdomInteriorRequest(BaseModel):
    session_id: str
    build_type: str = Field(..., pattern="^(farmland|city_district|training_ground)$")


class KingdomRecruitRequest(BaseModel):
    session_id: str
    unit_type: str = Field(..., pattern="^(scout|guard|wall_archer|elite)$")
    count: int = Field(1, ge=1, le=20)


class KingdomSiegeStartRequest(BaseModel):
    session_id: str
    attacker_civ: str = "goblin_tribe"
    goal_id: str = "plunder"
    goal_label: str = "약탈"


class KingdomSiegeRoundRequest(BaseModel):
    session_id: str
    war_id: str


class KingdomSiegeCommandRequest(BaseModel):
    session_id: str
    war_id: str
    doctrine: str = Field(
        ...,
        pattern="^(protect_commanders|coordinate_defense)$",
    )
    posture: Optional[str] = Field(
        None,
        pattern="^(forward_command|behind_wall|citadel)$",
    )


class ProgressionUnlockRequest(BaseModel):
    session_id: str
    character_id: str
    skill_id: str


class ProgressionEquipRequest(BaseModel):
    session_id: str
    character_id: str
    item_id: str


class ProgressionUseItemRequest(BaseModel):
    session_id: str
    character_id: str
    item_id: str


class ProgressionGrantRequest(BaseModel):
    session_id: str
    item_id: str
    count: int = Field(1, ge=1, le=99)


class CombatPreviewRequest(BaseModel):
    session_id: Optional[str] = None
    attacker_preset: Optional[str] = None
    defender_preset: Optional[str] = None
    force_sovereign_through: Optional[bool] = None


class ArthurAoeRequest(BaseModel):
    target_presets: Optional[list[str]] = None
    distance_pixels: Optional[list[int]] = None
    ultimate: bool = False


class ArthurSkillRequest(BaseModel):
    skill_id: str
    target_presets: Optional[list[str]] = None
    distance_pixels: Optional[list[int]] = None


class SovereignWishRequest(BaseModel):
    session_id: str
    edict_type: str = Field(..., min_length=1, max_length=64)
    civilization_id: Optional[str] = None
    prosperity_gain: Optional[int] = None
    prosperity_penalty: Optional[int] = None
    power_bonus: Optional[int] = None
    rule_key: Optional[str] = None
    rule_value: Optional[Any] = None
    label: Optional[str] = None


class TurnRequest(BaseModel):
    session_id: str
    action: str = Field(..., min_length=1, max_length=512)
    temporal_mode: Optional[Temporal] = None
    time_scale: float = Field(1.0, ge=0.0, le=10.0)
    mode: Optional[Mode] = None
    enemy_id: Optional[str] = None
    position: Optional[PositionBody] = None


class SimTickRequest(BaseModel):
    session_id: str
    dt_real_ms: int = Field(..., ge=0, le=30_000)


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
    root = package_root()
    init_heroes_from_party(session.state, base_dir=root)
    if body.game_mode in ("ecology", "hybrid"):
        init_world_sovereign(session.state, base_dir=root)
        init_player_civilization(
            session.state, player_race=body.player_race, base_dir=root
        )
        ensure_ecology_seeds(session.state, base_dir=root)
        get_player_settlement(session.state)
        init_world_conflicts(session.state, base_dir=root)
        from utils.sim_clock import enable_sim_clock

        enable_sim_clock(session.state, base_dir=root)
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
        kingdom_name=body.kingdom_name,
        doctrine_id=body.doctrine_id,
        custom_decree=body.custom_decree,
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "kingdom failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.get("/v1/kingdom/status")
def kingdom_status_route(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        **kingdom_status(session.state, base_dir=package_root()),
    }


@app.get("/v1/kingdom/wars")
def kingdom_wars_route(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        **kingdom_wars_status(session.state, base_dir=package_root()),
    }


@app.post("/v1/kingdom/war/start")
def kingdom_war_start_route(body: KingdomSiegeStartRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if not ecology_enabled(session.state):
        raise HTTPException(status_code=400, detail="ecology or hybrid mode required")
    import random

    result = start_siege_war(
        session.state,
        attacker_civ=body.attacker_civ,
        goal_id=body.goal_id,
        goal_label=body.goal_label,
        base_dir=package_root(),
        rng=random.Random(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "siege start failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/kingdom/war/round")
def kingdom_war_round_route(body: KingdomSiegeRoundRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    import random

    result = simulate_siege_round(
        session.state,
        body.war_id,
        base_dir=package_root(),
        rng=random.Random(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "round failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/kingdom/war/command")
def kingdom_war_command_route(body: KingdomSiegeCommandRequest) -> dict[str, Any]:
    from utils.kingdom_war import find_active_siege
    from utils.siege_command import command_live_view, set_defender_siege_command

    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    root = package_root()
    war = find_active_siege(session.state, body.war_id)
    if war is None:
        raise HTTPException(status_code=404, detail="active siege not found")
    result = set_defender_siege_command(
        war,
        doctrine=body.doctrine,
        posture=body.posture,
        base_dir=root,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "command failed"))
    session.manager.save(session.state)
    return {
        "api_version": API_VERSION,
        "session_id": body.session_id,
        **result,
        "command": command_live_view(war, base_dir=root),
    }


@app.get("/v1/kingdom/commanders")
def kingdom_commanders_route(session_id: str) -> dict[str, Any]:
    from utils.siege_command import kingdom_commander_roster_status

    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        **kingdom_commander_roster_status(session.state, base_dir=package_root()),
    }


@app.get("/v1/kingdom/doctrines")
def kingdom_doctrines_catalog_route(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    root = package_root()
    status = kingdom_status(session.state, base_dir=root)
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "doctrines": list_government_doctrines(base_dir=root),
        "current_monarchy": status.get("monarchy"),
        "is_kingdom": status.get("is_kingdom", False),
    }


@app.post("/v1/kingdom/doctrine")
def kingdom_doctrine_route(body: KingdomDoctrineRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    result = set_kingdom_doctrine(
        session.state,
        body.doctrine_id,
        base_dir=package_root(),
        custom_decree=body.custom_decree,
        is_founding=False,
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "doctrine failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/kingdom/laws")
def kingdom_laws_route(body: KingdomLawsRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    result = set_kingdom_laws(session.state, body.laws, base_dir=package_root())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "laws failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/kingdom/fortify")
def kingdom_fortify_route(body: KingdomFortifyRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    result = upgrade_fortification(
        session.state, body.upgrade_type, base_dir=package_root()
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "fortify failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/kingdom/build_interior")
def kingdom_interior_route(body: KingdomInteriorRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    result = build_interior(session.state, body.build_type, base_dir=package_root())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "build failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/kingdom/recruit")
def kingdom_recruit_route(body: KingdomRecruitRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    result = recruit_military(
        session.state,
        body.unit_type,
        body.count,
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "recruit failed"))
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


@app.get("/v1/progression/skill_tree")
def progression_skill_tree_route(session_id: str, character_id: str) -> dict[str, Any]:
    from utils.progression import get_hero_progress
    from utils.skill_tree import build_skill_tree

    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    root = package_root()
    from utils.progression import party_character_ids

    if character_id not in party_character_ids(session.state):
        raise HTTPException(status_code=404, detail=f"unknown character_id: {character_id}")
    try:
        hero = get_hero_progress(
            session.state, character_id, base_dir=root, create_if_missing=False
        )
    except KeyError:
        raise HTTPException(status_code=404, detail=f"unknown character_id: {character_id}")
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "skill_tree": build_skill_tree(hero, base_dir=root, character_id=character_id),
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


@app.get("/v1/catalog/items")
def catalog_items_route(
    session_id: Optional[str] = None,
    category: Optional[str] = None,
    grade: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = 200,
    offset: int = 0,
) -> dict[str, Any]:
    from utils.item_catalog import build_catalog_manifest

    root = package_root()
    if session_id:
        session = _store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
    payload = build_catalog_manifest(
        base_dir=root,
        category=category,
        grade=grade,
        search=q,
        limit=min(limit, 500),
        offset=max(offset, 0),
    )
    inv_summary = None
    if session_id:
        inv = session.state.get("inventory", {})
        inv_summary = {
            "equipment_owned": list(inv.get("equipment_owned", [])),
            "consumables": dict(inv.get("consumables", {})),
        }
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "inventory": inv_summary,
        **payload,
    }


@app.get("/v1/catalog/items/{item_id}")
def catalog_item_detail_route(item_id: str) -> dict[str, Any]:
    from utils.item_catalog import get_item_def

    root = package_root()
    item = get_item_def(item_id, base_dir=root)
    if item is None:
        raise HTTPException(status_code=404, detail=f"unknown item: {item_id}")
    return {"api_version": API_VERSION, "item": item}


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


@app.post("/v1/progression/use_item")
def progression_use_item(body: ProgressionUseItemRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if not ecology_enabled(session.state):
        raise HTTPException(status_code=400, detail="ecology or hybrid mode required")
    result = use_item(
        session.state,
        body.character_id,
        body.item_id,
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "use failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/progression/grant_item")
def progression_grant_item(body: ProgressionGrantRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    if not ecology_enabled(session.state):
        raise HTTPException(status_code=400, detail="ecology or hybrid mode required")
    result = grant_item(
        session.state,
        body.item_id,
        body.count,
        base_dir=package_root(),
    )
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "grant failed"))
    session.manager.save(session.state)
    return {"api_version": API_VERSION, "session_id": body.session_id, **result}


@app.post("/v1/combat/preview_strike")
def combat_preview_strike(body: CombatPreviewRequest) -> dict[str, Any]:
    import random

    from utils.combat_stats import build_combatant_snapshot, strike_damage_milli

    root = package_root()
    atk_id = body.attacker_preset or "apex_knight_lv999"
    def_id = body.defender_preset or "npc_arthur_pendragon"
    rng = random.Random(0)
    attacker = build_combatant_snapshot(base_dir=root, preset_id=atk_id)
    defender = build_combatant_snapshot(base_dir=root, preset_id=def_id)
    result = strike_damage_milli(
        attacker,
        defender,
        base_dir=root,
        rng=rng,
        force_hit=True,
        force_sovereign_through=body.force_sovereign_through,
    )
    return {
        "api_version": API_VERSION,
        "attacker": atk_id,
        "defender": def_id,
        "strike": result,
    }


@app.post("/v1/combat/arthur_aoe")
def combat_arthur_aoe(body: ArthurAoeRequest | None = None) -> dict[str, Any]:
    from utils.combat_stats import build_combatant_snapshot, load_combat_bundle, resolve_excalibur_aoe

    req = body or ArthurAoeRequest()
    root = package_root()
    bundle = load_combat_bundle(root)
    arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
    presets = req.target_presets or [f"world_rank_{r:02d}" for r in range(2, 6)]
    targets: list[dict[str, Any]] = []
    for i, preset_id in enumerate(presets):
        snap = build_combatant_snapshot(base_dir=root, preset_id=preset_id)
        if req.distance_pixels and i < len(req.distance_pixels):
            snap["distance_pixels"] = int(req.distance_pixels[i])
        targets.append(snap)
    result = resolve_excalibur_aoe(arthur, targets, bundle=bundle, ultimate=req.ultimate)
    return {"api_version": API_VERSION, "arthur_aoe": result}


@app.post("/v1/combat/arthur_skill")
def combat_arthur_skill(body: ArthurSkillRequest) -> dict[str, Any]:
    import random

    from utils.combat_stats import build_combatant_snapshot, resolve_arthur_skill

    root = package_root()
    arthur = build_combatant_snapshot(base_dir=root, preset_id="npc_arthur_pendragon")
    presets = body.target_presets or ["world_rank_02"]
    targets: list[dict[str, Any]] = []
    for i, preset_id in enumerate(presets):
        snap = build_combatant_snapshot(base_dir=root, preset_id=preset_id)
        if body.distance_pixels and i < len(body.distance_pixels):
            snap["distance_pixels"] = int(body.distance_pixels[i])
        else:
            snap.setdefault("distance_pixels", 0)
        targets.append(snap)
    result = resolve_arthur_skill(
        body.skill_id, arthur, targets, base_dir=root, rng=random.Random(0)
    )
    return {"api_version": API_VERSION, "arthur_skill": result}


@app.get("/v1/combat/elite_coalition")
def combat_elite_coalition() -> dict[str, Any]:
    from utils.combat_stats import elite_coalition_pierce_dps, load_combat_bundle

    root = package_root()
    bundle = load_combat_bundle(root)
    return {
        "api_version": API_VERSION,
        **elite_coalition_pierce_dps(bundle=bundle),
        "note": "2~11위 10명 전력 집결·산개 없으면 궁극기 전멸 — 마법사만 바이탈 10px 회피",
    }


@app.get("/v1/combat/combatant/{preset_id}")
def combat_combatant(preset_id: str) -> dict[str, Any]:
    from utils.combat_stats import build_combatant_snapshot, combat_power_estimate

    root = package_root()
    snap = build_combatant_snapshot(base_dir=root, preset_id=preset_id)
    return {
        "api_version": API_VERSION,
        "preset_id": preset_id,
        "snapshot": snap,
        "combat_power": combat_power_estimate(snap, base_dir=root),
    }


@app.get("/v1/sovereign/status")
def sovereign_status_route(session_id: Optional[str] = None) -> dict[str, Any]:
    from utils.combat_stats import sovereign_status

    root = package_root()
    state: dict[str, Any] = {"flags": {}}
    if session_id:
        session = _store.get(session_id)
        if session is None:
            raise HTTPException(status_code=404, detail="session not found")
        state = session.state
    return {"api_version": API_VERSION, **sovereign_status(state, base_dir=root)}


@app.post("/v1/sovereign/wish")
def sovereign_wish_route(body: SovereignWishRequest) -> dict[str, Any]:
    from utils.sovereign_wish import resolve_sovereign_wish

    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    payload: dict[str, Any] = {"edict_type": body.edict_type}
    for key in (
        "civilization_id",
        "prosperity_gain",
        "prosperity_penalty",
        "power_bonus",
        "rule_key",
        "rule_value",
        "label",
    ):
        val = getattr(body, key, None)
        if val is not None:
            payload[key] = val
    result = resolve_sovereign_wish(session.state, payload, base_dir=package_root())
    if not result.get("ok"):
        raise HTTPException(status_code=400, detail=result.get("error", "wish failed"))
    session.manager.save(session.state)
    return {
        "api_version": API_VERSION,
        "session_id": body.session_id,
        **result,
    }


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
    from utils.parallel_beat import ecology_beat_presentation

    presentation = ecology_beat_presentation(session.state)
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "map_id": mid,
        "ecology_enabled": ecology_enabled(session.state),
        "agents": agents,
        "schema": "ecology_agent",
        "beat_presentation": presentation,
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
    from utils.sim_clock import sim_clock_status

    root = package_root()
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "report": session.status_report(),
        "world": session.state.get("world", {}),
        "sim_clock": sim_clock_status(session.state, base_dir=root),
    }


@app.get("/v1/sim/status")
def sim_status(session_id: str) -> dict[str, Any]:
    session = _store.get(session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    from utils.sim_clock import sim_clock_status

    root = package_root()
    return {
        "api_version": API_VERSION,
        "session_id": session_id,
        "sim_clock": sim_clock_status(session.state, base_dir=root),
    }


@app.post("/v1/sim/tick")
def sim_tick(body: SimTickRequest) -> dict[str, Any]:
    session = _store.get(body.session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    dt_seconds = body.dt_real_ms / 1000.0
    try:
        result = session.run_sim_tick(dt_real_seconds=dt_seconds)
    except (RuntimeError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"sim tick failed: {exc}") from exc
    if not result.get("ok"):
        raise HTTPException(
            status_code=400,
            detail=result.get("error", "sim tick rejected"),
        )
    payload = sim_tick_payload(session, result)
    payload["session_id"] = body.session_id
    return payload


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

    try:
        result = session.run_turn(
            action=body.action,
            enemy_id=body.enemy_id,
            temporal_mode=temporal,
            time_scale=body.time_scale,
            position=pos_dict,
        )
    except (RuntimeError, KeyError, ValueError) as exc:
        raise HTTPException(status_code=500, detail=f"turn failed: {exc}") from exc
    payload = turn_payload(session, result)
    payload["session_id"] = body.session_id
    return payload


@app.delete("/v1/session/{session_id}")
def delete_session(session_id: str) -> dict[str, str]:
    if not _store.delete(session_id):
        raise HTTPException(status_code=404, detail="session not found")
    return {"status": "deleted", "session_id": session_id}
