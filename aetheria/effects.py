"""Status effects (buffs, debuffs, damage-over-time) shared by combat and items.

Effects are data-driven: a :class:`StatusEffect` carries a small bundle of numeric
modifiers plus per-turn hooks.  Actors keep a list of active effects which the
combat loop ticks each round.
"""

from __future__ import annotations

from dataclasses import dataclass, field


# Catalogue of effect templates keyed by name.  Designers add to this freely.
EFFECT_LIBRARY: dict[str, dict] = {
    "poison": {"per_turn_damage": 4, "damage_type": "poison", "duration": 3,
               "good": False, "desc": "Venom courses through the veins."},
    "burning": {"per_turn_damage": 6, "damage_type": "fire", "duration": 2,
                "good": False, "desc": "Flames lick at flesh and cloth."},
    "bleeding": {"per_turn_damage": 5, "damage_type": "physical", "duration": 3,
                 "good": False, "desc": "An open wound weeps steadily."},
    "frostbite": {"per_turn_damage": 3, "damage_type": "frost", "duration": 2,
                  "evasion_mod": -4, "good": False, "desc": "Limbs grow numb and slow."},
    "stunned": {"duration": 1, "skip_turn": True, "good": False,
                "desc": "Reeling, unable to act."},
    "regeneration": {"per_turn_heal": 6, "duration": 3, "good": True,
                     "desc": "Vitality knits wounds closed."},
    "blessed": {"attack_mod": 4, "accuracy_mod": 8, "duration": 3, "good": True,
                "desc": "A divine favour steadies the hand."},
    "shielded": {"defense_mod": 6, "duration": 3, "good": True,
                 "desc": "A ward of force turns aside blows."},
    "enraged": {"attack_mod": 6, "defense_mod": -3, "duration": 3, "good": True,
                "desc": "Fury lends strength at the cost of caution."},
    "weakened": {"attack_mod": -5, "duration": 3, "good": False,
                 "desc": "Muscles refuse to answer."},
    "hasted": {"evasion_mod": 6, "initiative_mod": 8, "duration": 3, "good": True,
               "desc": "The world seems to slow around them."},
    "focused": {"spell_power_mod": 5, "duration": 3, "good": True,
                "desc": "The mind is sharp as a blade."},
    "well_fed": {"defense_mod": 2, "per_turn_heal": 2, "duration": 5, "good": True,
                 "desc": "A hearty meal restores resolve."},
}


@dataclass
class StatusEffect:
    name: str
    duration: int
    per_turn_damage: int = 0
    per_turn_heal: int = 0
    damage_type: str = "physical"
    attack_mod: int = 0
    defense_mod: int = 0
    accuracy_mod: int = 0
    evasion_mod: int = 0
    initiative_mod: int = 0
    spell_power_mod: int = 0
    skip_turn: bool = False
    good: bool = True
    desc: str = ""

    @classmethod
    def create(cls, name: str, duration: int | None = None) -> "StatusEffect":
        template = EFFECT_LIBRARY.get(name, {})
        data = dict(template)
        data.pop("desc", None)
        eff = cls(
            name=name,
            duration=duration if duration is not None else int(template.get("duration", 1)),
            per_turn_damage=int(template.get("per_turn_damage", 0)),
            per_turn_heal=int(template.get("per_turn_heal", 0)),
            damage_type=str(template.get("damage_type", "physical")),
            attack_mod=int(template.get("attack_mod", 0)),
            defense_mod=int(template.get("defense_mod", 0)),
            accuracy_mod=int(template.get("accuracy_mod", 0)),
            evasion_mod=int(template.get("evasion_mod", 0)),
            initiative_mod=int(template.get("initiative_mod", 0)),
            spell_power_mod=int(template.get("spell_power_mod", 0)),
            skip_turn=bool(template.get("skip_turn", False)),
            good=bool(template.get("good", True)),
            desc=str(template.get("desc", "")),
        )
        return eff

    def to_dict(self) -> dict:
        return {
            "name": self.name, "duration": self.duration,
            "per_turn_damage": self.per_turn_damage, "per_turn_heal": self.per_turn_heal,
            "damage_type": self.damage_type, "attack_mod": self.attack_mod,
            "defense_mod": self.defense_mod, "accuracy_mod": self.accuracy_mod,
            "evasion_mod": self.evasion_mod, "initiative_mod": self.initiative_mod,
            "spell_power_mod": self.spell_power_mod, "skip_turn": self.skip_turn,
            "good": self.good, "desc": self.desc,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "StatusEffect":
        return cls(**data)
