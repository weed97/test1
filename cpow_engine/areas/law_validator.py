"""세계 법칙 검증 — 위반 시 강제 거부 (감쇄 없음)."""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from cpow_engine.areas.laws import AreaLawSet
from cpow_engine.models import CreativeObject, PropertyDef, SimulationState

ALLOWED_PROPERTY_NAMES: frozenset[str] = frozenset({
    "heat_intensity",
    "thermal_conductivity",
    "melting_point",
    "material_type",
    "transfer_rate",
    "efficiency",
    "scale",
    "area_id",
    "area_seed",
    "creation_investment",
    "durability",
    "is_confirmed",
    "is_core_facility",
    "spatial_x",
    "spatial_y",
    "spatial_z",
})

PROPERTY_BOUNDS: dict[str, tuple[float, float]] = {
    "heat_intensity": (0.0, 10_000.0),
    "thermal_conductivity": (0.0, 2.0),
    "melting_point": (0.0, 6_000.0),
    "transfer_rate": (0.0, 1.0),
    "efficiency": (0.0, 1.0),
    "scale": (0.01, 20.0),
    "spatial_x": (-100_000.0, 100_000.0),
    "spatial_y": (-100_000.0, 100_000.0),
    "spatial_z": (-100_000.0, 100_000.0),
}

MAX_LABEL_LENGTH = 120
MAX_PROPERTIES = 16
MAX_CONNECTIONS = 32


@dataclass
class LawViolation:
    code: str
    message: str
    property_name: str = ""

    def to_dict(self) -> dict[str, str]:
        return {
            "code": self.code,
            "message": self.message,
            "property_name": self.property_name,
        }


@dataclass
class LawValidationResult:
    ok: bool
    violations: list[LawViolation] = field(default_factory=list)

    @property
    def codes(self) -> list[str]:
        return [v.code for v in self.violations]


