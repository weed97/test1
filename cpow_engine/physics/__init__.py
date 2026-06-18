"""Definition-based Physics Engine — 속성 정의 기반 상호작용."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from cpow_engine.models import CreativeObject, InteractionResult, PropertyDef


class AttributeRole(ABC):
    """속성 역할 인터페이스 — 하드코딩된 Fire가 아닌 유저 정의 속성."""

    role_name: str

    @abstractmethod
    def can_apply(self, obj: CreativeObject) -> bool:
        ...

    @abstractmethod
    def extract(self, obj: CreativeObject) -> dict[str, float]:
        ...


class HeatSource(AttributeRole):
    """열 발생 속성 — 유저가 heat_intensity를 정의하면 작동."""

    role_name = "heat_source"

    def can_apply(self, obj: CreativeObject) -> bool:
        return obj.get_property("heat_intensity") is not None

    def extract(self, obj: CreativeObject) -> dict[str, float]:
        prop = obj.get_property("heat_intensity")
        assert prop is not None
        return {"intensity": prop.value, "unit": prop.unit or "joules_per_tick"}


class Material(AttributeRole):
    """물질 속성 — 열전도율·용융점 등."""

    role_name = "material"

    def can_apply(self, obj: CreativeObject) -> bool:
        return obj.get_property("material_type") is not None

    def extract(self, obj: CreativeObject) -> dict[str, float]:
        conductivity = obj.get_property("thermal_conductivity")
        melting = obj.get_property("melting_point")
        return {
            "conductivity": conductivity.value if conductivity else 0.1,
            "melting_point": melting.value if melting else 1000.0,
            "type": obj.get_property("material_type").value  # type: ignore[union-attr]
            if obj.get_property("material_type")
            else 0.0,
        }


class EnergyTransfer(AttributeRole):
    """에너지 전달 속성 — 전도·복사 등."""

    role_name = "energy_transfer"

    def can_apply(self, obj: CreativeObject) -> bool:
        return (
            obj.get_property("transfer_rate") is not None
            or obj.get_property("heat_intensity") is not None
        )

    def extract(self, obj: CreativeObject) -> dict[str, float]:
        rate = obj.get_property("transfer_rate")
        return {
            "rate": rate.value if rate else 1.0,
            "efficiency": (
                obj.get_property("efficiency").value  # type: ignore[union-attr]
                if obj.get_property("efficiency")
                else 0.85
            ),
        }


@dataclass
class PhysicsRule:
    """유저/시스템이 정의한 상호작용 규칙 (데이터)."""

    name: str
    source_roles: list[str]
    target_roles: list[str]
    formula: str  # e.g. "heat_transfer", "energy_emission"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "source_roles": list(self.source_roles),
            "target_roles": list(self.target_roles),
            "formula": self.formula,
        }


DEFAULT_RULES: list[PhysicsRule] = [
    PhysicsRule(
        name="heat_to_material",
        source_roles=["heat_source"],
        target_roles=["material"],
        formula="heat_transfer",
    ),
    PhysicsRule(
        name="standalone_emission",
        source_roles=["heat_source"],
        target_roles=[],
        formula="energy_emission",
    ),
    PhysicsRule(
        name="energy_conduction",
        source_roles=["energy_transfer"],
        target_roles=["material"],
        formula="conductive_transfer",
    ),
]


class DefinitionPhysicsEngine:
    """속성 조합 → 물리적 결과를 반환하는 엔진."""

    def __init__(self, rules: list[PhysicsRule] | None = None) -> None:
        self._roles: dict[str, AttributeRole] = {
            "heat_source": HeatSource(),
            "material": Material(),
            "energy_transfer": EnergyTransfer(),
        }
        self._rules = rules if rules is not None else list(DEFAULT_RULES)

    def register_role(self, role: AttributeRole) -> None:
        self._roles[role.role_name] = role

    def detect_roles(self, obj: CreativeObject) -> list[str]:
        return [name for name, role in self._roles.items() if role.can_apply(obj)]

    def resolve_interactions(
        self, objects: dict[str, CreativeObject]
    ) -> list[InteractionResult]:
        results: list[InteractionResult] = []
        obj_list = list(objects.values())

        for rule in self._rules:
            sources = [
                o for o in obj_list if self._matches_roles(o, rule.source_roles)
            ]
            targets = (
                [o for o in obj_list if self._matches_roles(o, rule.target_roles)]
                if rule.target_roles
                else []
            )

            for source in sources:
                if not targets:
                    result = self._apply_formula(rule.formula, source, None)
                    if result:
                        results.append(result)
                else:
                    for target in targets:
                        if source.id == target.id:
                            continue
                        if target.id not in source.connections:
                            continue
                        result = self._apply_formula(rule.formula, source, target)
                        if result:
                            results.append(result)

        return results

    def _matches_roles(self, obj: CreativeObject, role_names: list[str]) -> bool:
        detected = set(self.detect_roles(obj))
        return all(r in detected for r in role_names)

    def _apply_formula(
        self,
        formula: str,
        source: CreativeObject,
        target: CreativeObject | None,
    ) -> InteractionResult | None:
        if formula == "energy_emission":
            heat = HeatSource().extract(source)
            magnitude = heat["intensity"]
            return InteractionResult(
                source_id=source.id,
                target_id=None,
                effect_type="energy_emission",
                magnitude=magnitude,
                energy_delta=magnitude * 0.9,
                metadata={"formula": formula},
            )

        if formula == "heat_transfer" and target is not None:
            heat = HeatSource().extract(source)
            mat = Material().extract(target)
            transfer = heat["intensity"] * mat["conductivity"] * 0.01
            absorbed = min(transfer, heat["intensity"])
            return InteractionResult(
                source_id=source.id,
                target_id=target.id,
                effect_type="heat_transfer",
                magnitude=absorbed,
                energy_delta=absorbed * 0.7,
                metadata={
                    "formula": formula,
                    "material_type": mat.get("type", "unknown"),
                    "temperature_delta": absorbed / max(mat["melting_point"], 1.0),
                },
            )

        if formula == "conductive_transfer" and target is not None:
            transfer = EnergyTransfer().extract(source)
            mat = Material().extract(target)
            flow = transfer["rate"] * transfer["efficiency"] * mat["conductivity"]
            return InteractionResult(
                source_id=source.id,
                target_id=target.id,
                effect_type="conductive_transfer",
                magnitude=flow,
                energy_delta=flow * 0.5,
                metadata={"formula": formula},
            )

        return None


def create_heat_object(
    creator_id: str,
    label: str,
    heat_intensity: float,
    *,
    unit: str = "joules_per_tick",
) -> CreativeObject:
    """MVP: 유저가 Heat 속성을 부여한 오브젝트 생성 (파이어볼 스킬 대체)."""
    return CreativeObject(
        creator_id=creator_id,
        label=label,
        properties=[
            PropertyDef(name="heat_intensity", value=heat_intensity, unit=unit),
        ],
    )


def create_material_object(
    creator_id: str,
    label: str,
    material_type: str,
    *,
    thermal_conductivity: float = 0.5,
    melting_point: float = 1200.0,
) -> CreativeObject:
    """MVP: 유저가 Material 속성을 부여한 오브젝트 생성."""
    return CreativeObject(
        creator_id=creator_id,
        label=label,
        properties=[
            PropertyDef(name="material_type", value=0.0, unit=material_type),
            PropertyDef(
                name="thermal_conductivity",
                value=thermal_conductivity,
                unit="w_per_mk",
            ),
            PropertyDef(name="melting_point", value=melting_point, unit="celsius"),
        ],
    )
