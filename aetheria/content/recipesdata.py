"""Crafting recipes across smithing, alchemy, cooking and tailoring."""

from __future__ import annotations

from ..crafting import Recipe
from ..state import World


def register_recipes(world: World) -> None:
    reg = world.recipes
    add = reg.register

    # smithing (requires a forge)
    add(Recipe("smelt_iron", "Smelt Iron Ingot",
               inputs=(("iron_ore", 2), ("coal", 1)), output="iron_ingot",
               profession="smithing", station="forge", skill_required=0))
    add(Recipe("forge_iron_sword", "Forge Iron Sword",
               inputs=(("iron_ingot", 3), ("oak_wood", 1)), output="iron_sword",
               profession="smithing", station="forge", skill_required=2))
    add(Recipe("forge_iron_shield", "Forge Iron Shield",
               inputs=(("iron_ingot", 4),), output="iron_shield",
               profession="smithing", station="forge", skill_required=3))
    add(Recipe("forge_chain_mail", "Forge Chain Mail",
               inputs=(("iron_ingot", 6),), output="chain_mail",
               profession="smithing", station="forge", skill_required=5))

    # alchemy (requires an alchemy table)
    add(Recipe("brew_minor_health", "Brew Minor Health Potion",
               inputs=(("redroot", 2),), output="minor_health_potion",
               profession="alchemy", station="alchemy_table", skill_required=0))
    add(Recipe("brew_health", "Brew Health Potion",
               inputs=(("redroot", 3), ("moonpetal", 1)), output="health_potion",
               profession="alchemy", station="alchemy_table", skill_required=3))
    add(Recipe("brew_mana", "Brew Mana Potion",
               inputs=(("moonpetal", 2), ("mana_crystal", 1)), output="mana_potion",
               profession="alchemy", station="alchemy_table", skill_required=2))
    add(Recipe("brew_antidote", "Brew Antidote",
               inputs=(("moonpetal", 1), ("redroot", 1)), output="antidote",
               profession="alchemy", station="alchemy_table", skill_required=1))

    # tailoring (requires a loom)
    add(Recipe("weave_robe", "Weave Enchanted Robe",
               inputs=(("linen", 3), ("mana_crystal", 1), ("spider_silk", 2)),
               output="mage_robe", profession="tailoring", station="loom",
               skill_required=3))
    add(Recipe("cure_leather", "Cure Leather Armor",
               inputs=(("wolf_pelt", 3), ("linen", 1)), output="leather_armor",
               profession="tailoring", station="loom", skill_required=1))

    # cooking (requires a cooking fire — present in taverns)
    add(Recipe("cook_venison", "Cook Roast Venison",
               inputs=(("wolf_pelt", 1),), output="venison",
               profession="cooking", station="cookfire", skill_required=0,
               base_success=0.9))
