"""오브젝트 물리 속성 — 읽기/쓰기 헬퍼."""

from __future__ import annotations

from cpow_engine.models import CreativeObject, PropertyDef


def get_prop(obj: CreativeObject, name: str) -> float | None:
    prop = obj.get_property(name)
    return prop.value if prop is not None else None


def set_prop(
    obj: CreativeObject,
    name: str,
    value: float,
    *,
    unit: str = "",
) -> None:
    prop = obj.get_property(name)
    if prop is None:
        obj.properties.append(PropertyDef(name=name, value=value, unit=unit))
    else:
        prop.value = value
        if unit:
            prop.unit = unit


def heat_of(obj: CreativeObject) -> float:
    return get_prop(obj, "heat_intensity") or 0.0


def residual_of(obj: CreativeObject) -> float:
    return get_prop(obj, "residual_heat") or 0.0


def charge_of(obj: CreativeObject) -> float:
    return get_prop(obj, "electric_charge") or 0.0


def fluid_pressure_of(obj: CreativeObject) -> float:
    return get_prop(obj, "fluid_pressure") or 0.0


def mass_of(obj: CreativeObject) -> float:
    return get_prop(obj, "mass") or 0.0


def radiation_of(obj: CreativeObject) -> float:
    return get_prop(obj, "radiation_intensity") or 0.0


def structural_stress_of(obj: CreativeObject) -> float:
    return get_prop(obj, "structural_stress") or 0.0


def temperature_of(obj: CreativeObject) -> float:
    """열원 + 잔열 근사 온도."""
    return heat_of(obj) + residual_of(obj) * 0.6


def phase_of(obj: CreativeObject) -> str:
    prop = obj.get_property("phase")
    if prop is None or not prop.unit:
        return "solid"
    return str(prop.unit)


def clamp_delta(delta: float, cap: float) -> float:
    if cap <= 0:
        return delta
    return max(-cap, min(cap, delta))