class WorldLawValidator:
    """오브젝트가 에리어·세계 법칙을 깨는지 엄격 검사."""

    def validate_creation(
        self,
        obj: CreativeObject,
        laws: AreaLawSet,
        *,
        creation_type: str,
        role_max_heat: float,
        state: SimulationState | None = None,
        is_founding_seed: bool = False,
    ) -> LawValidationResult:
        violations: list[LawViolation] = []

        violations.extend(self._validate_structure(obj))
        violations.extend(self._validate_creation_type(obj, creation_type, is_founding_seed))
        violations.extend(self._validate_properties(obj, laws, role_max_heat, is_founding_seed))
        violations.extend(self._validate_connections(obj, state))

        if violations:
            return LawValidationResult(False, violations)
        return LawValidationResult(True)

    def validate_mutation(
        self,
        existing: CreativeObject,
        mutated: CreativeObject,
        laws: AreaLawSet,
        *,
        role_max_heat: float,
        state: SimulationState | None = None,
    ) -> LawValidationResult:
        violations: list[LawViolation] = []
        is_seed = is_founding_core(existing) and is_founding_core(mutated)
        violations.extend(self._validate_structure(mutated))
        violations.extend(self._validate_properties(mutated, laws, role_max_heat, is_seed))
        violations.extend(self._validate_connections(mutated, state))

        if is_founding_core(existing) and not is_founding_core(mutated):
            violations.append(LawViolation(
                "founding_core_tamper",
                "창조 심장의 정체성을 변경할 수 없습니다",
            ))

        if violations:
            return LawValidationResult(False, violations)
        return LawValidationResult(True)

    def _validate_structure(self, obj: CreativeObject) -> list[LawViolation]:
        out: list[LawViolation] = []
        if not obj.label or not obj.label.strip():
            out.append(LawViolation("empty_label", "오브젝트 이름이 비어 있습니다"))
        elif len(obj.label) > MAX_LABEL_LENGTH:
            out.append(LawViolation(
                "label_too_long",
                f"이름은 {MAX_LABEL_LENGTH}자 이하여야 합니다",
            ))

        if len(obj.properties) > MAX_PROPERTIES:
            out.append(LawViolation(
                "too_many_properties",
                f"속성은 최대 {MAX_PROPERTIES}개까지 허용됩니다",
            ))

        if len(obj.connections) > MAX_CONNECTIONS:
            out.append(LawViolation(
                "too_many_connections",
                f"연결은 최대 {MAX_CONNECTIONS}개까지 허용됩니다",
            ))

        names = [p.name.lower() for p in obj.properties]
        if len(names) != len(set(names)):
            out.append(LawViolation("duplicate_property", "중복 속성은 허용되지 않습니다"))

        return out

    def _validate_creation_type(
        self,
        obj: CreativeObject,
        creation_type: str,
        is_founding_seed: bool,
    ) -> list[LawViolation]:
        if is_founding_seed:
            return []
        ctype = creation_type.lower()
        if ctype == "heat" and obj.get_property("heat_intensity") is None:
            return [LawViolation(
                "missing_required_property",
                "heat 창조에는 heat_intensity가 필요합니다",
                "heat_intensity",
            )]
        if ctype == "material" and obj.get_property("material_type") is None:
            return [LawViolation(
                "missing_required_property",
                "material 창조에는 material_type이 필요합니다",
                "material_type",
            )]
        return []

    def _validate_properties(
        self,
        obj: CreativeObject,
        laws: AreaLawSet,
        role_max_heat: float,
        is_founding_seed: bool,
    ) -> list[LawViolation]:
        out: list[LawViolation] = []
        regional_max = laws.physics_constants.get("max_heat_intensity", 300.0)
        heat_cap = min(role_max_heat, regional_max)

        for prop in obj.properties:
            out.extend(self._validate_single_property(
                prop, heat_cap, is_founding_seed,
            ))
        return out

    def _validate_single_property(
        self,
        prop: PropertyDef,
        heat_cap: float,
        is_founding_seed: bool,
    ) -> list[LawViolation]:
        out: list[LawViolation] = []
        name = prop.name.lower()

        if name not in ALLOWED_PROPERTY_NAMES:
            out.append(LawViolation(
                "forbidden_property",
                f"허용되지 않은 속성: {prop.name}",
                prop.name,
            ))
            return out

        if name == "area_seed" and not is_founding_seed:
            out.append(LawViolation(
                "forbidden_area_seed",
                "area_seed는 창시 심장에만 부여할 수 있습니다",
                prop.name,
            ))

        if name == "material_type":
            if not prop.unit or not prop.unit.strip():
                out.append(LawViolation(
                    "invalid_material_type",
                    "material_type에는 재료 이름(unit)이 필요합니다",
                    prop.name,
                ))
            return out

        if name in ("area_id",):
            return out

        if not math.isfinite(prop.value):
            out.append(LawViolation(
                "non_finite_value",
                f"{prop.name} 값이 유한하지 않습니다",
                prop.name,
            ))
            return out

        bounds = PROPERTY_BOUNDS.get(name)
        if bounds:
            lo, hi = bounds
            if prop.value < lo or prop.value > hi:
                out.append(LawViolation(
                    "value_out_of_bounds",
                    f"{prop.name}={prop.value} 는 허용 범위 [{lo}, {hi}] 밖입니다",
                    prop.name,
                ))

        if name == "heat_intensity" and prop.value > heat_cap:
            out.append(LawViolation(
                "heat_exceeds_law_limit",
                f"heat_intensity={prop.value} 는 법칙 상한 {heat_cap} 을 초과합니다",
                prop.name,
            ))

        return out

    def _validate_connections(
        self,
        obj: CreativeObject,
        state: SimulationState | None,
    ) -> list[LawViolation]:
        if not obj.connections or state is None:
            return []
        out: list[LawViolation] = []
        for cid in obj.connections:
            if cid == obj.id:
                out.append(LawViolation(
                    "self_connection",
                    "오브젝트는 자기 자신과 연결할 수 없습니다",
                ))
            elif cid not in state.objects:
                out.append(LawViolation(
                    "connection_target_missing",
                    f"연결 대상이 존재하지 않습니다: {cid}",
                ))
        return out


def is_founding_core(obj: CreativeObject) -> bool:
    return obj.get_property("area_seed") is not None


_default_validator = WorldLawValidator()


def validate_creation(
    obj: CreativeObject,
    laws: AreaLawSet,
    *,
    creation_type: str,
    role_max_heat: float,
    state: SimulationState | None = None,
    is_founding_seed: bool = False,
) -> LawValidationResult:
    return _default_validator.validate_creation(
        obj, laws,
        creation_type=creation_type,
        role_max_heat=role_max_heat,
        state=state,
        is_founding_seed=is_founding_seed,
    )


def validate_mutation(
    existing: CreativeObject,
    mutated: CreativeObject,
    laws: AreaLawSet,
    *,
    role_max_heat: float,
    state: SimulationState | None = None,
) -> LawValidationResult:
    return _default_validator.validate_mutation(
        existing, mutated, laws,
        role_max_heat=role_max_heat,
        state=state,
    )
