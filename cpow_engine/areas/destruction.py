"""파괴력 기반 파괴 — 내구도·패널티·균열."""

from __future__ import annotations

from dataclasses import dataclass

from cpow_engine.areas.durability import (
    get_creation_investment,
    get_durability,
    is_confirmed,
    is_core_facility,
)
from cpow_engine.areas.powers import PowerLedger, UserPowers
from cpow_engine.areas.rift import RiftState
from cpow_engine.models import CreativeObject


@dataclass
class DestroyAttemptResult:
    ok: bool
    reason: str = ""
    durability_required: float = 0.0
    destruction_spent: float = 0.0
    penalty_applied: float = 0.0
    rift: dict | None = None
    monsters_attacking: bool = False


@dataclass
class DefendResult:
    ok: bool
    reason: str = ""
    threat_reduced: float = 0.0
    destruction_spent: float = 0.0


def can_destroy_object(
    powers: UserPowers,
    obj: CreativeObject,
) -> tuple[bool, str, float]:
    if not is_confirmed(obj):
        return False, "object_not_confirmed", 0.0

    durability = get_durability(obj)
    if powers.destruction_gauge < durability:
        return False, "insufficient_destruction_power", durability

    return True, "ok", durability


def attempt_powered_destroy(
    powers: UserPowers,
    obj: CreativeObject,
    rift: RiftState,
) -> DestroyAttemptResult:
    allowed, reason, durability = can_destroy_object(powers, obj)
    if not allowed:
        return DestroyAttemptResult(
            False,
            reason=reason,
            durability_required=durability,
        )

    if not powers.spend_destruction(durability):
        return DestroyAttemptResult(
            False,
            reason="insufficient_destruction_power",
            durability_required=durability,
        )

    investment = get_creation_investment(obj)
    core_bonus = 1.8 if is_core_facility(obj) else 1.0
    penalty = (durability * 0.3 + investment * 0.6) * core_bonus
    powers.apply_destruction_penalty(penalty)

    rift_info = rift.on_destruction(
        powers.user_id, obj.id, durability,
    )

    return DestroyAttemptResult(
        True,
        reason="destroyed",
        durability_required=durability,
        destruction_spent=durability,
        penalty_applied=penalty,
        rift=rift_info,
        monsters_attacking=bool(rift_info.get("monsters_attacking")),
    )


def attempt_defend_rift(
    powers: UserPowers,
    rift: RiftState,
    *,
    power_spend: float,
) -> DefendResult:
    if power_spend <= 0:
        return DefendResult(False, reason="invalid_power_spend")
    if powers.destruction_gauge < power_spend:
        return DefendResult(False, reason="insufficient_destruction_power")
    if rift.monster_threat <= 0 and rift.level <= 0:
        return DefendResult(False, reason="no_rift_threat")

    if not powers.spend_destruction(power_spend):
        return DefendResult(False, reason="insufficient_destruction_power")

    reduced = rift.defend(powers.user_id, power_spend)
    return DefendResult(
        True,
        reason="defended",
        threat_reduced=reduced,
        destruction_spent=power_spend,
    )
