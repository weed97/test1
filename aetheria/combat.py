"""Turn-based combat resolution.

A :class:`Battle` pits the player's side against a group of enemies (and can also
be used NPC-vs-NPC by the simulation).  It supports basic attacks, abilities/spells,
items, fleeing, status effects, criticals and elemental damage types.  The same
engine drives both the interactive CLI fights and fully automatic simulated ones.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .character import Actor
from .effects import StatusEffect, EFFECT_LIBRARY
from .rng import GameRandom
from .skills import Ability, AbilityKind, AbilityRegistry, TargetMode
from .stats import Attribute


# Elemental interaction table — multipliers applied on top of base damage.
RESISTANCE: dict[str, dict[str, float]] = {
    # defender tag -> {damage_type: multiplier}
    "undead": {"fire": 1.25, "holy": 1.5, "poison": 0.0, "frost": 0.75},
    "beast": {"poison": 1.25, "fire": 1.1},
    "construct": {"physical": 0.75, "poison": 0.0, "lightning": 1.5},
    "elemental_fire": {"fire": 0.0, "frost": 1.75},
    "elemental_frost": {"frost": 0.0, "fire": 1.75},
    "demon": {"holy": 1.6, "fire": 0.5},
    "plant": {"fire": 1.6, "frost": 0.6},
}


class ActionType(str, Enum):
    ATTACK = "attack"
    ABILITY = "ability"
    ITEM = "item"
    DEFEND = "defend"
    FLEE = "flee"


@dataclass
class CombatAction:
    actor: Actor
    type: ActionType
    target: Actor | None = None
    ability: Ability | None = None
    item_id: str | None = None


class Battle:
    def __init__(self, players: list[Actor], enemies: list[Actor],
                 abilities: AbilityRegistry, rng: GameRandom) -> None:
        self.players = players
        self.enemies = enemies
        self.abilities = abilities
        self.rng = rng
        self.round = 0
        self.log: list[str] = []
        self.over = False
        self.fled = False
        self.defending: set[str] = set()

    # -- helpers -------------------------------------------------------------
    def living(self, side: list[Actor]) -> list[Actor]:
        return [a for a in side if a.alive]

    def player_won(self) -> bool:
        return not self.living(self.enemies) and bool(self.living(self.players))

    def player_lost(self) -> bool:
        return not self.living(self.players)

    def side_of(self, actor: Actor) -> list[Actor]:
        return self.players if actor in self.players else self.enemies

    def opponents_of(self, actor: Actor) -> list[Actor]:
        return self.enemies if actor in self.players else self.players

    def _emit(self, line: str) -> None:
        self.log.append(line)

    def drain_log(self) -> list[str]:
        lines, self.log = self.log, []
        return lines

    # -- damage model --------------------------------------------------------
    def _resist_mult(self, defender: Actor, damage_type: str) -> float:
        tags = getattr(defender, "loot_table", None)
        species_tags: list[str] = []
        # NPCs may declare resistance tags via their species / role
        for attr in ("species", "role", "faction"):
            val = getattr(defender, attr, "")
            if val:
                species_tags.append(str(val))
        mult = 1.0
        for tag in species_tags:
            table = RESISTANCE.get(tag)
            if table and damage_type in table:
                mult *= table[damage_type]
        return mult

    def resolve_attack(self, attacker: Actor, defender: Actor,
                       ability: Ability | None = None) -> None:
        atk_stats = attacker.derived_stats()
        def_stats = defender.derived_stats()

        accuracy = atk_stats.accuracy
        evasion = def_stats.evasion
        if defender.id in self.defending:
            evasion += 8
        hit_roll = self.rng.percent()
        hit_threshold = max(5, min(95, accuracy - evasion))
        if hit_roll > hit_threshold:
            self._emit(f"  {attacker.name}'s attack misses {defender.name}.")
            return

        if ability and ability.kind is AbilityKind.SPELL:
            base = ability.power + atk_stats.spell_power
            scale = attacker.attrs.modifier(ability.scaling_attr) * ability.scaling_factor
            damage = int(base + scale)
            damage_type = ability.damage_type
            defense = def_stats.defense // 2  # magic partly bypasses armour
        elif ability:  # martial skill
            weapon = attacker.inventory.main_weapon() if attacker.inventory else None
            dice = weapon.damage_dice if weapon and weapon.damage_dice[0] else (1, 4)
            roll = self.rng.dice(*dice)
            scale = attacker.attrs.modifier(ability.scaling_attr) * ability.scaling_factor
            damage = int(atk_stats.attack + roll + ability.power + scale)
            damage_type = ability.damage_type
            defense = def_stats.defense
        else:  # basic attack
            weapon = attacker.inventory.main_weapon() if attacker.inventory else None
            dice = weapon.damage_dice if weapon and weapon.damage_dice[0] else (1, 3)
            roll = self.rng.dice(*dice)
            damage = atk_stats.attack + roll
            damage_type = weapon.damage_type if weapon else "physical"
            defense = def_stats.defense

        crit = self.rng.chance(atk_stats.crit_chance)
        if crit:
            damage = int(damage * 1.8)

        damage = max(1, damage - max(0, defense))
        damage = int(damage * self._resist_mult(defender, damage_type))
        if defender.id in self.defending:
            damage = int(damage * 0.6)

        if damage <= 0:
            self._emit(f"  {defender.name} shrugs off the {damage_type} damage.")
            return

        dealt = defender.take_damage(damage)
        verb = "critically strikes" if crit else "hits"
        spell_word = f" with {ability.name}" if ability else ""
        self._emit(f"  {attacker.name} {verb} {defender.name}{spell_word} "
                   f"for {dealt} {damage_type} damage. "
                   f"({defender.name}: {max(0, defender.health)}/{defender.max_health} HP)")

        if ability and ability.effect and defender.alive:
            if self.rng.chance(0.7):
                defender.add_effect(StatusEffect.create(ability.effect, ability.effect_duration or None))
                self._emit(f"  {defender.name} is afflicted with {ability.effect}!")

        if not defender.alive:
            self._emit(f"  {defender.name} falls!")

    def _apply_support(self, caster: Actor, ability: Ability, target: Actor) -> None:
        stats = caster.derived_stats()
        if ability.heal:
            amount = ability.heal + stats.spell_power
            healed = target.heal(amount)
            self._emit(f"  {caster.name} mends {target.name} for {healed} HP.")
        if ability.shield:
            eff = StatusEffect.create("shielded", ability.effect_duration or 3)
            eff.defense_mod = ability.shield
            target.add_effect(eff)
            self._emit(f"  {target.name} is wreathed in a protective ward.")
        if ability.effect and ability.heal == 0 and ability.shield == 0:
            target.add_effect(StatusEffect.create(ability.effect, ability.effect_duration or None))
            self._emit(f"  {target.name} gains {ability.effect}.")

    # -- a single actor's turn ----------------------------------------------
    def perform(self, action: CombatAction) -> None:
        actor = action.actor
        self.defending.discard(actor.id)
        if not actor.alive:
            return
        if actor.is_stunned():
            self._emit(f"  {actor.name} is stunned and loses the turn.")
            return

        if action.type is ActionType.DEFEND:
            self.defending.add(actor.id)
            actor.restore_stamina(5)
            self._emit(f"  {actor.name} takes a defensive stance.")

        elif action.type is ActionType.ATTACK:
            target = action.target or self._auto_target(actor)
            if target:
                self.resolve_attack(actor, target)

        elif action.type is ActionType.ABILITY and action.ability:
            ability = action.ability
            if not actor.can_use(ability):
                self._emit(f"  {actor.name} cannot use {ability.name} right now.")
                return
            actor.spend_for(ability)
            if ability.target in (TargetMode.SELF, TargetMode.ALLY) or ability.heal or ability.shield:
                target = action.target or actor
                if ability.target is TargetMode.SELF:
                    target = actor
                self._apply_support(actor, ability, target)
            elif ability.aoe:
                self._emit(f"  {actor.name} unleashes {ability.name}!")
                for foe in list(self.living(self.opponents_of(actor))):
                    self.resolve_attack(actor, foe, ability)
            else:
                target = action.target or self._auto_target(actor)
                if target:
                    self.resolve_attack(actor, target, ability)

        elif action.type is ActionType.ITEM and action.item_id:
            self._use_item(actor, action.item_id)

        elif action.type is ActionType.FLEE:
            chance = 0.4 + actor.derived_stats().evasion * 0.01
            if self.rng.chance(chance):
                self.fled = True
                self.over = True
                self._emit(f"  {actor.name} flees from battle!")
            else:
                self._emit(f"  {actor.name} fails to escape!")

    def _use_item(self, actor: Actor, item_id: str) -> None:
        if not actor.inventory or not actor.inventory.has(item_id):
            self._emit(f"  {actor.name} has no such item.")
            return
        template = actor.inventory.registry.get(item_id)
        actor.inventory.remove(item_id, 1)
        used = False
        if template.heal_amount:
            healed = actor.heal(template.heal_amount)
            self._emit(f"  {actor.name} uses {template.name}, recovering {healed} HP.")
            used = True
        if template.mana_amount:
            actor.restore_mana(template.mana_amount)
            self._emit(f"  {actor.name} restores {template.mana_amount} mana.")
            used = True
        if template.stamina_amount:
            actor.restore_stamina(template.stamina_amount)
            self._emit(f"  {actor.name} restores {template.stamina_amount} stamina.")
            used = True
        if template.effect:
            actor.add_effect(StatusEffect.create(template.effect))
            self._emit(f"  {actor.name} gains {template.effect}.")
            used = True
        if not used:
            self._emit(f"  {template.name} has no effect in battle.")

    def _auto_target(self, actor: Actor) -> Actor | None:
        foes = self.living(self.opponents_of(actor))
        if not foes:
            return None
        # focus the weakest foe
        return min(foes, key=lambda a: a.health)

    # -- enemy / ally AI -----------------------------------------------------
    def choose_ai_action(self, actor: Actor) -> CombatAction:
        # heal self if badly hurt and a heal ability is available
        if actor.health < actor.max_health * 0.35:
            for aid in actor.abilities:
                ab = self.abilities.get(aid)
                if ab.heal and actor.can_use(ab):
                    return CombatAction(actor, ActionType.ABILITY, target=actor, ability=ab)
            # try a healing potion
            if actor.inventory:
                for tmpl, _ in actor.inventory.items():
                    if tmpl.heal_amount:
                        return CombatAction(actor, ActionType.ITEM, item_id=tmpl.id)
        # otherwise prefer an affordable offensive ability sometimes
        offensive = [self.abilities.get(a) for a in actor.abilities
                     if self.abilities.get(a).is_offensive and actor.can_use(self.abilities.get(a))]
        target = self._auto_target(actor)
        if offensive and self.rng.chance(0.6):
            return CombatAction(actor, ActionType.ABILITY,
                                target=target, ability=self.rng.choice(offensive))
        return CombatAction(actor, ActionType.ATTACK, target=target)

    # -- round orchestration -------------------------------------------------
    def begin_round(self) -> None:
        self.round += 1
        self._emit(f"— Round {self.round} —")

    def turn_order(self) -> list[Actor]:
        combatants = self.living(self.players) + self.living(self.enemies)
        return sorted(combatants,
                      key=lambda a: a.derived_stats().initiative + self.rng.randint(0, 4),
                      reverse=True)

    def end_round(self) -> None:
        for actor in self.living(self.players) + self.living(self.enemies):
            for line in actor.tick_effects():
                self._emit(line)
            actor.tick_cooldowns()
        if self.player_won() or self.player_lost():
            self.over = True

    def auto_resolve(self, max_rounds: int = 30) -> str:
        """Run an entire battle with AI on both sides (used by the simulation)."""
        while not self.over and self.round < max_rounds:
            self.begin_round()
            for actor in self.turn_order():
                if self.over or not actor.alive:
                    continue
                self.perform(self.choose_ai_action(actor))
                if self.player_won() or self.player_lost():
                    self.over = True
                    break
            self.end_round()
        if self.player_won():
            return "players"
        if self.player_lost():
            return "enemies"
        return "draw"
