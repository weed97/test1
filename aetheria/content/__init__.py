"""Authored game content for Aetheria.

``build_world(seed)`` assembles a fully-populated :class:`~aetheria.state.World`:
items, abilities, classes, recipes, factions, the map, the bestiary, the NPC
population, the quests and the opening rumours.  The persistence layer calls this to
rebuild static content before overlaying a saved dynamic state.
"""

from __future__ import annotations

from ..state import World


def build_world(seed: int | str | None = None) -> World:
    world = World(seed)
    # order matters: items/abilities first, then things that reference them
    from .itemsdata import register_items
    from .abilitiesdata import register_abilities
    from .classesdata import register_classes
    from .recipesdata import register_recipes
    from .factionsdata import register_factions
    from .worlddata import register_world
    from .monsters import register_bestiary
    from .npcdata import register_npcs
    from .questdata import register_quests
    from .rumors import register_rumors

    register_items(world)
    register_abilities(world)
    register_classes(world)
    register_recipes(world)
    register_factions(world)
    register_world(world)
    register_bestiary(world)
    register_npcs(world)
    register_quests(world)
    register_rumors(world)
    return world


__all__ = ["build_world"]
