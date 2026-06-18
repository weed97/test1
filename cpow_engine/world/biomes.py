"""바이옴 정의 — 지역 규칙·위험·소리 예고."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ZoneClass(str, Enum):
    """건축·정착 허용 구역."""

    SAFE = "safe"
    BUFFER = "buffer"
    DANGER = "danger"


class BiomeId(str, Enum):
    PLAINS = "plains"
    FOREST = "forest"
    HILLS = "hills"
    COAST = "coast"
    ALPINE = "alpine"
    DESERT = "desert"
    VOLCANO = "volcano"
    OCEAN = "ocean"
    MINE = "mine"
    RIFT = "rift"


@dataclass(frozen=True)
class HazardPhase:
    """바이옴별 주기 상태."""

    phase_id: str
    label: str
    danger_level: int
    audio_cue: str
    audio_stage: str
    seconds_to_event: float = 0.0


@dataclass(frozen=True)
class BiomeDef:
    biome_id: BiomeId
    label: str
    zone: ZoneClass
    phases: tuple[str, ...]
    hazard_audio: dict[str, str] = field(default_factory=dict)
    allows_settlement: bool = False
    allows_outpost: bool = False

    def to_dict(self) -> dict:
        return {
            "biome_id": self.biome_id.value,
            "label": self.label,
            "zone": self.zone.value,
            "phases": list(self.phases),
            "hazard_audio": dict(self.hazard_audio),
            "allows_settlement": self.allows_settlement,
            "allows_outpost": self.allows_outpost,
        }


BIOME_CATALOG: dict[BiomeId, BiomeDef] = {
    BiomeId.PLAINS: BiomeDef(
        BiomeId.PLAINS,
        "평원",
        ZoneClass.SAFE,
        ("calm", "harvest", "flood_warning"),
        {
            "flood_warning": "env.plains.flood_rumble",
            "flood": "env.plains.flood_surge",
        },
        allows_settlement=True,
        allows_outpost=True,
    ),
    BiomeId.FOREST: BiomeDef(
        BiomeId.FOREST,
        "숲",
        ZoneClass.SAFE,
        ("calm", "rain", "growth"),
        {
            "rain": "env.forest.rain_loop",
            "growth": "env.forest.creak",
        },
        allows_settlement=True,
        allows_outpost=True,
    ),
    BiomeId.HILLS: BiomeDef(
        BiomeId.HILLS,
        "산악",
        ZoneClass.BUFFER,
        ("calm", "fog", "rockfall_warning"),
        {
            "rockfall_warning": "env.hills.stress_crack",
            "rockfall": "env.hills.avalanche",
        },
        allows_outpost=True,
    ),
    BiomeId.COAST: BiomeDef(
        BiomeId.COAST,
        "해안",
        ZoneClass.BUFFER,
        ("calm", "tide_low", "tide_high", "tsunami_warning"),
        {
            "tide_low": "env.coast.tide_out",
            "tide_high": "env.coast.tide_in",
            "tsunami_warning": "env.coast.tsunami_rumble",
            "tsunami": "env.coast.tsunami_roar",
        },
        allows_outpost=True,
    ),
    BiomeId.ALPINE: BiomeDef(
        BiomeId.ALPINE,
        "설산",
        ZoneClass.DANGER,
        ("calm", "blizzard_warning", "blizzard"),
        {
            "blizzard_warning": "env.alpine.wind_howl",
            "blizzard": "env.alpine.blizzard_peak",
        },
        allows_outpost=True,
    ),
    BiomeId.DESERT: BiomeDef(
        BiomeId.DESERT,
        "사막",
        ZoneClass.DANGER,
        ("calm", "heat_day", "sandstorm_warning", "sandstorm"),
        {
            "heat_day": "env.desert.heat_shimmer",
            "sandstorm_warning": "env.desert.wind_whistle",
            "sandstorm": "env.desert.sand_blast",
        },
        allows_outpost=True,
    ),
    BiomeId.VOLCANO: BiomeDef(
        BiomeId.VOLCANO,
        "화산",
        ZoneClass.DANGER,
        ("calm", "tremor", "gas_warning", "eruption_warning", "eruption"),
        {
            "tremor": "env.volcano.low_rumble",
            "gas_warning": "env.volcano.hiss",
            "eruption_warning": "env.volcano.deep_boom",
            "eruption": "env.volcano.blast",
        },
        allows_outpost=True,
    ),
    BiomeId.OCEAN: BiomeDef(
        BiomeId.OCEAN,
        "심해",
        ZoneClass.DANGER,
        ("calm", "current_shift", "pressure_warning"),
        {
            "current_shift": "env.ocean.drift",
            "pressure_warning": "env.ocean.depth_pulse",
        },
        allows_outpost=True,
    ),
    BiomeId.MINE: BiomeDef(
        BiomeId.MINE,
        "탄광",
        ZoneClass.BUFFER,
        ("calm", "cave_in_warning", "cave_in"),
        {
            "cave_in_warning": "env.mine.timber_stress",
            "cave_in": "env.mine.collapse",
        },
        allows_outpost=True,
    ),
    BiomeId.RIFT: BiomeDef(
        BiomeId.RIFT,
        "균열",
        ZoneClass.DANGER,
        ("calm", "rift_hum", "rift_open", "rift_close"),
        {
            "rift_hum": "env.rift.low_tone",
            "rift_open": "env.rift.tear",
            "rift_close": "env.rift.seal",
        },
        allows_outpost=True,
    ),
}


def biome_catalog_public() -> list[dict]:
    return [b.to_dict() for b in BIOME_CATALOG.values()]
