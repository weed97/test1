"""오브젝트에 파괴력 부여 — 유저 게이지 → imbued_destruction."""

from __future__ import annotations

from dataclasses import dataclass

from cpow_engine.areas.extent import max_imbue_amount
from cpow_engine.areas.powers import UserPowers
from cpow_engine.models import CreativeObject, PropertyDef


@dataclass
class ImbueResult:
    ok: bool
    reason: str = ""
    amount_applied: float = 0.0
    imbued_total: float = 0.0
    destruction_spent: float = 0.0
    cap_remaining: float = 0.0


def get_imbued_destruction(obj: CreativeObject) -> float:
    prop = obj.get_property("imbued_destruction")
    if prop is None:
        return 0.0
    return max(0.0, prop.value)


def set_imbued_destruction(obj: CreativeObject, value: float) -> None:
    prop = obj.get_property("imbued_destruction")
    if prop is None:
        obj.properties.append(
            PropertyDef(name="imbued_destruction", value=value, unit="dp")
        )
    else:
        prop.value = value


def effective_destroy_resistance(
    obj: CreativeObject,
    *,
    area_extent: float,
) -> float:
    """내구도 + 부여 파괴력 — 넓은 에리어일수록 저항 보너스."""
    from cpow_engine.areas.durability import get_durability

    durability = get_durability(obj)
    imbued = get_imbued_destruction(obj)
    extent_bonus = min(area_extent * 0.12, 25.0)
    return durability + imbued * 0.85 + extent_bonus


def attempt_imbue_destruction(
    powers: UserPowers,
    obj: CreativeObject,
    amount: float,
    *,
    area_extent: float,
    is_confirmed_obj: bool,
) -> ImbueResult:
    if amount <= 0.0:
        return ImbueResult(False, reason="invalid_amount")
    if not is_confirmed_obj:
        return ImbueResult(False, reason="object_not_confirmed")

    current = get_imbued_destruction(obj)
    cap = max_imbue_amount(
        extent=area_extent,
        destruction_gauge_max=powers.destruction_gauge_max,
        destruction_gauge=powers.destruction_gauge,
        already_imbued=current,
    )
    if cap <= 1e-9:
        return ImbueResult(
            False,
            reason="imbue_cap_reached",
            cap_remaining=0.0,
        )

    spend = min(amount, cap, powers.destruction_gauge)
    if spend <= 1e-9:
        return ImbueResult(False, reason="insufficient_destruction_power")

    if not powers.spend_destruction(spend):
        return ImbueResult(False, reason="insufficient_destruction_power")

    new_total = current + spend
    set_imbued_destruction(obj, new_total)
    return ImbueResult(
        True,
        reason="imbued",
        amount_applied=spend,
        imbued_total=new_total,
        destruction_spent=spend,
        cap_remaining=max(0.0, cap - spend),
    )
