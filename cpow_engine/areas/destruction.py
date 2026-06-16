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
    *,
    area_extent: float = 1.0,
) -> tuple[bool, str, float]:
    if not is_confirmed(obj):
        return False, "object_not_confirmed", 0.0

    from cpow_engine.areas.imbue import effective_destroy_resistance

    required = effective_destroy_resistance(obj, area_extent=area_extent)
    if powers.destruction_gauge < required:
        return False, "insufficient_destruction_power", required

    return True, "ok", required


def attempt_powered_destroy(
    powers: UserPowers,
    obj: CreativeObject,
    rift: RiftState,
    *,
    area_extent: float = 1.0,
) -> DestroyAttemptResult:
    allowed, reason, required = can_destroy_object(
        powers, obj, area_extent=area_extent,
    )
    if not allowed:
        return DestroyAttemptResult(
            False,
            reason=reason,
            durability_required=required,
        )

    if not powers.spend_destruction(required):
        return DestroyAttemptResult(
            False,
            reason="insufficient_destruction_power",
            durability_required=required,
        )

    investment = get_creation_investment(obj)
    core_bonus = 1.8 if is_core_facility(obj) else 1.0
    penalty = (required * 0.3 + investment * 0.6) * core_bonus
    powers.apply_destruction_penalty(penalty)

    rift_info = rift.on_destruction(
        powers.user_id, obj.id, required,
    )

    return DestroyAttemptResult(
        True,
        reason="destroyed",
        durability_required=required,
        destruction_spent=required,
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
