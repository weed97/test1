"""물리 오브젝트 팩토리 — 확장 속성."""

from __future__ import annotations

from cpow_engine.models import CreativeObject, PropertyDef


def create_charge_object(
    creator_id: str,
    label: str,
    charge: float,
    *,
    unit: str = "coulomb",
) -> CreativeObject:
    return CreativeObject(
        creator_id=creator_id,
        label=label,
        properties=[
            PropertyDef(name="electric_charge", value=charge, unit=unit),
        ],
    )


def create_fluid_object(
    creator_id: str,
    label: str,
    pressure: float,
    *,
    viscosity: float = 1.0,
) -> CreativeObject:
    return CreativeObject(
        creator_id=creator_id,
        label=label,
        properties=[
            PropertyDef(name="fluid_pressure", value=pressure, unit="kpa"),
            PropertyDef(name="viscosity", value=viscosity, unit="pas"),
        ],
    )


def create_radiant_object(
    creator_id: str,
    label: str,
    intensity: float,
) -> CreativeObject:
    return CreativeObject(
        creator_id=creator_id,
        label=label,
        properties=[
            PropertyDef(name="radiation_intensity", value=intensity, unit="sievert_proxy"),
        ],
    )


def create_structural_object(
    creator_id: str,
    label: str,
    mass: float,
    *,
    material: str = "steel",
    melting_point: float = 1500.0,
    conductivity: float = 0.5,
) -> CreativeObject:
    return CreativeObject(
        creator_id=creator_id,
        label=label,
        properties=[
            PropertyDef(name="mass", value=mass, unit="kg"),
            PropertyDef(name="structural_stress", value=0.0, unit="mpa"),
            PropertyDef(name="material_type", value=0.0, unit=material),
            PropertyDef(name="melting_point", value=melting_point, unit="celsius"),
            PropertyDef(name="thermal_conductivity", value=conductivity, unit="w_per_mk"),
            PropertyDef(name="phase", value=1.0, unit="solid"),
        ],
    )
