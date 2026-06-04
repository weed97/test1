"""Character classes, combat skills and magic spells.

A :class:`CharacterClass` defines starting attribute biases, growth and a starting
kit of abilities.  An :class:`Ability` is the unified representation of both a
martial *skill* and an arcane *spell*; the distinction is the resource it consumes
(stamina vs mana) and its ``school``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .stats import Attribute


class AbilityKind(str, Enum):
    SKILL = "skill"     # consumes stamina
    SPELL = "spell"     # consumes mana


class TargetMode(str, Enum):
    ENEMY = "enemy"
    SELF = "self"
    ALLY = "ally"
    AREA = "area"


@dataclass(frozen=True)
class Ability:
    id: str
    name: str
    kind: AbilityKind
    description: str = ""
    cost: int = 0                       # stamina (skill) or mana (spell)
    cooldown: int = 0                   # turns
    power: int = 0                      # base magnitude before scaling
    scaling_attr: Attribute = Attribute.STRENGTH
    scaling_factor: float = 1.0
    damage_type: str = "physical"
    target: TargetMode = TargetMode.ENEMY
    school: str = "martial"
    heal: int = 0
    shield: int = 0
    effect: str | None = None           # named status effect
    effect_duration: int = 0
    aoe: bool = False
    required_level: int = 1

    @property
    def is_offensive(self) -> bool:
        return self.target in (TargetMode.ENEMY, TargetMode.AREA) and self.heal == 0

    def describe(self) -> str:
        bits = [f"{self.name} ({self.kind.value})"]
        if self.cost:
            res = "mana" if self.kind is AbilityKind.SPELL else "stamina"
            bits.append(f"{self.cost} {res}")
        if self.power:
            bits.append(f"power {self.power} ({self.scaling_attr.value[:3]})")
        if self.heal:
            bits.append(f"heal {self.heal}")
        if self.shield:
            bits.append(f"shield {self.shield}")
        if self.effect:
            bits.append(f"applies {self.effect}")
        if self.cooldown:
            bits.append(f"cd {self.cooldown}")
        return " | ".join(bits)


class AbilityRegistry:
    def __init__(self) -> None:
        self._abilities: dict[str, Ability] = {}

    def register(self, ability: Ability) -> Ability:
        if ability.id in self._abilities:
            raise ValueError(f"duplicate ability id: {ability.id}")
        self._abilities[ability.id] = ability
        return ability

    def get(self, ability_id: str) -> Ability:
        try:
            return self._abilities[ability_id]
        except KeyError as exc:
            raise KeyError(f"unknown ability id: {ability_id}") from exc

    def exists(self, ability_id: str) -> bool:
        return ability_id in self._abilities

    def all(self) -> list[Ability]:
        return list(self._abilities.values())


@dataclass(frozen=True)
class CharacterClass:
    id: str
    name: str
    description: str
    primary_attr: Attribute
    secondary_attr: Attribute
    attribute_bias: dict[str, int] = field(default_factory=dict)
    starting_abilities: tuple[str, ...] = ()
    health_per_level: int = 8
    mana_per_level: int = 4
    starting_items: tuple[str, ...] = ()
    hit_die: int = 8

    def describe(self) -> str:
        return (f"{self.name} — {self.description}\n"
                f"  Primary: {self.primary_attr.value}, "
                f"Secondary: {self.secondary_attr.value}")


class ClassRegistry:
    def __init__(self) -> None:
        self._classes: dict[str, CharacterClass] = {}

    def register(self, cls: CharacterClass) -> CharacterClass:
        if cls.id in self._classes:
            raise ValueError(f"duplicate class id: {cls.id}")
        self._classes[cls.id] = cls
        return cls

    def get(self, class_id: str) -> CharacterClass:
        try:
            return self._classes[class_id]
        except KeyError as exc:
            raise KeyError(f"unknown class id: {class_id}") from exc

    def all(self) -> list[CharacterClass]:
        return list(self._classes.values())
