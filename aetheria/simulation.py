"""The autonomous world-simulation loop that makes Aetheria *live*.

Even when the player is idle, the world keeps turning.  Each simulated hour:

* the clock advances and NPCs move along their daily **schedules**;
* moods drift back toward each NPC's temperament and resources slowly regenerate;
* the **market** breathes (mean-reverting random walk);
* once per day a **world event** may fire, rippling through prices and moods;
* co-located NPCs **gossip**, spreading rumours and nudging each other's moods;
* in dangerous places hostile NPCs may **clash** with others, resolved automatically.

The loop returns a chronicle of notable happenings so the UI can surface "what
happened while you were away".
"""

from __future__ import annotations

from .character import NPC
from .combat import Battle
from .state import World


class Simulation:
    def __init__(self, world: World) -> None:
        self.world = world

    # -- per-tick steps ------------------------------------------------------
    def _move_npcs(self) -> None:
        tod = self.world.clock.time_of_day.value
        for npc in self.world.npcs.values():
            if not npc.alive:
                continue
            target = npc.location_for(tod)
            if target and target in self.world.map.locations:
                npc.current_location = target

    def _drift_npcs(self) -> None:
        for npc in self.world.npcs.values():
            if not npc.alive:
                continue
            # mood eases toward a personality baseline
            baseline = (npc.personality.warmth - 50) // 5
            if npc.mood_score > baseline:
                npc.mood_score -= 1
            elif npc.mood_score < baseline:
                npc.mood_score += 1
            # gentle resource regeneration
            npc.restore_stamina(2)
            npc.restore_mana(1)
            if not npc.has_effect("poison"):
                npc.heal(1)

    def _gossip(self, log: list[str], verbose: bool) -> None:
        rng = self.world.rng
        by_loc: dict[str, list[NPC]] = {}
        for npc in self.world.npcs.values():
            if npc.alive:
                by_loc.setdefault(npc.current_location, []).append(npc)
        for loc_id, group in by_loc.items():
            if len(group) < 2:
                continue
            if not rng.chance(0.25):
                continue
            a, b = rng.sample(group, 2)
            # share a rumour
            source_rumors = a.known_rumors + self.world.rumor_pool
            if source_rumors and rng.chance(0.5):
                rumor = rng.choice(source_rumors)
                if rumor not in b.known_rumors:
                    b.known_rumors.append(rumor)
                    if len(b.known_rumors) > 8:
                        b.known_rumors.pop(0)
            # a small mood exchange
            shift = 1 if (a.personality.warmth + b.personality.warmth) > 100 else -1
            a.adjust_mood(shift)
            b.adjust_mood(shift)
            if verbose and rng.chance(0.15):
                loc = self.world.map.locations.get(loc_id)
                where = loc.name if loc else loc_id
                log.append(f"  {a.name} and {b.name} chat quietly in {where}.")

    def _skirmishes(self, log: list[str]) -> None:
        rng = self.world.rng
        by_loc: dict[str, list[NPC]] = {}
        for npc in self.world.npcs.values():
            if npc.alive:
                by_loc.setdefault(npc.current_location, []).append(npc)
        for loc_id, group in by_loc.items():
            loc = self.world.map.locations.get(loc_id)
            if not loc or loc.is_safe:
                continue
            hostiles = [n for n in group if n.hostile_by_default]
            victims = [n for n in group if not n.hostile_by_default]
            if not hostiles or not victims:
                continue
            if not rng.chance(0.2):
                continue
            attacker = rng.choice(hostiles)
            victim = rng.choice(victims)
            battle = Battle([victim], [attacker], self.world.abilities, rng)
            outcome = battle.auto_resolve()
            where = loc.name
            if outcome == "players":
                log.append(f"  {victim.name} fought off {attacker.name} in {where}.")
                attacker.heal(attacker.max_health)  # they retreat, not die, off-screen
            elif outcome == "enemies":
                log.append(f"  {victim.name} was robbed by {attacker.name} in {where}!")
                victim.heal(victim.max_health)
                victim.adjust_mood(-15)
            for actor in (victim, attacker):
                actor.full_restore()

    def _maybe_event(self, log: list[str]) -> None:
        if self.world.clock.hour != 8:  # one roll per in-world morning
            return
        if not self.world.rng.chance(0.55):
            return
        event = self.world.event_deck.draw(self.world.rng, self.world.clock.season.value)
        if event:
            log.extend(self.world.event_deck.apply(event, self.world))

    # -- public API ----------------------------------------------------------
    def tick(self, log: list[str], verbose: bool = False) -> None:
        self.world.clock.advance(1)
        self.world.tick_count += 1
        self._move_npcs()
        self._drift_npcs()
        self._maybe_event(log)
        self._gossip(log, verbose)
        self._skirmishes(log)
        if self.world.tick_count % 4 == 0:
            self.world.market.drift()

    def advance(self, hours: int = 1, verbose: bool = False) -> list[str]:
        log: list[str] = []
        for _ in range(max(1, hours)):
            self.tick(log, verbose=verbose)
        return log

    def run(self, days: int, verbose: bool = True) -> list[str]:
        return self.advance(hours=days * 24, verbose=verbose)
