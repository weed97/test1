"""월드 서비스 — 바이옴·채굴·건축·위험."""

from __future__ import annotations

from cpow_engine.world.biomes import biome_catalog_public
from cpow_engine.world.building import (
    blueprint_catalog_public,
    validate_blueprint_placement,
)
from cpow_engine.world.grid import biome_at, cell_from_world, cell_snapshot, ore_at_position
from cpow_engine.world.hazards import advance_hazard, hazard_snapshot
from cpow_engine.world.mining import attempt_mine, parse_tool_from_payload
from cpow_engine.world.ores import ORE_CATALOG, ore_catalog_public
from cpow_engine.world.state import AreaWorldRuntime
from cpow_engine.world.tools import tool_catalog_public


class WorldService:
    def __init__(self) -> None:
        self._areas: dict[str, AreaWorldRuntime] = {}

    def runtime_for(self, area_id: str) -> AreaWorldRuntime:
        if area_id not in self._areas:
            self._areas[area_id] = AreaWorldRuntime(
                area_id=area_id,
                world_seed=area_id,
            )
        return self._areas[area_id]

    def catalog(self) -> dict:
        return {
            "ok": True,
            "biomes": biome_catalog_public(),
            "ores": ore_catalog_public(),
            "tools": tool_catalog_public(),
            "blueprints": blueprint_catalog_public(),
        }

    def inspect_cell(
        self,
        area_id: str,
        *,
        x: float,
        z: float,
        depth_y: int = 48,
        cell_size: int = 64,
        advance_tick: bool = False,
    ) -> dict:
        runtime = self.runtime_for(area_id)
        cx, cz = cell_from_world(x, z, cell_size)
        biome = biome_at(runtime.world_seed, cx, cz)
        hazard_st = runtime.hazard_state_for(cx, cz)
        if advance_tick:
            runtime.world_tick += 1
            advance_hazard(hazard_st, biome)
        snap = cell_snapshot(runtime.world_seed, cx, cz, depth_y)
        snap["hazard"] = hazard_snapshot(biome, hazard_st)
        snap["ok"] = True
        snap["area_id"] = area_id
        return snap

    def mine(
        self,
        area_id: str,
        payload: dict,
    ) -> dict:
        runtime = self.runtime_for(area_id)
        actor_id = str(payload.get("actor_id", "anonymous"))
        x = float(payload.get("x", 0.0))
        z = float(payload.get("z", 0.0))
        depth_y = int(payload.get("depth_y", 48))
        cell_size = int(payload.get("cell_size", 64))
        ore_id = payload.get("ore_id")
        consumable = str(payload.get("consumable", ""))

        cx, cz = cell_from_world(x, z, cell_size)
        biome = biome_at(runtime.world_seed, cx, cz)
        hazard_st = runtime.hazard_state_for(cx, cz)
        from cpow_engine.world.hazards import hazard_phase_for

        phase = hazard_phase_for(biome, hazard_st)

        if ore_id:
            ore = ORE_CATALOG.get(str(ore_id))
        else:
            ore = ore_at_position(runtime.world_seed, biome.biome_id, depth_y, cx, cz)
        if ore is None:
            return {"ok": False, "reason": "no_ore_here", "area_id": area_id}

        tool = parse_tool_from_payload(payload)
        profile = runtime.miner_profile(actor_id)
        result = attempt_mine(
            actor_id=actor_id,
            ore=ore,
            tool=tool,
            profile=profile,
            consumable=consumable,
            hazard_danger=phase.danger_level,
        )
        out = result.to_dict()
        out["area_id"] = area_id
        out["biome_id"] = biome.biome_id.value
        out["hazard_audio"] = {
            "audio_cue": phase.audio_cue,
            "audio_stage": phase.audio_stage,
            "phase_id": phase.phase_id,
        }
        return out

    def validate_build(self, payload: dict) -> dict:
        area_id = str(payload.get("area_id", ""))
        biome_id = str(payload.get("biome_id", "plains"))
        blueprint_id = str(payload.get("blueprint_id", ""))
        placed_modules = {
            str(k): int(v)
            for k, v in dict(payload.get("placed_modules", {})).items()
        }
        placed_materials = {
            str(k): int(v)
            for k, v in dict(payload.get("placed_materials", {})).items()
        }
        civ = int(payload.get("civilization_level", 0))
        result = validate_blueprint_placement(
            biome_id=biome_id,
            blueprint_id=blueprint_id,
            placed_modules=placed_modules,
            placed_materials=placed_materials,
            civilization_level=civ,
        )
        out = result.to_dict()
        out["ok"] = result.ok
        out["area_id"] = area_id
        return out

    def boss_loot(self, area_id: str, payload: dict) -> dict:
        """균열 보스 — 블랙미스릴 파편 시드."""
        runtime = self.runtime_for(area_id)
        actor_id = str(payload.get("actor_id", "anonymous"))
        from cpow_engine.world.mining import build_resource_object, apply_mining_xp

        ore = ORE_CATALOG["black_mithril_shard"]
        profile = runtime.miner_profile(actor_id)
        amount = float(payload.get("amount", 1.0))
        apply_mining_xp(profile, ore.ore_id, amount)
        return {
            "ok": True,
            "reason": "boss_loot",
            "area_id": area_id,
            "resource": build_resource_object(actor_id, ore.ore_id, amount).to_dict(),
            "mining": profile.to_dict(),
        }


_DEFAULT = WorldService()


def get_world_service() -> WorldService:
    return _DEFAULT
