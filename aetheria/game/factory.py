"""Build a fresh :class:`Player` from a chosen class and place them in the world."""

from __future__ import annotations

from ..character import Player
from ..skills import CharacterClass
from ..state import World
from ..stats import Attribute

START_LOCATION = "brackenford_square"


def create_player(world: World, name: str, class_id: str) -> Player:
    cls: CharacterClass = world.classes.get(class_id)
    player = Player("player", name, world.items, char_class=class_id)

    for attr_name, delta in cls.attribute_bias.items():
        player.attrs.modify(attr_name, delta)

    for ability_id in cls.starting_abilities:
        player.learn(ability_id)

    for item_id in cls.starting_items:
        if world.items.exists(item_id):
            player.inventory.add(item_id)

    # auto-equip the best obvious gear
    for item_id in cls.starting_items:
        template = world.items.get(item_id) if world.items.exists(item_id) else None
        if template and template.is_equippable:
            player.inventory.equip(item_id)

    player.gold = 75
    player.location_id = START_LOCATION
    player.discovered_locations.add(START_LOCATION)
    player.full_restore()
    world.player = player
    return player
