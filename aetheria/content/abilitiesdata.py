"""The ability & spell book: martial skills (stamina) and arcane spells (mana)."""

from __future__ import annotations

from ..skills import Ability, AbilityKind, TargetMode
from ..state import World
from ..stats import Attribute


def register_abilities(world: World) -> None:
    reg = world.abilities
    add = reg.register

    # ---- martial skills (stamina) -----------------------------------------
    add(Ability("power_strike", "Power Strike", AbilityKind.SKILL,
                "A mighty overhead blow.", cost=8, power=6,
                scaling_attr=Attribute.STRENGTH, scaling_factor=1.5,
                school="martial", required_level=1))
    add(Ability("cleave", "Cleave", AbilityKind.SKILL,
                "A sweeping strike that hits all foes.", cost=14, power=4,
                scaling_attr=Attribute.STRENGTH, scaling_factor=1.0, aoe=True,
                target=TargetMode.AREA, school="martial", required_level=3))
    add(Ability("shield_bash", "Shield Bash", AbilityKind.SKILL,
                "Slam your shield to stun a foe.", cost=10, power=3,
                scaling_attr=Attribute.STRENGTH, effect="stunned", effect_duration=1,
                school="martial", cooldown=3, required_level=2))
    add(Ability("rapid_shot", "Rapid Shot", AbilityKind.SKILL,
                "Loose two arrows in a heartbeat.", cost=9, power=5,
                scaling_attr=Attribute.DEXTERITY, scaling_factor=1.4,
                school="martial", required_level=1))
    add(Ability("backstab", "Backstab", AbilityKind.SKILL,
                "A vicious strike that causes bleeding.", cost=10, power=7,
                scaling_attr=Attribute.DEXTERITY, scaling_factor=1.6, effect="bleeding",
                effect_duration=3, school="martial", required_level=2))
    add(Ability("second_wind", "Second Wind", AbilityKind.SKILL,
                "Catch your breath and recover.", cost=6, heal=18,
                target=TargetMode.SELF, scaling_attr=Attribute.CONSTITUTION,
                school="martial", cooldown=4, required_level=1))
    add(Ability("whirlwind", "Whirlwind", AbilityKind.SKILL,
                "Spin with blade extended, striking all around.", cost=20, power=8,
                scaling_attr=Attribute.STRENGTH, scaling_factor=1.2, aoe=True,
                target=TargetMode.AREA, school="martial", cooldown=3, required_level=5))

    # ---- arcane spells (mana) ---------------------------------------------
    add(Ability("firebolt", "Firebolt", AbilityKind.SPELL,
                "A dart of flame.", cost=8, power=8, damage_type="fire",
                scaling_attr=Attribute.INTELLIGENCE, scaling_factor=1.3,
                school="evocation", required_level=1))
    add(Ability("frost_lance", "Frost Lance", AbilityKind.SPELL,
                "A spear of ice that chills the marrow.", cost=10, power=7,
                damage_type="frost", effect="frostbite", effect_duration=2,
                scaling_attr=Attribute.INTELLIGENCE, scaling_factor=1.2,
                school="evocation", required_level=2))
    add(Ability("lightning", "Chain Lightning", AbilityKind.SPELL,
                "Arcing lightning that leaps between foes.", cost=18, power=9,
                damage_type="lightning", aoe=True, target=TargetMode.AREA,
                scaling_attr=Attribute.INTELLIGENCE, scaling_factor=1.1,
                school="evocation", cooldown=2, required_level=4))
    add(Ability("poison_dart", "Poison Dart", AbilityKind.SPELL,
                "A venomous bolt.", cost=7, power=4, damage_type="poison",
                effect="poison", effect_duration=3,
                scaling_attr=Attribute.INTELLIGENCE, school="conjuration",
                required_level=1))
    add(Ability("heal", "Heal", AbilityKind.SPELL,
                "Knit wounds with restorative light.", cost=9, heal=22,
                target=TargetMode.ALLY, scaling_attr=Attribute.WISDOM,
                school="restoration", required_level=1))
    add(Ability("greater_heal", "Greater Heal", AbilityKind.SPELL,
                "A surge of life-giving energy.", cost=18, heal=50,
                target=TargetMode.ALLY, scaling_attr=Attribute.WISDOM,
                school="restoration", cooldown=2, required_level=4))
    add(Ability("arcane_shield", "Arcane Shield", AbilityKind.SPELL,
                "A ward of force.", cost=10, shield=8, target=TargetMode.SELF,
                effect="shielded", effect_duration=3, school="abjuration",
                cooldown=3, required_level=2))
    add(Ability("ice_armor", "Ice Armor", AbilityKind.SPELL,
                "Sheathe yourself in protective frost.", cost=12, shield=6,
                target=TargetMode.SELF, effect="shielded", effect_duration=4,
                school="abjuration", cooldown=3, required_level=3))
    add(Ability("holy_smite", "Holy Smite", AbilityKind.SPELL,
                "Call down radiant judgement.", cost=14, power=10, damage_type="holy",
                scaling_attr=Attribute.WISDOM, scaling_factor=1.3, school="holy",
                cooldown=2, required_level=3))
    add(Ability("bless", "Bless", AbilityKind.SPELL,
                "Bestow divine favour upon an ally.", cost=8, effect="blessed",
                effect_duration=3, target=TargetMode.ALLY, school="holy",
                required_level=2))
    add(Ability("meteor", "Meteor", AbilityKind.SPELL,
                "Call a burning rock from the heavens.", cost=30, power=18,
                damage_type="fire", aoe=True, target=TargetMode.AREA, effect="burning",
                effect_duration=2, scaling_attr=Attribute.INTELLIGENCE,
                scaling_factor=1.4, school="evocation", cooldown=4, required_level=7))

    # ---- monster abilities -------------------------------------------------
    add(Ability("bite", "Savage Bite", AbilityKind.SKILL, "A tearing bite.",
                cost=0, power=4, scaling_attr=Attribute.STRENGTH, school="natural"))
    add(Ability("venom_bite", "Venomous Bite", AbilityKind.SKILL, "A poisoned bite.",
                cost=0, power=3, effect="poison", effect_duration=3,
                scaling_attr=Attribute.STRENGTH, school="natural"))
    add(Ability("fire_breath", "Fire Breath", AbilityKind.SKILL,
                "A gout of dragonfire.", cost=0, power=14, damage_type="fire",
                aoe=True, target=TargetMode.AREA, effect="burning", effect_duration=2,
                scaling_attr=Attribute.CONSTITUTION, scaling_factor=1.2, school="natural",
                cooldown=3))
    add(Ability("rend", "Rend", AbilityKind.SKILL, "Claws that leave deep gashes.",
                cost=0, power=5, effect="bleeding", effect_duration=2,
                scaling_attr=Attribute.STRENGTH, school="natural"))
