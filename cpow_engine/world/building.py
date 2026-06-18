"""모듈형 건축 — 블루프린트·구역 규칙."""

from __future__ import annotations

from dataclasses import dataclass, field

from cpow_engine.world.biomes import BIOME_CATALOG, BiomeId, ZoneClass


@dataclass(frozen=True)
class ModuleReq:
    module_id: str
    count: int

    def to_dict(self) -> dict:
        return {"module_id": self.module_id, "count": int(self.count)}


@dataclass(frozen=True)
class BlueprintDef:
    blueprint_id: str
    label: str
    building_type: str
    zone_min: ZoneClass
    modules: tuple[ModuleReq, ...]
    materials: tuple[ModuleReq, ...] = ()
    civ_min: int = 0

    def to_dict(self) -> dict:
        return {
            "blueprint_id": self.blueprint_id,
            "label": self.label,
            "building_type": self.building_type,
            "zone_min": self.zone_min.value,
            "modules": [m.to_dict() for m in self.modules],
            "materials": [m.to_dict() for m in self.materials],
            "civ_min": self.civ_min,
        }


BLUEPRINT_CATALOG: dict[str, BlueprintDef] = {
    "camp_kit": BlueprintDef(
        "camp_kit",
        "원정 캠프 키트",
        "outpost",
        ZoneClass.DANGER,
        (
            ModuleReq("foundation_1x1", 1),
            ModuleReq("wall_t1", 4),
            ModuleReq("heater_core", 1),
        ),
        (ModuleReq("wood_plank", 8), ModuleReq("stone_brick", 4)),
    ),
    "smelter_lv1": BlueprintDef(
        "smelter_lv1",
        "제련소 Lv1",
        "smelter",
        ZoneClass.SAFE,
        (
            ModuleReq("foundation_2x2", 1),
            ModuleReq("wall_t1", 8),
            ModuleReq("furnace_box", 1),
            ModuleReq("chimney_stack", 1),
        ),
        (ModuleReq("iron_plate", 12), ModuleReq("stone_brick", 16)),
        civ_min=1,
    ),
    "power_line": BlueprintDef(
        "power_line",
        "지열 전력선",
        "energy",
        ZoneClass.BUFFER,
        (
            ModuleReq("pipe_straight", 4),
            ModuleReq("cable_segment", 2),
        ),
        (ModuleReq("copper_wire", 6),),
        civ_min=2,
    ),
}


@dataclass
class BuildValidationResult:
    ok: bool
    reason: str = ""
    blueprint: dict | None = None
    missing: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "reason": self.reason,
            "blueprint": self.blueprint,
            "missing": list(self.missing),
        }


_ZONE_ORDER = {ZoneClass.SAFE: 0, ZoneClass.BUFFER: 1, ZoneClass.DANGER: 2}


def _zone_allows_building(zone: ZoneClass, building_type: str) -> tuple[bool, str]:
    if building_type in ("settlement", "smelter", "greenhouse", "town_hall"):
        if zone != ZoneClass.SAFE:
            return False, "settlement_only_in_safe_zone"
        return True, "ok"
    if building_type in ("outpost", "camp", "drill_platform", "energy"):
        return True, "ok"
    if zone == ZoneClass.DANGER and building_type == "fortress_core":
        return False, "no_core_in_danger_zone"
    return True, "ok"


def validate_blueprint_placement(
    *,
    biome_id: str,
    blueprint_id: str,
    placed_modules: dict[str, int],
    placed_materials: dict[str, int] | None = None,
    civilization_level: int = 0,
) -> BuildValidationResult:
    bp = BLUEPRINT_CATALOG.get(blueprint_id)
    if bp is None:
        return BuildValidationResult(False, reason="unknown_blueprint")
    try:
        bid = BiomeId(biome_id)
    except ValueError:
        return BuildValidationResult(False, reason="unknown_biome")
    biome = BIOME_CATALOG[bid]
    zone_ok, zone_reason = _zone_allows_building(biome.zone, bp.building_type)
    if not zone_ok:
        return BuildValidationResult(False, reason=zone_reason, blueprint=bp.to_dict())
    if _ZONE_ORDER[biome.zone] < _ZONE_ORDER[bp.zone_min]:
        return BuildValidationResult(False, reason="zone_too_dangerous", blueprint=bp.to_dict())
    if civilization_level < bp.civ_min:
        return BuildValidationResult(False, reason="civilization_too_low", blueprint=bp.to_dict())
    mats = placed_materials or {}
    missing: list[dict] = []
    for req in bp.modules:
        have = int(placed_modules.get(req.module_id, 0))
        if have < req.count:
            missing.append({"kind": "module", **req.to_dict(), "have": have})
    for req in bp.materials:
        have = int(mats.get(req.module_id, 0))
        if have < req.count:
            missing.append({"kind": "material", **req.to_dict(), "have": have})
    if missing:
        return BuildValidationResult(
            False, reason="missing_parts", blueprint=bp.to_dict(), missing=missing,
        )
    return BuildValidationResult(True, reason="blueprint_valid", blueprint=bp.to_dict())


def blueprint_catalog_public() -> list[dict]:
    return [b.to_dict() for b in BLUEPRINT_CATALOG.values()]
