from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass(slots=True)
class Item:
    key: str
    name: str
    category: str
    base_price: int
    description: str


@dataclass(slots=True)
class Market:
    price_modifiers: Dict[str, float] = field(default_factory=dict)

    def get_price(self, item: Item) -> int:
        modifier = self.price_modifiers.get(item.key, 1.0)
        return max(1, int(item.base_price * modifier))

    def fluctuate(self, item_key: str, delta: float) -> None:
        current = self.price_modifiers.get(item_key, 1.0)
        updated = current + delta
        self.price_modifiers[item_key] = min(2.2, max(0.45, round(updated, 2)))


@dataclass(slots=True)
class Region:
    key: str
    name: str
    biome: str
    danger: int
    prosperity: int
    resources: List[str]
    neighbors: List[str]
    market: Market = field(default_factory=Market)


@dataclass(slots=True)
class Faction:
    key: str
    name: str
    doctrine: str
    military: int
    wealth: int
    influence: int
    relations: Dict[str, int] = field(default_factory=dict)


@dataclass(slots=True)
class NPC:
    key: str
    name: str
    role: str
    region_key: str
    faction_key: str
    personality: Dict[str, int]
    disposition: int = 0
    memory: List[str] = field(default_factory=list)
    dialogue_tags: List[str] = field(default_factory=list)

    def remember(self, note: str) -> None:
        self.memory.append(note)
        if len(self.memory) > 8:
            self.memory = self.memory[-8:]


@dataclass(slots=True)
class QuestObjective:
    action: str
    target: str
    required: int
    progress: int = 0

    def is_complete(self) -> bool:
        return self.progress >= self.required


@dataclass(slots=True)
class Quest:
    key: str
    title: str
    giver_npc_key: str
    region_key: str
    description: str
    reward_gold: int
    reward_reputation: Dict[str, int]
    objective: QuestObjective
    status: str = "available"


@dataclass(slots=True)
class Player:
    name: str
    region_key: str
    gold: int
    health: int
    max_health: int
    level: int
    experience: int
    inventory: Dict[str, int] = field(default_factory=dict)
    reputation: Dict[str, int] = field(default_factory=dict)

    def add_item(self, item_key: str, amount: int = 1) -> None:
        self.inventory[item_key] = self.inventory.get(item_key, 0) + amount
        if self.inventory[item_key] <= 0:
            self.inventory.pop(item_key, None)

    def has_item(self, item_key: str, amount: int = 1) -> bool:
        return self.inventory.get(item_key, 0) >= amount

    def gain_experience(self, amount: int) -> bool:
        self.experience += amount
        leveled = False
        while self.experience >= self.level * 120:
            self.experience -= self.level * 120
            self.level += 1
            self.max_health += 8
            self.health = self.max_health
            leveled = True
        return leveled


@dataclass(slots=True)
class WorldState:
    day: int
    weather: str
    regions: Dict[str, Region]
    factions: Dict[str, Faction]
    npcs: Dict[str, NPC]
    quests: Dict[str, Quest]
    events: List[str] = field(default_factory=list)

    def log_event(self, message: str) -> None:
        self.events.append(message)
        if len(self.events) > 120:
            self.events = self.events[-120:]
