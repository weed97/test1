"""오브젝트 내구도 — 창조력 투자가 높을수록 단단함."""

from __future__ import annotations

from cpow_engine.models import CreativeObject, PropertyDef

CORE_DURABILITY_MULTIPLIER = 3.5
FACILITY_DURABILITY_MULTIPLIER = 2.0


def is_confirmed(obj: CreativeObject) -> bool:
    flag = obj.get_property("is_confirmed")
    return flag is not None and flag.value >= 1.0


def is_core_facility(obj: CreativeObject) -> bool:
    core = obj.get_property("area_seed")
    facility = obj.get_property("is_core_facility")
    return core is not None or (facility is not None and facility.value >= 1.0)


def get_durability(obj: CreativeObject) -> float:
    prop = obj.get_property("durability")
    if prop is not None:
        return max(0.0, prop.value)
    inv = obj.get_property("creation_investment")
    if inv is not None:
        return inv.value * 1.2
    heat = obj.get_property("heat_intensity")
    return 8.0 + (heat.value * 0.05 if heat else 0.0)


def get_creation_investment(obj: CreativeObject) -> float:
    prop = obj.get_property("creation_investment")
    if prop is not None:
        return max(0.0, prop.value)
    return get_durability(obj) / 1.2


def compute_durability(
    creation_spent: float,
    *,
    is_core: bool = False,
    is_facility: bool = False,
    heat_intensity: float = 0.0,
) -> float:
    mult = 1.0
    if is_core:
        mult = CORE_DURABILITY_MULTIPLIER
    elif is_facility:
        mult = FACILITY_DURABILITY_MULTIPLIER
    return (creation_spent * mult * 1.15) + heat_intensity * 0.08


def stamp_creation_powers(
    obj: CreativeObject,
    creation_spent: float,
    *,
    is_core: bool = False,
    is_facility: bool = False,
) -> None:
    """합의 확정 후 창조 투자·내구도를 오브젝트에 기록."""
    heat = obj.get_property("heat_intensity")
    heat_val = heat.value if heat else 0.0
    durability = compute_durability(
        creation_spent,
        is_core=is_core,
        is_facility=is_facility,
        heat_intensity=heat_val,
    )

    _set_prop(obj, "creation_investment", creation_spent, "cp")
    _set_prop(obj, "durability", durability, "dp")
    _set_prop(obj, "is_confirmed", 1.0, "flag")
    if is_facility and not is_core:
        _set_prop(obj, "is_core_facility", 1.0, "flag")


def _set_prop(obj: CreativeObject, name: str, value: float, unit: str) -> None:
    existing = obj.get_property(name)
    if existing is not None:
        existing.value = value
        existing.unit = unit
    else:
        obj.properties.append(PropertyDef(name=name, value=value, unit=unit))
