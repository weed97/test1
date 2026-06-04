"""Actors of the world: the shared :class:`Actor` base, the :class:`Player`, and
the rich :class:`NPC` with personality, mood, memory, schedules and relationships.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .effects import StatusEffect
from .items import Inventory, ItemRegistry, EquipSlot
from .skills import Ability, AbilityRegistry
from .stats import Attribute, AttributeBlock, DerivedStats


def xp_for_level(level: int) -> int:
    """Total XP required to *reach* a given level."""
    return int(50 * (level - 1) ** 2 + 50 * (level - 1))


class Actor:
    """Base class shared by players and NPCs."""

    def __init__(self, actor_id: str, name: str, *, attrs: AttributeBlock | None = None,
                 level: int = 1, char_class: str = "commoner",
                 registry: ItemRegistry | None = None) -> None:
        self.id = actor_id
        self.name = name
        self.attrs = attrs or AttributeBlock()
        self.level = level
        self.xp = xp_for_level(level)
        self.char_class = char_class
        self.inventory = Inventory(registry) if registry else None
        self.abilities: list[str] = []
        self.cooldowns: dict[str, int] = {}
        self.effects: list[StatusEffect] = []
        self.gold = 0
        self.alive = True

        derived = self.derived_stats()
        self.health = derived.max_health
        self.mana = derived.max_mana
        self.stamina = derived.max_stamina

    # -- derived stats with equipment & effect modifiers ---------------------
    def derived_stats(self) -> DerivedStats:
        armor = self.inventory.total_defense_bonus() if self.inventory else 0
        weapon = self.inventory.total_attack_bonus() if self.inventory else 0
        base = DerivedStats.compute(self.attrs, self.level,
                                    armor_bonus=armor, weapon_bonus=weapon)
        for eff in self.effects:
            base.attack += eff.attack_mod
            base.defense += eff.defense_mod
            base.accuracy += eff.accuracy_mod
            base.evasion += eff.evasion_mod
            base.initiative += eff.initiative_mod
            base.spell_power += eff.spell_power_mod
        base.attack = max(0, base.attack)
        base.defense = max(0, base.defense)
        return base

    # -- resource helpers ----------------------------------------------------
    @property
    def max_health(self) -> int:
        return self.derived_stats().max_health

    @property
    def max_mana(self) -> int:
        return self.derived_stats().max_mana

    @property
    def max_stamina(self) -> int:
        return self.derived_stats().max_stamina

    def clamp_resources(self) -> None:
        self.health = max(0, min(self.health, self.max_health))
        self.mana = max(0, min(self.mana, self.max_mana))
        self.stamina = max(0, min(self.stamina, self.max_stamina))
        if self.health <= 0:
            self.alive = False

    def heal(self, amount: int) -> int:
        before = self.health
        self.health = min(self.max_health, self.health + max(0, amount))
        return self.health - before

    def take_damage(self, amount: int) -> int:
        amount = max(0, amount)
        self.health -= amount
        if self.health <= 0:
            self.health = 0
            self.alive = False
        return amount

    def restore_mana(self, amount: int) -> int:
        before = self.mana
        self.mana = min(self.max_mana, self.mana + max(0, amount))
        return self.mana - before

    def restore_stamina(self, amount: int) -> int:
        before = self.stamina
        self.stamina = min(self.max_stamina, self.stamina + max(0, amount))
        return self.stamina - before

    def full_restore(self) -> None:
        self.health = self.max_health
        self.mana = self.max_mana
        self.stamina = self.max_stamina
        self.alive = True
        self.effects = [e for e in self.effects if e.good]

    # -- effects -------------------------------------------------------------
    def add_effect(self, effect: StatusEffect) -> None:
        for existing in self.effects:
            if existing.name == effect.name:
                existing.duration = max(existing.duration, effect.duration)
                return
        self.effects.append(effect)

    def has_effect(self, name: str) -> bool:
        return any(e.name == name for e in self.effects)

    def is_stunned(self) -> bool:
        return any(e.skip_turn for e in self.effects)

    def tick_effects(self) -> list[str]:
        """Apply per-turn effect deltas and expire finished effects."""
        log: list[str] = []
        for eff in list(self.effects):
            if eff.per_turn_damage:
                self.take_damage(eff.per_turn_damage)
                log.append(f"{self.name} suffers {eff.per_turn_damage} {eff.damage_type} "
                           f"damage from {eff.name}.")
            if eff.per_turn_heal:
                healed = self.heal(eff.per_turn_heal)
                if healed:
                    log.append(f"{self.name} recovers {healed} HP from {eff.name}.")
            eff.duration -= 1
            if eff.duration <= 0:
                self.effects.remove(eff)
                log.append(f"{eff.name} fades from {self.name}.")
        self.clamp_resources()
        return log

    def tick_cooldowns(self) -> None:
        for key in list(self.cooldowns):
            self.cooldowns[key] -= 1
            if self.cooldowns[key] <= 0:
                del self.cooldowns[key]

    def can_use(self, ability: Ability) -> bool:
        if ability.id in self.cooldowns:
            return False
        if ability.kind.value == "spell":
            return self.mana >= ability.cost
        return self.stamina >= ability.cost

    def spend_for(self, ability: Ability) -> None:
        if ability.kind.value == "spell":
            self.mana -= ability.cost
        else:
            self.stamina -= ability.cost
        if ability.cooldown:
            self.cooldowns[ability.id] = ability.cooldown

    # -- progression ---------------------------------------------------------
    def add_xp(self, amount: int) -> list[str]:
        messages: list[str] = []
        self.xp += max(0, amount)
        while self.xp >= xp_for_level(self.level + 1):
            self.level += 1
            self.attrs.modify(Attribute.CONSTITUTION, 1)
            messages.append(f"{self.name} reaches level {self.level}!")
            self.full_restore()
        return messages

    def learn(self, ability_id: str) -> None:
        if ability_id not in self.abilities:
            self.abilities.append(ability_id)

    # -- persistence ---------------------------------------------------------
    def base_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "attrs": self.attrs.to_dict(),
            "level": self.level, "xp": self.xp, "char_class": self.char_class,
            "abilities": list(self.abilities), "cooldowns": dict(self.cooldowns),
            "effects": [e.to_dict() for e in self.effects], "gold": self.gold,
            "alive": self.alive, "health": self.health, "mana": self.mana,
            "stamina": self.stamina,
            "inventory": self.inventory.to_dict() if self.inventory else None,
        }

    def load_base(self, data: dict, registry: ItemRegistry) -> None:
        self.attrs = AttributeBlock.from_dict(data["attrs"])
        self.level = int(data["level"])
        self.xp = int(data["xp"])
        self.char_class = data["char_class"]
        self.abilities = list(data.get("abilities", []))
        self.cooldowns = dict(data.get("cooldowns", {}))
        self.effects = [StatusEffect.from_dict(e) for e in data.get("effects", [])]
        self.gold = int(data.get("gold", 0))
        self.alive = bool(data.get("alive", True))
        if data.get("inventory") is not None:
            self.inventory = Inventory.from_dict(data["inventory"], registry)
        self.health = int(data.get("health", self.max_health))
        self.mana = int(data.get("mana", self.max_mana))
        self.stamina = int(data.get("stamina", self.max_stamina))


class Player(Actor):
    def __init__(self, actor_id: str, name: str, registry: ItemRegistry, **kwargs) -> None:
        super().__init__(actor_id, name, registry=registry, **kwargs)
        self.location_id: str = ""
        self.discovered_locations: set[str] = set()
        self.reputation: dict[str, int] = {}
        self.active_quests: list[str] = []
        self.completed_quests: list[str] = []
        self.quest_progress: dict[str, dict] = {}
        self.journal: list[str] = []
        self.kills: dict[str, int] = {}
        self.professions: dict[str, int] = {}
        self.looted_pois: set[str] = set()
        self.play_title: str = "Wanderer"

    def reputation_with(self, faction_id: str) -> int:
        return self.reputation.get(faction_id, 0)

    def adjust_reputation(self, faction_id: str, delta: int) -> None:
        self.reputation[faction_id] = self.reputation.get(faction_id, 0) + delta

    def to_dict(self) -> dict:
        data = self.base_dict()
        data.update({
            "kind": "player",
            "location_id": self.location_id,
            "discovered_locations": sorted(self.discovered_locations),
            "reputation": dict(self.reputation),
            "active_quests": list(self.active_quests),
            "completed_quests": list(self.completed_quests),
            "quest_progress": self.quest_progress,
            "journal": list(self.journal),
            "kills": dict(self.kills),
            "professions": dict(self.professions),
            "looted_pois": sorted(self.looted_pois),
            "play_title": self.play_title,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict, registry: ItemRegistry) -> "Player":
        p = cls(data["id"], data["name"], registry)
        p.load_base(data, registry)
        p.location_id = data.get("location_id", "")
        p.discovered_locations = set(data.get("discovered_locations", []))
        p.reputation = dict(data.get("reputation", {}))
        p.active_quests = list(data.get("active_quests", []))
        p.completed_quests = list(data.get("completed_quests", []))
        p.quest_progress = data.get("quest_progress", {})
        p.journal = list(data.get("journal", []))
        p.kills = dict(data.get("kills", {}))
        p.professions = dict(data.get("professions", {}))
        p.looted_pois = set(data.get("looted_pois", []))
        p.play_title = data.get("play_title", "Wanderer")
        return p


# --------------------------------------------------------------------------- #
#  NPC personality / mood / memory                                            #
# --------------------------------------------------------------------------- #

class Disposition(str, Enum):
    HOSTILE = "hostile"
    WARY = "wary"
    NEUTRAL = "neutral"
    FRIENDLY = "friendly"
    DEVOTED = "devoted"

    @classmethod
    def from_score(cls, score: int) -> "Disposition":
        if score <= -50:
            return cls.HOSTILE
        if score < -10:
            return cls.WARY
        if score < 25:
            return cls.NEUTRAL
        if score < 75:
            return cls.FRIENDLY
        return cls.DEVOTED


class Mood(str, Enum):
    CONTENT = "content"
    HAPPY = "happy"
    CHEERFUL = "cheerful"
    GRUMPY = "grumpy"
    ANGRY = "angry"
    FEARFUL = "fearful"
    SORROWFUL = "sorrowful"
    DRUNK = "drunk"
    TIRED = "tired"

    @classmethod
    def from_score(cls, score: int) -> "Mood":
        if score <= -60:
            return cls.ANGRY
        if score <= -25:
            return cls.GRUMPY
        if score < 25:
            return cls.CONTENT
        if score < 60:
            return cls.HAPPY
        return cls.CHEERFUL


@dataclass
class Personality:
    """Five-axis personality model that biases dialogue, mood and behaviour."""

    warmth: int = 50        # cold(0)        .. warm(100)
    bravery: int = 50       # cowardly       .. fearless
    honesty: int = 50       # deceitful      .. honest
    greed: int = 50         # generous       .. avaricious
    curiosity: int = 50     # incurious      .. inquisitive
    traits: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {"warmth": self.warmth, "bravery": self.bravery,
                "honesty": self.honesty, "greed": self.greed,
                "curiosity": self.curiosity, "traits": list(self.traits)}

    @classmethod
    def from_dict(cls, data: dict) -> "Personality":
        return cls(
            warmth=int(data.get("warmth", 50)),
            bravery=int(data.get("bravery", 50)),
            honesty=int(data.get("honesty", 50)),
            greed=int(data.get("greed", 50)),
            curiosity=int(data.get("curiosity", 50)),
            traits=tuple(data.get("traits", [])),
        )


@dataclass
class MemoryEntry:
    day: int
    text: str
    weight: int = 1   # how strongly it colours future interactions


class NPC(Actor):
    def __init__(self, actor_id: str, name: str, registry: ItemRegistry,
                 *, role: str = "villager", faction: str = "",
                 home_location: str = "", **kwargs) -> None:
        super().__init__(actor_id, name, registry=registry, **kwargs)
        self.role = role
        self.faction = faction
        self.home_location = home_location
        self.current_location = home_location
        self.personality = Personality()
        self.relationship = 0       # toward the player, -100..100
        self.mood_score = 0         # -100..100
        self.memory: list[MemoryEntry] = []
        self.schedule: dict[str, str] = {}   # time_of_day -> location_id
        self.dialogue_id: str = ""
        self.greeting: str = ""
        self.is_merchant: bool = False
        self.shop_inventory: list[str] = []
        self.loot_table: list[tuple[str, float]] = []
        self.xp_reward: int = 0
        self.hostile_by_default: bool = False
        self.known_rumors: list[str] = []
        self.quests_offered: list[str] = []
        self.titles: tuple[str, ...] = ()
        self.species: str = "human"

    # -- social --------------------------------------------------------------
    @property
    def disposition(self) -> Disposition:
        if self.hostile_by_default and self.relationship < 25:
            return Disposition.HOSTILE
        return Disposition.from_score(self.relationship)

    @property
    def mood(self) -> Mood:
        if self.has_effect("well_fed"):
            return Mood.HAPPY
        return Mood.from_score(self.mood_score)

    def adjust_relationship(self, delta: int) -> None:
        self.relationship = max(-100, min(100, self.relationship + delta))

    def adjust_mood(self, delta: int) -> None:
        self.mood_score = max(-100, min(100, self.mood_score + delta))

    def remember(self, day: int, text: str, weight: int = 1) -> None:
        self.memory.append(MemoryEntry(day, text, weight))
        if len(self.memory) > 40:
            self.memory.pop(0)

    def recent_memories(self, limit: int = 3) -> list[MemoryEntry]:
        return sorted(self.memory, key=lambda m: (m.weight, m.day), reverse=True)[:limit]

    def location_for(self, time_of_day: str) -> str:
        return self.schedule.get(time_of_day, self.home_location)

    # -- persistence ---------------------------------------------------------
    def to_dict(self) -> dict:
        data = self.base_dict()
        data.update({
            "kind": "npc",
            "role": self.role, "faction": self.faction,
            "home_location": self.home_location,
            "current_location": self.current_location,
            "personality": self.personality.to_dict(),
            "relationship": self.relationship, "mood_score": self.mood_score,
            "memory": [{"day": m.day, "text": m.text, "weight": m.weight} for m in self.memory],
            "schedule": dict(self.schedule),
            "dialogue_id": self.dialogue_id, "greeting": self.greeting,
            "is_merchant": self.is_merchant, "shop_inventory": list(self.shop_inventory),
            "loot_table": [list(x) for x in self.loot_table],
            "xp_reward": self.xp_reward, "hostile_by_default": self.hostile_by_default,
            "known_rumors": list(self.known_rumors),
            "quests_offered": list(self.quests_offered),
            "titles": list(self.titles), "species": self.species,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict, registry: ItemRegistry) -> "NPC":
        npc = cls(data["id"], data["name"], registry,
                  role=data.get("role", "villager"),
                  faction=data.get("faction", ""),
                  home_location=data.get("home_location", ""))
        npc.load_base(data, registry)
        npc.current_location = data.get("current_location", npc.home_location)
        npc.personality = Personality.from_dict(data.get("personality", {}))
        npc.relationship = int(data.get("relationship", 0))
        npc.mood_score = int(data.get("mood_score", 0))
        npc.memory = [MemoryEntry(m["day"], m["text"], m.get("weight", 1))
                      for m in data.get("memory", [])]
        npc.schedule = dict(data.get("schedule", {}))
        npc.dialogue_id = data.get("dialogue_id", "")
        npc.greeting = data.get("greeting", "")
        npc.is_merchant = bool(data.get("is_merchant", False))
        npc.shop_inventory = list(data.get("shop_inventory", []))
        npc.loot_table = [tuple(x) for x in data.get("loot_table", [])]
        npc.xp_reward = int(data.get("xp_reward", 0))
        npc.hostile_by_default = bool(data.get("hostile_by_default", False))
        npc.known_rumors = list(data.get("known_rumors", []))
        npc.quests_offered = list(data.get("quests_offered", []))
        npc.titles = tuple(data.get("titles", []))
        npc.species = data.get("species", "human")
        return npc
