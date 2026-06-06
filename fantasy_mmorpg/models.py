"""Core data models for the fantasy simulator."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


Stats = dict[str, int]


@dataclass(frozen=True)
class Item:
    id: str
    name: str
    type: str
    description: str
    value: int
    rarity: str = "common"
    stats: Stats = field(default_factory=dict)
    effects: Stats = field(default_factory=dict)
    equip_slot: str | None = None
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class EnemyTemplate:
    id: str
    name: str
    description: str
    level: int
    max_hp: int
    attack: int
    defense: int
    xp_reward: int
    faction: str
    loot_table: tuple[tuple[str, float], ...] = ()
    abilities: tuple[str, ...] = ()
    opening_line: str = ""


@dataclass
class Enemy:
    template_id: str
    name: str
    description: str
    level: int
    hp: int
    max_hp: int
    attack: int
    defense: int
    xp_reward: int
    faction: str
    loot_table: tuple[tuple[str, float], ...] = ()
    abilities: tuple[str, ...] = ()

    @classmethod
    def from_template(cls, template: EnemyTemplate) -> "Enemy":
        return cls(
            template_id=template.id,
            name=template.name,
            description=template.description,
            level=template.level,
            hp=template.max_hp,
            max_hp=template.max_hp,
            attack=template.attack,
            defense=template.defense,
            xp_reward=template.xp_reward,
            faction=template.faction,
            loot_table=template.loot_table,
            abilities=template.abilities,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Enemy":
        data = dict(data)
        data["loot_table"] = tuple(tuple(row) for row in data.get("loot_table", ()))
        data["abilities"] = tuple(data.get("abilities", ()))
        return cls(**data)


@dataclass(frozen=True)
class NPC:
    id: str
    name: str
    title: str
    faction: str
    personality: str
    greeting: str
    topics: dict[str, str]
    quest_ids: tuple[str, ...] = ()
    shop_inventory: tuple[str, ...] = ()
    services: tuple[str, ...] = ()

    @property
    def display_name(self) -> str:
        return f"{self.name}, {self.title}"


@dataclass(frozen=True)
class Zone:
    id: str
    name: str
    region: str
    description: str
    danger_level: int
    exits: dict[str, str]
    npc_ids: tuple[str, ...] = ()
    encounters: tuple[tuple[str, int], ...] = ()
    resources: tuple[str, ...] = ()
    secrets: tuple[str, ...] = ()
    shop_ids: tuple[str, ...] = ()
    faction: str = "Hearthfolk"
    ambience: tuple[str, ...] = ()
    rest_allowed: bool = False


@dataclass(frozen=True)
class Quest:
    id: str
    title: str
    giver: str
    description: str
    objectives: tuple[dict[str, Any], ...]
    rewards: dict[str, Any]
    completion_text: str
    faction: str
    required_level: int = 1
    prerequisites: tuple[str, ...] = ()


@dataclass(frozen=True)
class Recipe:
    id: str
    name: str
    ingredients: dict[str, int]
    result_item: str
    result_count: int = 1
    required_tag: str | None = None


@dataclass
class Player:
    name: str
    ancestry: str
    class_name: str
    background: str
    level: int
    xp: int
    gold: int
    location: str
    attributes: Stats
    hp: int
    max_hp: int
    mana: int
    max_mana: int
    inventory: dict[str, int] = field(default_factory=dict)
    equipment: dict[str, str] = field(default_factory=dict)
    active_quests: dict[str, str] = field(default_factory=dict)
    completed_quests: list[str] = field(default_factory=list)
    reputation: dict[str, int] = field(default_factory=dict)
    world_flags: dict[str, Any] = field(default_factory=dict)
    killed: dict[str, int] = field(default_factory=dict)
    explored: list[str] = field(default_factory=list)
    talked_to: list[str] = field(default_factory=list)
    discoveries: list[str] = field(default_factory=list)
    known_lore: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Player":
        return cls(**data)

    def add_item(self, item_id: str, count: int = 1) -> None:
        if count <= 0:
            return
        self.inventory[item_id] = self.inventory.get(item_id, 0) + count

    def remove_item(self, item_id: str, count: int = 1) -> bool:
        if self.inventory.get(item_id, 0) < count:
            return False
        self.inventory[item_id] -= count
        if self.inventory[item_id] <= 0:
            del self.inventory[item_id]
        return True

    def has_items(self, item_id: str, count: int = 1) -> bool:
        return self.inventory.get(item_id, 0) >= count


@dataclass
class WorldState:
    day: int = 1
    hour: int = 8
    turn: int = 0
    active_event: str | None = None
    event_duration: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WorldState":
        return cls(**data)
