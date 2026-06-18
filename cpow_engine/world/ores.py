"""광물·자재 정의 — 티어·경도·바이옴."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from cpow_engine.world.biomes import BiomeId


class MaterialTier(int, Enum):
    T0 = 0
    T1 = 1
    T2 = 2
    T3 = 3
    T4 = 4
    T5 = 5
    T6 = 6


class OreSource(str, Enum):
    VEIN = "vein"
    MOB = "mob"
    BOSS = "boss"
    CRAFT = "craft"


@dataclass(frozen=True)
class OreDef:
    ore_id: str
    label: str
    tier: MaterialTier
    hardness: int
    base_yield: float
    biomes: frozenset[BiomeId]
    min_depth: int = 0
    max_depth: int = 256
    source: OreSource = OreSource.VEIN
    requires_consumable: str = ""

    def to_dict(self) -> dict:
        return {
            "ore_id": self.ore_id,
            "label": self.label,
            "tier": int(self.tier),
            "hardness": self.hardness,
            "base_yield": self.base_yield,
            "biomes": sorted(b.value for b in self.biomes),
            "min_depth": self.min_depth,
            "max_depth": self.max_depth,
            "source": self.source.value,
            "requires_consumable": self.requires_consumable,
        }


ORE_CATALOG: dict[str, OreDef] = {
    "dirt": OreDef("dirt", "흙", MaterialTier.T0, 1, 4.0, frozenset({BiomeId.PLAINS, BiomeId.FOREST}), 0, 32),
    "stone": OreDef("stone", "돌", MaterialTier.T0, 1, 3.0, frozenset(BiomeId), 0, 64),
    "coal": OreDef("coal", "석탄", MaterialTier.T1, 2, 2.5, frozenset({BiomeId.MINE, BiomeId.HILLS, BiomeId.PLAINS}), 16, 96),
    "copper_ore": OreDef(
        "copper_ore", "구리 광석", MaterialTier.T1, 2, 2.0,
        frozenset({BiomeId.HILLS, BiomeId.PLAINS, BiomeId.MINE}), 20, 80,
    ),
    "iron_ore": OreDef(
        "iron_ore", "철 광석", MaterialTier.T2, 3, 1.8,
        frozenset({BiomeId.HILLS, BiomeId.MINE, BiomeId.PLAINS}), 32, 128,
    ),
    "silver_ore": OreDef(
        "silver_ore", "은 광석", MaterialTier.T3, 4, 1.2,
        frozenset({BiomeId.HILLS, BiomeId.MINE}), 56, 160,
    ),
    "gold_ore": OreDef(
        "gold_ore", "금 광석", MaterialTier.T3, 4, 1.0,
        frozenset({BiomeId.HILLS, BiomeId.MINE}), 64, 180,
    ),
    "diamond_ore": OreDef(
        "diamond_ore", "다이아 광석", MaterialTier.T4, 5, 0.6,
        frozenset(BiomeId), 80, 256,
    ),
    "sapphire_ore": OreDef(
        "sapphire_ore", "사파이어", MaterialTier.T4, 5, 0.5,
        frozenset({BiomeId.MINE, BiomeId.RIFT}), 72, 200,
    ),
    "emerald_ore": OreDef(
        "emerald_ore", "에메랄드", MaterialTier.T4, 5, 0.45,
        frozenset({BiomeId.FOREST, BiomeId.RIFT}), 70, 190,
    ),
    "frost_crystal": OreDef(
        "frost_crystal", "서리 결정", MaterialTier.T4, 4, 0.8,
        frozenset({BiomeId.ALPINE}), 40, 160,
    ),
    "sulfur": OreDef(
        "sulfur", "황", MaterialTier.T3, 4, 1.1,
        frozenset({BiomeId.VOLCANO}), 20, 120,
    ),
    "pearl": OreDef(
        "pearl", "진주", MaterialTier.T3, 3, 0.7,
        frozenset({BiomeId.OCEAN, BiomeId.COAST}), 0, 40, source=OreSource.VEIN,
    ),
    "mithril_ore": OreDef(
        "mithril_ore", "미스릴 광석", MaterialTier.T5, 6, 0.35,
        frozenset({BiomeId.ALPINE, BiomeId.RIFT, BiomeId.VOLCANO}), 90, 256,
    ),
    "black_mithril_shard": OreDef(
        "black_mithril_shard", "블랙미스릴 파편", MaterialTier.T6, 7, 0.15,
        frozenset({BiomeId.RIFT}), source=OreSource.BOSS,
    ),
    "black_mithril_ore": OreDef(
        "black_mithril_ore", "블랙미스릴 광석", MaterialTier.T6, 7, 0.12,
        frozenset({BiomeId.RIFT}), 100, 256,
        requires_consumable="void_stabilizer",
    ),
}


def ore_catalog_public() -> list[dict]:
    return [o.to_dict() for o in ORE_CATALOG.values()]
