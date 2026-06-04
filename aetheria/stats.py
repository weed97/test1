"""Character attributes and the derived combat statistics built from them.

Every actor (player or NPC) has six primary attributes.  From those we derive the
secondary statistics that the combat, dialogue and economy systems consume.  The
relationships are intentionally transparent so designers can reason about balance.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
from enum import Enum


class Attribute(str, Enum):
    STRENGTH = "strength"        # melee damage, carry weight
    DEXTERITY = "dexterity"      # accuracy, dodge, initiative, ranged damage
    CONSTITUTION = "constitution"  # health, stamina, resilience
    INTELLIGENCE = "intelligence"  # spell power, mana
    WISDOM = "wisdom"            # perception, healing, mana regen
    CHARISMA = "charisma"        # persuasion, prices, leadership


@dataclass
class AttributeBlock:
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10

    def get(self, attr: Attribute | str) -> int:
        key = attr.value if isinstance(attr, Attribute) else attr
        return int(getattr(self, key))

    def set(self, attr: Attribute | str, value: int) -> None:
        key = attr.value if isinstance(attr, Attribute) else attr
        setattr(self, key, int(value))

    def modify(self, attr: Attribute | str, delta: int) -> None:
        self.set(attr, self.get(attr) + delta)

    def modifier(self, attr: Attribute | str) -> int:
        """D20-style modifier: (score - 10) // 2."""
        return (self.get(attr) - 10) // 2

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AttributeBlock":
        return cls(**{k: int(v) for k, v in data.items() if k in cls.__annotations__})


@dataclass
class DerivedStats:
    """Secondary statistics computed from attributes and level."""

    max_health: int
    max_mana: int
    max_stamina: int
    attack: int
    spell_power: int
    defense: int
    accuracy: int
    evasion: int
    initiative: int
    crit_chance: float
    carry_capacity: int

    @classmethod
    def compute(cls, attrs: AttributeBlock, level: int,
                armor_bonus: int = 0, weapon_bonus: int = 0) -> "DerivedStats":
        con = attrs.modifier(Attribute.CONSTITUTION)
        dex = attrs.modifier(Attribute.DEXTERITY)
        intel = attrs.modifier(Attribute.INTELLIGENCE)
        wis = attrs.modifier(Attribute.WISDOM)
        strn = attrs.modifier(Attribute.STRENGTH)
        return cls(
            max_health=max(1, 20 + level * 8 + con * 6),
            max_mana=max(0, 10 + level * 4 + intel * 5 + wis * 2),
            max_stamina=max(1, 15 + level * 3 + con * 3),
            attack=max(0, 3 + strn * 2 + weapon_bonus + level),
            spell_power=max(0, 2 + intel * 2 + wis),
            defense=max(0, armor_bonus + con),
            accuracy=max(1, 72 + dex * 3 + level),
            evasion=max(0, 5 + dex * 2),
            initiative=max(0, 10 + dex * 2),
            crit_chance=min(0.6, 0.05 + dex * 0.01),
            carry_capacity=max(10, 30 + strn * 5),
        )

    def to_dict(self) -> dict:
        return asdict(self)
