"""Crafting recipes and professions.

A :class:`Recipe` turns input materials into an output item, optionally requiring a
*station* (a forge, an alchemy table) available at the player's current location and
a minimum profession skill.  Successful crafts grant profession XP.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .items import ItemRegistry
from .rng import GameRandom


@dataclass
class Recipe:
    id: str
    name: str
    inputs: tuple[tuple[str, int], ...]   # (item_id, qty)
    output: str
    output_qty: int = 1
    profession: str = "general"
    skill_required: int = 0
    station: str = ""                     # required point-of-interest tag
    base_success: float = 0.95

    def describe(self, registry: ItemRegistry) -> str:
        ins = ", ".join(f"{qty}x {registry.get(i).name}" for i, qty in self.inputs)
        out = registry.get(self.output).name
        extra = f" @ {self.station}" if self.station else ""
        return f"{self.name}: {ins} -> {self.output_qty}x {out}{extra}"


class RecipeRegistry:
    def __init__(self) -> None:
        self._recipes: dict[str, Recipe] = {}

    def register(self, recipe: Recipe) -> Recipe:
        self._recipes[recipe.id] = recipe
        return recipe

    def get(self, recipe_id: str) -> Recipe:
        return self._recipes[recipe_id]

    def all(self) -> list[Recipe]:
        return list(self._recipes.values())

    def craftable_at(self, station_tags: set[str]) -> list[Recipe]:
        return [r for r in self._recipes.values()
                if not r.station or r.station in station_tags]


class CraftingManager:
    def __init__(self, registry: RecipeRegistry, items: ItemRegistry, rng: GameRandom) -> None:
        self.registry = registry
        self.items = items
        self.rng = rng

    def can_craft(self, player, recipe_id: str, station_tags: set[str]) -> tuple[bool, str]:
        if recipe_id not in [r.id for r in self.registry.all()]:
            return False, "No such recipe."
        recipe = self.registry.get(recipe_id)
        if recipe.station and recipe.station not in station_tags:
            return False, f"You need a {recipe.station} to craft this."
        skill = player.professions.get(recipe.profession, 0) if hasattr(player, "professions") else 0
        if skill < recipe.skill_required:
            return False, (f"Requires {recipe.profession} skill {recipe.skill_required} "
                           f"(you have {skill}).")
        for item_id, qty in recipe.inputs:
            if not player.inventory.has(item_id, qty):
                return False, f"Missing {qty}x {self.items.get(item_id).name}."
        return True, "ok"

    def craft(self, player, recipe_id: str, station_tags: set[str]) -> tuple[bool, str]:
        ok, reason = self.can_craft(player, recipe_id, station_tags)
        if not ok:
            return False, reason
        recipe = self.registry.get(recipe_id)
        for item_id, qty in recipe.inputs:
            player.inventory.remove(item_id, qty)
        if not self.rng.chance(recipe.base_success):
            return False, f"The {recipe.name} was ruined! Materials lost."
        player.inventory.add(recipe.output, recipe.output_qty)
        if not hasattr(player, "professions"):
            player.professions = {}
        player.professions[recipe.profession] = player.professions.get(recipe.profession, 0) + 1
        out = self.items.get(recipe.output)
        return True, (f"Crafted {recipe.output_qty}x {out.name}! "
                      f"({recipe.profession} skill now "
                      f"{player.professions[recipe.profession]})")
