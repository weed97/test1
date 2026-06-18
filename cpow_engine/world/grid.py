"""월드 그리드 — 좌표→바이옴·광맥."""

from __future__ import annotations

import hashlib

from cpow_engine.world.biomes import BIOME_CATALOG, BiomeDef, BiomeId
from cpow_engine.world.ores import ORE_CATALOG, OreDef


_BIOME_RING: tuple[BiomeId, ...] = (
    BiomeId.PLAINS,
    BiomeId.FOREST,
    BiomeId.HILLS,
    BiomeId.COAST,
    BiomeId.DESERT,
    BiomeId.ALPINE,
    BiomeId.VOLCANO,
    BiomeId.OCEAN,
    BiomeId.MINE,
    BiomeId.RIFT,
)


def _hash_u32(seed: str, *parts: int) -> int:
    raw = f"{seed}:{':'.join(str(p) for p in parts)}".encode()
    return int(hashlib.sha256(raw).hexdigest()[:8], 16)


def biome_at(seed: str, cell_x: int, cell_z: int) -> BiomeDef:
    """결정론적 바이옴 — 에리어 시드 + 셀 좌표."""
    h = _hash_u32(seed, cell_x, cell_z, 1)
    idx = h % len(_BIOME_RING)
    # 평원·숲 비중을 높임 (안전 허브 공간)
    if h % 5 < 2:
        idx = 0 if h % 2 == 0 else 1
    biome_id = _BIOME_RING[idx]
    return BIOME_CATALOG[biome_id]


def cell_from_world(x: float, z: float, cell_size: int = 64) -> tuple[int, int]:
    return int(x // cell_size), int(z // cell_size)


def ore_at_position(
    seed: str,
    biome: BiomeId,
    depth_y: int,
    cell_x: int,
    cell_z: int,
) -> OreDef | None:
    """위치에 노출된 광맥 (없을 수 있음)."""
    candidates = [
        o for o in ORE_CATALOG.values()
        if biome in o.biomes
        and o.min_depth <= depth_y <= o.max_depth
        and o.source.value == "vein"
    ]
    if not candidates:
        return None
    h = _hash_u32(seed, cell_x, cell_z, depth_y, 7)
    pick = candidates[h % len(candidates)]
    # 희귀도 — 티어 높을수록 낮은 확률
    rarity_gate = 100 - int(pick.tier) * 12
    if (h >> 8) % 100 > rarity_gate:
        return None
    return pick


def cell_snapshot(seed: str, cell_x: int, cell_z: int, depth_y: int = 48) -> dict:
    biome = biome_at(seed, cell_x, cell_z)
    ore = ore_at_position(seed, biome.biome_id, depth_y, cell_x, cell_z)
    return {
        "cell_x": cell_x,
        "cell_z": cell_z,
        "depth_y": depth_y,
        "biome": biome.to_dict(),
        "ore": ore.to_dict() if ore else None,
    }
