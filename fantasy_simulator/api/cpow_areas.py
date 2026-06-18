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
from cpow_engine.areas.siege import area_fortification_strength
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
        "consensus_pending": result.consensus_pending,
        "proposal_id": result.proposal_id,
        "approvals_needed": result.approvals_needed,
        "approvals_received": result.approvals_received,
        "law_violations": result.law_violations,
        "penalty_redeemed": result.penalty_redeemed,
    }
    if result.ok and result.object_id and not result.queued and not result.consensus_pending:
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
    _registry.tick_sieges()
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
        "durability_required": result.durability_required,
        "destruction_spent": result.destruction_spent,
        "penalty_applied": result.penalty_applied,
        "rift_level": result.rift_level,
        "monsters_attacking": result.monsters_attacking,
        "pulse_committed": pulse.advanced,
    }
    if actor_id in area.power_ledger.members:
        out["powers"] = area.member_powers(actor_id)
    out["area"] = area.to_public_dict()
    return out


def handle_area_vote(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    voter_id = str(payload.get("voter_id", "anonymous"))
    proposal_id = str(payload["proposal_id"])
    approve = bool(payload.get("approve", True))
    vote = area.vote_on_creation(voter_id, proposal_id, approve=approve)
    pulse = area.maybe_advance_pulse()
    return {
        "ok": vote.ok,
        "area_id": area.area_id,
        "proposal_id": proposal_id,
        "status": vote.status,
        "reason": vote.reason,
        "approved": vote.approved,
        "approvals_needed": vote.approvals_needed,
        "approvals_received": vote.approvals_received,
        "pulse_committed": pulse.advanced,
        "area": area.to_public_dict(),
    }


def handle_area_defend(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    spend = float(payload.get("power_spend", 15.0))
    result = area.defend_rift(actor_id, power_spend=spend)
    siege_repulses: list[dict] = []
    if result.ok and spend > 0:
        area_id = area.area_id
        for contest in _registry.siege.contests_for(area_id):
            if contest.defender_area_id != area_id:
                continue
            share = spend * 0.25
            updated = _registry.siege.on_repulse(
                contest.attacker_area_id,
                area_id,
                actor_id,
                power_spent=share,
            )
            fort = area_fortification_strength(area.world.state.objects)
            attacker = _registry.get_or_raise(contest.attacker_area_id)
            siege_repulses.append(
                updated.to_dict(
                    fortification=fort,
                    dominance_ratio=attacker.dominance_vs(area),
                )
            )
    return {
        "ok": result.ok,
        "reason": result.reason,
        "threat_reduced": result.threat_reduced,
        "destruction_spent": result.destruction_spent,
        "rift": area.rift.to_dict(),
        "powers": area.member_powers(actor_id),
        "siege_repulses": siege_repulses,
        "area": area.to_public_dict(),
    }


def handle_area_extract_core(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    return {**area.extract_core(actor_id), "area": area.to_public_dict()}


def handle_area_restore_core(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    label = payload.get("label")
    result = area.restore_core(actor_id, label=str(label) if label else None)
    return {
        "ok": result.ok,
        "reason": result.reason,
        "object_id": result.object_id,
        "area": area.to_public_dict(),
    }


def handle_area_migrate(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    return {**area.migrate_member(actor_id), "area": area.to_public_dict()}


def handle_area_powers(area_id: str, user_id: str) -> dict[str, Any]:
    area = _registry.get_or_raise(area_id)
    powers = area.member_powers(user_id)
    if powers is None:
        return {"ok": False, "reason": "not_a_member"}
    return {
        "ok": True,
        "powers": powers,
        "rift": area.rift.to_dict(),
        "area_extent": round(area.area_extent(), 2),
    }


def handle_area_imbue(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    amount = float(payload.get("amount", 0.0))
    return {
        **area.imbue_object_destruction(
            actor_id, str(payload["object_id"]), amount,
        ),
        "area": area.to_public_dict(),
    }


def handle_area_spawn_npc(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    owner_id = str(payload.get("owner_id", "anonymous"))
    label = str(payload.get("label", "일꾼"))
    return {**area.spawn_npc(owner_id, label), "area": area.to_public_dict()}


def handle_area_npc_allocate(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    owner_id = str(payload.get("owner_id", "anonymous"))
    npc_id = str(payload["npc_id"])
    amount = float(payload.get("amount", 0.0))
    return {
        **area.allocate_npc_creation(owner_id, npc_id, amount),
        "area": area.to_public_dict(),
    }


def handle_area_npc_task(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    owner_id = str(payload.get("owner_id", "anonymous"))
    npc_id = str(payload["npc_id"])
    task = str(payload.get("task", "idle"))
    return {**area.set_npc_task(owner_id, npc_id, task), "area": area.to_public_dict()}


def handle_area_npc_tick(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    results = area.tick_npcs()
    pulse = area.maybe_advance_pulse()
    return {
        "ok": True,
        "results": results,
        "pulse_committed": pulse.advanced,
        "area": area.to_public_dict(),
    }


def handle_area_expand(payload: dict[str, Any]) -> dict[str, Any]:
    area = _registry.get_or_raise(str(payload["area_id"]))
    actor_id = str(payload.get("actor_id", "anonymous"))
    return {**area.expand_area(actor_id), "area": area.to_public_dict()}


def handle_area_dominance(area_id_a: str, area_id_b: str) -> dict[str, Any]:
    return {"ok": True, **_registry.dominance_between(area_id_a, area_id_b)}


def handle_area_diplomacy_set(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        **_registry.set_diplomatic_stance(
            str(payload["area_id"]),
            str(payload["target_area_id"]),
            str(payload.get("stance", "neutral")),
            str(payload.get("actor_id", "anonymous")),
        ),
    }


def handle_area_diplomacy_status(area_id: str, target_area_id: str) -> dict[str, Any]:
    return {
        "ok": True,
        **_registry.diplomatic_status(area_id, target_area_id),
    }


def handle_area_cross_destroy(payload: dict[str, Any]) -> dict[str, Any]:
    result = _registry.cross_area_destroy(
        str(payload["attacker_area_id"]),
        str(payload.get("actor_id", "anonymous")),
        str(payload["target_area_id"]),
        str(payload["object_id"]),
    )
    target = _registry.get_or_raise(str(payload["target_area_id"]))
    result["area"] = target.to_public_dict()
    return result


def handle_area_allied_create(payload: dict[str, Any]) -> dict[str, Any]:
    home_area_id = str(payload["home_area_id"])
    target_area_id = str(payload["target_area_id"])
    creator_id = str(payload.get("creator_id", "anonymous"))
    obj, creation_type = _build_object(payload, creator_id)
    result = _registry.allied_creation(
        home_area_id,
        target_area_id,
        creator_id,
        obj,
        creation_type=creation_type,
        creativity_score=float(payload.get("creativity_score", 1.0)),
    )
    target = _registry.get_or_raise(target_area_id)
    target.maybe_advance_pulse()
    return {
        "ok": result.ok,
        "reason": result.reason,
        "object_id": result.object_id,
        "resolved_stance": _registry.diplomacy.resolved_stance(
            home_area_id, target_area_id,
        ).value,
        "area": target.to_public_dict(),
    }


def handle_governance_draft(payload: dict[str, Any]) -> dict[str, Any]:
    return _registry.draft_system_proposal(
        str(payload.get("author_id", "anonymous")),
        kind=str(payload.get("kind", "custom")),
        title=str(payload.get("title", "시스템 발의")),
        spec=payload.get("spec"),
        area_id=str(payload.get("area_id", "")),
    )


def handle_governance_compose(payload: dict[str, Any]) -> dict[str, Any]:
    return _registry.sign_system_composer(
        str(payload["proposal_id"]),
        str(payload.get("user_id", "anonymous")),
    )


def handle_governance_cosponsor(payload: dict[str, Any]) -> dict[str, Any]:
    return _registry.cosponsor_system_proposal(
        str(payload["proposal_id"]),
        str(payload.get("user_id", "anonymous")),
    )


def handle_governance_vote(payload: dict[str, Any]) -> dict[str, Any]:
    return _registry.vote_system_proposal(
        str(payload["proposal_id"]),
        str(payload.get("user_id", "anonymous")),
        approve=bool(payload.get("approve", True)),
    )


def handle_governance_tick() -> dict[str, Any]:
    return _registry.tick_governance()


def handle_governance_state() -> dict[str, Any]:
    return _registry.governance_state()


def handle_area_siege_status(attacker_area_id: str, defender_area_id: str) -> dict[str, Any]:
    return _registry.siege_between(attacker_area_id, defender_area_id)


def handle_area_siege_active(area_id: str) -> dict[str, Any]:
    return _registry.active_sieges(area_id)


def handle_area_siege_repulse(payload: dict[str, Any]) -> dict[str, Any]:
    return _registry.repulse_siege(
        str(payload["defender_area_id"]),
        str(payload["attacker_area_id"]),
        str(payload.get("actor_id", "anonymous")),
        power_spend=float(payload.get("power_spend", 15.0)),
    )


def handle_identity_register(payload: dict[str, Any]) -> dict[str, Any]:
    return _registry.register_member_identity(
        str(payload.get("user_id", "")),
        str(payload.get("person_key", "")),
    )


def handle_identity_status(user_id: str) -> dict[str, Any]:
    return _registry.member_identity_status(user_id)
