from __future__ import annotations

import random
from typing import Dict, List

from .data import build_world
from .dialogue import generate_reply
from .models import Item, NPC, Player, Quest, Region, WorldState


WEATHERS = ["clear", "rain", "storm", "fog", "heatwave", "ashen_wind"]


class SimulatorEngine:
    def __init__(self, player_name: str, seed: int = 1337) -> None:
        self.rng = random.Random(seed)
        self.world, self.player, self.items = build_world(player_name=player_name, rng=self.rng)

    @property
    def current_region(self) -> Region:
        return self.world.regions[self.player.region_key]

    def _npcs_here(self) -> List[NPC]:
        return [npc for npc in self.world.npcs.values() if npc.region_key == self.player.region_key]

    def _available_quests_here(self) -> List[Quest]:
        return [
            quest
            for quest in self.world.quests.values()
            if quest.region_key == self.player.region_key and quest.status == "available"
        ]

    def _active_quests(self) -> List[Quest]:
        return [quest for quest in self.world.quests.values() if quest.status == "active"]

    def status(self) -> str:
        region = self.current_region
        return (
            f"Day {self.world.day} | Weather: {self.world.weather} | Region: {region.name}\n"
            f"HP {self.player.health}/{self.player.max_health} | LV {self.player.level} "
            f"(XP {self.player.experience}/{self.player.level * 120}) | Gold {self.player.gold}\n"
            f"Reputation: "
            + ", ".join(
                f"{self.world.factions[key].name}:{value:+d}"
                for key, value in sorted(self.player.reputation.items())
            )
        )

    def world_map(self) -> str:
        lines = ["=== Realm Regions ==="]
        for region in self.world.regions.values():
            marker = " (You are here)" if region.key == self.player.region_key else ""
            lines.append(
                f"- {region.name}{marker}: biome={region.biome}, danger={region.danger}, "
                f"prosperity={region.prosperity}, neighbors={', '.join(region.neighbors)}"
            )
        return "\n".join(lines)

    def look(self) -> str:
        region = self.current_region
        npcs = self._npcs_here()
        quests = self._available_quests_here()
        market_lines = []
        for item_key in region.resources:
            item = self.items[item_key]
            market_lines.append(f"{item.key}: {region.market.get_price(item)}g")
        if not market_lines:
            market_lines.append("No active market listings.")
        return (
            f"{region.name} ({region.biome})\n"
            f"Danger {region.danger}/10, Prosperity {region.prosperity}/10\n"
            f"Resources: {', '.join(region.resources)}\n"
            f"Notable NPCs: {', '.join(npc.name for npc in npcs) if npcs else 'none'}\n"
            f"Available Quests: {', '.join(quest.key for quest in quests) if quests else 'none'}\n"
            f"Market Snapshot: {', '.join(market_lines)}"
        )

    def travel(self, target_region_key: str) -> str:
        target_region_key = target_region_key.lower().strip()
        if target_region_key not in self.world.regions:
            return f"Unknown region '{target_region_key}'. Use map to inspect valid regions."
        if target_region_key == self.player.region_key:
            return "You are already in that region."
        if target_region_key not in self.current_region.neighbors:
            return (
                f"You cannot travel directly from {self.current_region.key} to {target_region_key}. "
                "Travel only to neighboring regions."
            )
        target = self.world.regions[target_region_key]
        hazard_roll = self.rng.randint(1, 10)
        notes = [f"You travel from {self.current_region.name} to {target.name}."]
        self.player.region_key = target_region_key
        if hazard_roll <= target.danger // 2:
            damage = self.rng.randint(4, 10 + target.danger)
            self.player.health = max(1, self.player.health - damage)
            notes.append(f"The road is dangerous. You lose {damage} health.")
        else:
            found_item = self.rng.choice(target.resources)
            self.player.add_item(found_item, 1)
            notes.append(f"You arrive safely and scavenge 1 {found_item}.")
            self._apply_quest_progress("collect", found_item, 1)
        self.tick(1)
        return " ".join(notes)

    def talk(self, npc_key_or_name: str, message: str) -> str:
        normalized = npc_key_or_name.lower().strip()
        npcs_here = self._npcs_here()
        candidate = None
        for npc in npcs_here:
            if normalized in {npc.key.lower(), npc.name.lower()}:
                candidate = npc
                break
        if candidate is None:
            fuzzy = [npc for npc in npcs_here if normalized in npc.name.lower()]
            candidate = fuzzy[0] if fuzzy else None
        if candidate is None:
            return "No such NPC is present in your current region."
        quests = [quest for quest in self._available_quests_here() if quest.giver_npc_key == candidate.key]
        return generate_reply(self.world, self.player, candidate, message, quests, self.rng)

    def hunt(self) -> str:
        region = self.current_region
        roll = self.rng.randint(1, 20) + self.player.level
        threshold = 8 + region.danger
        if roll >= threshold:
            drop = self.rng.choice([item for item in region.resources if "ration" not in item] or region.resources)
            amount = 2 if self.rng.random() < 0.25 else 1
            self.player.add_item(drop, amount)
            self._apply_quest_progress("collect", drop, amount)
            exp = 18 + region.danger * 2
            leveled = self.player.gain_experience(exp)
            self.tick(1)
            level_line = " You leveled up!" if leveled else ""
            return f"Hunt successful: +{amount} {drop}, +{exp} XP.{level_line}"
        damage = self.rng.randint(6, 14 + region.danger)
        self.player.health = max(1, self.player.health - damage)
        self.tick(1)
        return f"The hunt failed. You are injured for {damage} health."

    def rest(self) -> str:
        restored = min(self.player.max_health - self.player.health, 20 + self.player.level * 2)
        self.player.health += restored
        self.tick(1)
        return f"You rest at a local camp and recover {restored} health."

    def inventory(self) -> str:
        if not self.player.inventory:
            return "Inventory is empty."
        lines = ["=== Inventory ==="]
        for key, amount in sorted(self.player.inventory.items()):
            label = self.items[key].name if key in self.items else key
            lines.append(f"- {key} ({label}): {amount}")
        return "\n".join(lines)

    def list_quests(self) -> str:
        lines = ["=== Quests ==="]
        for quest in self.world.quests.values():
            giver = self.world.npcs[quest.giver_npc_key].name
            lines.append(
                f"- {quest.key} [{quest.status}] {quest.title} | giver={giver} | "
                f"objective={quest.objective.action}:{quest.objective.target} "
                f"{quest.objective.progress}/{quest.objective.required}"
            )
        return "\n".join(lines)

    def accept_quest(self, quest_key: str) -> str:
        quest_key = quest_key.lower().strip()
        quest = self.world.quests.get(quest_key)
        if quest is None:
            return f"Unknown quest '{quest_key}'."
        if quest.status != "available":
            return f"Quest '{quest.key}' is not available."
        if quest.region_key != self.player.region_key:
            return f"Travel to {quest.region_key} first to accept this quest."
        quest.status = "active"
        self.world.log_event(f"Day {self.world.day}: {self.player.name} accepted quest {quest.title}.")
        return f"Quest accepted: {quest.title}"

    def complete_quest(self, quest_key: str) -> str:
        quest_key = quest_key.lower().strip()
        quest = self.world.quests.get(quest_key)
        if quest is None:
            return f"Unknown quest '{quest_key}'."
        if quest.status != "active":
            return f"Quest '{quest.key}' is not active."
        if not quest.objective.is_complete():
            return (
                f"Quest progress insufficient: {quest.objective.progress}/{quest.objective.required} "
                f"{quest.objective.target}."
            )
        quest.status = "completed"
        self.player.gold += quest.reward_gold
        for faction_key, rep in quest.reward_reputation.items():
            self.player.reputation[faction_key] = self.player.reputation.get(faction_key, 0) + rep
        exp_gain = 50 + 10 * len(quest.reward_reputation)
        leveled = self.player.gain_experience(exp_gain)
        self.world.log_event(f"Day {self.world.day}: {self.player.name} completed quest {quest.title}.")
        leveled_msg = " You leveled up from the reward." if leveled else ""
        return f"Quest complete! +{quest.reward_gold} gold, +{exp_gain} XP.{leveled_msg}"

    def buy(self, item_key: str, amount: int = 1) -> str:
        item_key = item_key.lower().strip()
        item = self.items.get(item_key)
        if item is None:
            return f"Unknown item '{item_key}'."
        if amount <= 0:
            return "Amount must be positive."
        price = self.current_region.market.get_price(item) * amount
        if self.player.gold < price:
            return f"Not enough gold. Required: {price}, available: {self.player.gold}."
        self.player.gold -= price
        self.player.add_item(item_key, amount)
        self._apply_quest_progress("collect", item_key, amount)
        return f"Purchased {amount} x {item_key} for {price} gold."

    def sell(self, item_key: str, amount: int = 1) -> str:
        item_key = item_key.lower().strip()
        item = self.items.get(item_key)
        if item is None:
            return f"Unknown item '{item_key}'."
        if amount <= 0:
            return "Amount must be positive."
        if not self.player.has_item(item_key, amount):
            return f"You do not have {amount} x {item_key}."
        unit_price = int(self.current_region.market.get_price(item) * 0.62)
        payout = max(1, unit_price * amount)
        self.player.add_item(item_key, -amount)
        self.player.gold += payout
        return f"Sold {amount} x {item_key} for {payout} gold."

    def consume(self, item_key: str) -> str:
        item_key = item_key.lower().strip()
        if not self.player.has_item(item_key, 1):
            return f"You do not have any '{item_key}'."
        if item_key != "healing_draught":
            return f"{item_key} cannot be consumed directly."
        self.player.add_item(item_key, -1)
        recovered = min(self.player.max_health - self.player.health, 35)
        self.player.health += recovered
        return f"You drink a healing draught and recover {recovered} health."

    def logs(self, count: int = 8) -> str:
        count = max(1, min(50, count))
        return "\n".join(self.world.events[-count:])

    def mega_simulate(self, days: int) -> str:
        days = max(1, min(365, days))
        self.tick(days)
        active = len(self._active_quests())
        completed = len([quest for quest in self.world.quests.values() if quest.status == "completed"])
        return (
            f"Simulated {days} days. Day now {self.world.day}, weather={self.world.weather}. "
            f"Active quests={active}, completed={completed}."
        )

    def tick(self, days: int = 1) -> None:
        for _ in range(max(1, days)):
            self.world.day += 1
            self.world.weather = self.rng.choices(
                WEATHERS,
                weights=[28, 22, 13, 16, 9, 12],
                k=1,
            )[0]
            self._simulate_factions()
            self._simulate_markets()
            self._simulate_npcs()
            self._simulate_world_events()

    def _simulate_factions(self) -> None:
        for faction in self.world.factions.values():
            faction.wealth = max(1, min(100, faction.wealth + self.rng.randint(-2, 3)))
            faction.influence = max(1, min(100, faction.influence + self.rng.randint(-1, 2)))
            for other_key in faction.relations:
                drift = self.rng.randint(-2, 2)
                faction.relations[other_key] = max(-100, min(100, faction.relations[other_key] + drift))

    def _simulate_markets(self) -> None:
        weather_penalty = {
            "clear": 0.00,
            "rain": 0.03,
            "storm": 0.08,
            "fog": 0.02,
            "heatwave": 0.05,
            "ashen_wind": 0.11,
        }[self.world.weather]
        for region in self.world.regions.values():
            scarcity = (region.danger * 0.009) - (region.prosperity * 0.006)
            jitter = self.rng.uniform(-0.05, 0.07)
            delta = scarcity + weather_penalty + jitter
            for item_key in self.items:
                resource_bonus = -0.04 if item_key in region.resources else 0.02
                region.market.fluctuate(item_key, delta + resource_bonus)

    def _simulate_npcs(self) -> None:
        for npc in self.world.npcs.values():
            shift = self.rng.randint(-3, 3)
            npc.disposition = max(-60, min(60, npc.disposition + shift))
            if self.rng.random() < 0.2:
                npc.remember(f"Day {self.world.day}: dealt with local unrest in {npc.region_key}.")

    def _simulate_world_events(self) -> None:
        focus_region = self.rng.choice(list(self.world.regions.values()))
        focus_faction = self.rng.choice(list(self.world.factions.values()))
        event = (
            f"Day {self.world.day}: {focus_faction.name} activity rises in {focus_region.name} "
            f"under {self.world.weather} skies."
        )
        self.world.log_event(event)

    def _apply_quest_progress(self, action: str, target: str, amount: int) -> None:
        for quest in self._active_quests():
            objective = quest.objective
            if objective.action in {"collect", "hunt"} and action in {"collect", "hunt"}:
                if objective.target == target:
                    objective.progress = min(objective.required, objective.progress + amount)
