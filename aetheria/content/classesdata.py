"""Playable character classes with starting kits."""

from __future__ import annotations

from ..skills import CharacterClass
from ..state import World
from ..stats import Attribute


def register_classes(world: World) -> None:
    reg = world.classes
    add = reg.register

    add(CharacterClass(
        "warrior", "Warrior",
        "A frontline fighter who lives by the strength of arm and steel.",
        primary_attr=Attribute.STRENGTH, secondary_attr=Attribute.CONSTITUTION,
        attribute_bias={"strength": 6, "constitution": 4, "dexterity": 2,
                        "intelligence": -2, "wisdom": 0, "charisma": 0},
        starting_abilities=("power_strike", "second_wind", "shield_bash"),
        starting_items=("iron_sword", "wooden_shield", "leather_armor",
                        "minor_health_potion", "bread"),
        health_per_level=10, mana_per_level=2, hit_die=10))

    add(CharacterClass(
        "mage", "Mage",
        "A scholar of the arcane who turns thought into fire and frost.",
        primary_attr=Attribute.INTELLIGENCE, secondary_attr=Attribute.WISDOM,
        attribute_bias={"intelligence": 6, "wisdom": 3, "dexterity": 1,
                        "strength": -2, "constitution": 0, "charisma": 1},
        starting_abilities=("firebolt", "frost_lance", "arcane_shield"),
        starting_items=("oak_staff", "mage_robe", "mana_potion", "minor_health_potion"),
        health_per_level=5, mana_per_level=8, hit_die=6))

    add(CharacterClass(
        "rogue", "Rogue",
        "A nimble opportunist who strikes from the shadows.",
        primary_attr=Attribute.DEXTERITY, secondary_attr=Attribute.CHARISMA,
        attribute_bias={"dexterity": 6, "charisma": 3, "constitution": 1,
                        "strength": 1, "intelligence": 1, "wisdom": -1},
        starting_abilities=("backstab", "rapid_shot", "second_wind"),
        starting_items=("dagger", "leather_armor", "minor_health_potion",
                        "stamina_draught"),
        health_per_level=7, mana_per_level=3, hit_die=8))

    add(CharacterClass(
        "ranger", "Ranger",
        "A hunter of the wilds, deadly at range and at home in the wood.",
        primary_attr=Attribute.DEXTERITY, secondary_attr=Attribute.WISDOM,
        attribute_bias={"dexterity": 5, "wisdom": 3, "constitution": 2,
                        "strength": 1, "intelligence": 0, "charisma": -1},
        starting_abilities=("rapid_shot", "second_wind", "poison_dart"),
        starting_items=("hunting_bow", "leather_armor", "leather_boots",
                        "minor_health_potion"),
        health_per_level=8, mana_per_level=4, hit_die=8))

    add(CharacterClass(
        "cleric", "Cleric",
        "A devout healer whose faith mends wounds and smites the wicked.",
        primary_attr=Attribute.WISDOM, secondary_attr=Attribute.CONSTITUTION,
        attribute_bias={"wisdom": 6, "constitution": 3, "strength": 2,
                        "charisma": 1, "intelligence": 0, "dexterity": -2},
        starting_abilities=("heal", "holy_smite", "bless"),
        starting_items=("mace_of_dawn", "chain_mail", "minor_health_potion",
                        "mana_potion"),
        health_per_level=8, mana_per_level=6, hit_die=8))

    add(CharacterClass(
        "paladin", "Paladin",
        "A holy warrior blending martial might with divine grace.",
        primary_attr=Attribute.STRENGTH, secondary_attr=Attribute.WISDOM,
        attribute_bias={"strength": 4, "wisdom": 3, "constitution": 3,
                        "charisma": 2, "dexterity": -1, "intelligence": -1},
        starting_abilities=("power_strike", "heal", "bless"),
        starting_items=("steel_longsword", "iron_shield", "chain_mail",
                        "health_potion"),
        health_per_level=9, mana_per_level=4, hit_die=10))
