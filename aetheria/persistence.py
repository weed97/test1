"""Save and load the full mutable world state to JSON.

Static *content* (items, abilities, classes, recipes, quests, the map, factions) is
always rebuilt from code, so the save file only needs the *dynamic* state: the clock,
the RNG cursor, the market, every NPC's living condition, the player, the rumour pool
and the world chronicle.  This keeps saves small and forward-compatible with content
patches.
"""

from __future__ import annotations

import json
import os
from typing import Callable

from .character import NPC, Player
from .economy import Market
from .gametime import GameClock
from .state import World

SAVE_VERSION = 1


def _rng_state_to_json(state) -> list:
    version, internal, gauss = state
    return [version, list(internal), gauss]


def _rng_state_from_json(data) -> tuple:
    version, internal, gauss = data
    return (version, tuple(internal), gauss)


def serialize(world: World) -> dict:
    return {
        "save_version": SAVE_VERSION,
        "seed": world.seed,
        "tick_count": world.tick_count,
        "clock": world.clock.to_dict(),
        "rng_state": _rng_state_to_json(world.rng.getstate()),
        "market": world.market.to_dict(),
        "rumor_pool": list(world.rumor_pool),
        "chronicle": list(world.chronicle),
        "player": world.player.to_dict() if world.player else None,
        "npcs": {nid: npc.to_dict() for nid, npc in world.npcs.items()},
    }


def save(world: World, path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    os.makedirs(directory, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(serialize(world), fh, indent=2)


def load(path: str, content_builder: Callable[[int | str | None], World]) -> World:
    """Rebuild a world from ``content_builder(seed)`` then overlay saved state."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    world = content_builder(data.get("seed"))
    world.clock = GameClock.from_dict(data["clock"])
    world.tick_count = int(data.get("tick_count", 0))
    world.rng.setstate(_rng_state_from_json(data["rng_state"]))
    world.market = Market.from_dict(data["market"], world.rng)
    world.trade.market = world.market
    world.rumor_pool = list(data.get("rumor_pool", []))
    world.chronicle = list(data.get("chronicle", []))

    # Overlay dynamic NPC state on top of the freshly-built population.
    saved_npcs = data.get("npcs", {})
    for nid, ndata in saved_npcs.items():
        world.npcs[nid] = NPC.from_dict(ndata, world.items)

    if data.get("player"):
        world.player = Player.from_dict(data["player"], world.items)
    return world


def autosave_path(save_dir: str, slot: str = "autosave") -> str:
    return os.path.join(save_dir, f"{slot}.json")
