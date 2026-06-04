"""Items, equipment and inventories.

Items are defined as lightweight, immutable *templates* (:class:`ItemTemplate`).
A central :class:`ItemRegistry` stores every template by id.  Actors carry an
:class:`Inventory` which references items by id and quantity, which keeps save
files compact and makes balancing a single source of truth.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ItemType(str, Enum):
    WEAPON = "weapon"
    ARMOR = "armor"
    SHIELD = "shield"
    CONSUMABLE = "consumable"
    MATERIAL = "material"
    QUEST = "quest"
    TREASURE = "treasure"
    TRINKET = "trinket"
    FOOD = "food"
    BOOK = "book"


class EquipSlot(str, Enum):
    MAIN_HAND = "main_hand"
    OFF_HAND = "off_hand"
    HEAD = "head"
    BODY = "body"
    HANDS = "hands"
    FEET = "feet"
    NECK = "neck"
    RING = "ring"


class Rarity(str, Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    EPIC = "epic"
    LEGENDARY = "legendary"

    @property
    def color_hint(self) -> str:
        return {
            Rarity.COMMON: "white",
            Rarity.UNCOMMON: "green",
            Rarity.RARE: "blue",
            Rarity.EPIC: "purple",
            Rarity.LEGENDARY: "gold",
        }[self]

    @property
    def value_multiplier(self) -> float:
        return {
            Rarity.COMMON: 1.0,
            Rarity.UNCOMMON: 2.2,
            Rarity.RARE: 5.0,
            Rarity.EPIC: 12.0,
            Rarity.LEGENDARY: 30.0,
        }[self]


@dataclass(frozen=True)
class ItemTemplate:
    id: str
    name: str
    item_type: ItemType
    description: str = ""
    base_value: int = 1          # in copper; market may adjust the price
    weight: float = 1.0
    rarity: Rarity = Rarity.COMMON
    stackable: bool = False
    max_stack: int = 1
    slot: EquipSlot | None = None

    # combat-relevant numbers (zero unless applicable)
    attack_bonus: int = 0
    defense_bonus: int = 0
    damage_dice: tuple[int, int] = (0, 0)   # (count, sides)
    damage_type: str = "physical"

    # consumable effects
    heal_amount: int = 0
    mana_amount: int = 0
    stamina_amount: int = 0
    effect: str | None = None     # named status effect to apply

    # crafting / misc
    tags: tuple[str, ...] = ()

    @property
    def value(self) -> int:
        return max(1, int(self.base_value * self.rarity.value_multiplier))

    @property
    def is_equippable(self) -> bool:
        return self.slot is not None

    def describe(self) -> str:
        parts = [f"{self.name} [{self.rarity.value}]"]
        if self.damage_dice[0]:
            parts.append(f"{self.damage_dice[0]}d{self.damage_dice[1]} {self.damage_type} dmg")
        if self.attack_bonus:
            parts.append(f"+{self.attack_bonus} atk")
        if self.defense_bonus:
            parts.append(f"+{self.defense_bonus} def")
        if self.heal_amount:
            parts.append(f"heals {self.heal_amount}")
        if self.mana_amount:
            parts.append(f"restores {self.mana_amount} mana")
        if self.stamina_amount:
            parts.append(f"restores {self.stamina_amount} stamina")
        parts.append(f"{self.value}c")
        return " | ".join(parts)


class ItemRegistry:
    """Global lookup table mapping item ids to their templates."""

    def __init__(self) -> None:
        self._items: dict[str, ItemTemplate] = {}

    def register(self, template: ItemTemplate) -> ItemTemplate:
        if template.id in self._items:
            raise ValueError(f"duplicate item id: {template.id}")
        self._items[template.id] = template
        return template

    def get(self, item_id: str) -> ItemTemplate:
        try:
            return self._items[item_id]
        except KeyError as exc:
            raise KeyError(f"unknown item id: {item_id}") from exc

    def exists(self, item_id: str) -> bool:
        return item_id in self._items

    def all(self) -> list[ItemTemplate]:
        return list(self._items.values())

    def by_type(self, item_type: ItemType) -> list[ItemTemplate]:
        return [i for i in self._items.values() if i.item_type == item_type]

    def by_tag(self, tag: str) -> list[ItemTemplate]:
        return [i for i in self._items.values() if tag in i.tags]


@dataclass
class ItemStack:
    item_id: str
    quantity: int = 1


class Inventory:
    """A bag of items plus equipped gear, all referenced by item id."""

    def __init__(self, registry: ItemRegistry) -> None:
        self.registry = registry
        self.stacks: list[ItemStack] = []
        self.equipment: dict[EquipSlot, str] = {}

    # -- queries -------------------------------------------------------------
    def count(self, item_id: str) -> int:
        return sum(s.quantity for s in self.stacks if s.item_id == item_id)

    def has(self, item_id: str, quantity: int = 1) -> bool:
        return self.count(item_id) >= quantity

    def total_weight(self) -> float:
        weight = 0.0
        for s in self.stacks:
            weight += self.registry.get(s.item_id).weight * s.quantity
        for item_id in self.equipment.values():
            weight += self.registry.get(item_id).weight
        return round(weight, 2)

    def items(self) -> list[tuple[ItemTemplate, int]]:
        return [(self.registry.get(s.item_id), s.quantity) for s in self.stacks]

    # -- mutation ------------------------------------------------------------
    def add(self, item_id: str, quantity: int = 1) -> None:
        template = self.registry.get(item_id)
        if template.stackable:
            for s in self.stacks:
                if s.item_id == item_id and s.quantity < template.max_stack:
                    space = template.max_stack - s.quantity
                    moved = min(space, quantity)
                    s.quantity += moved
                    quantity -= moved
                    if quantity <= 0:
                        return
            while quantity > 0:
                moved = min(template.max_stack, quantity)
                self.stacks.append(ItemStack(item_id, moved))
                quantity -= moved
        else:
            for _ in range(quantity):
                self.stacks.append(ItemStack(item_id, 1))

    def remove(self, item_id: str, quantity: int = 1) -> bool:
        if self.count(item_id) < quantity:
            return False
        remaining = quantity
        for s in list(self.stacks):
            if s.item_id != item_id:
                continue
            take = min(s.quantity, remaining)
            s.quantity -= take
            remaining -= take
            if s.quantity <= 0:
                self.stacks.remove(s)
            if remaining <= 0:
                break
        return True

    def equip(self, item_id: str) -> tuple[bool, str]:
        template = self.registry.get(item_id)
        if not template.is_equippable:
            return False, f"{template.name} cannot be equipped."
        if not self.has(item_id):
            return False, f"You do not carry {template.name}."
        slot = template.slot
        assert slot is not None
        previous = self.equipment.get(slot)
        self.remove(item_id, 1)
        if previous:
            self.add(previous, 1)
        self.equipment[slot] = item_id
        msg = f"Equipped {template.name}."
        if previous:
            msg += f" (unequipped {self.registry.get(previous).name})"
        return True, msg

    def unequip(self, slot: EquipSlot) -> tuple[bool, str]:
        item_id = self.equipment.pop(slot, None)
        if not item_id:
            return False, "Nothing equipped there."
        self.add(item_id, 1)
        return True, f"Unequipped {self.registry.get(item_id).name}."

    def equipped_items(self) -> list[ItemTemplate]:
        return [self.registry.get(i) for i in self.equipment.values()]

    def total_attack_bonus(self) -> int:
        return sum(i.attack_bonus for i in self.equipped_items())

    def total_defense_bonus(self) -> int:
        return sum(i.defense_bonus for i in self.equipped_items())

    def main_weapon(self) -> ItemTemplate | None:
        item_id = self.equipment.get(EquipSlot.MAIN_HAND)
        return self.registry.get(item_id) if item_id else None

    # -- persistence ---------------------------------------------------------
    def to_dict(self) -> dict:
        return {
            "stacks": [{"item_id": s.item_id, "quantity": s.quantity} for s in self.stacks],
            "equipment": {slot.value: item_id for slot, item_id in self.equipment.items()},
        }

    @classmethod
    def from_dict(cls, data: dict, registry: ItemRegistry) -> "Inventory":
        inv = cls(registry)
        inv.stacks = [ItemStack(s["item_id"], int(s["quantity"])) for s in data.get("stacks", [])]
        inv.equipment = {EquipSlot(k): v for k, v in data.get("equipment", {}).items()}
        return inv
