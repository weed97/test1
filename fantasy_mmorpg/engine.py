"""Game engine and command handlers for the text MMORPG simulator."""

from __future__ import annotations

import json
import random
import re
from pathlib import Path
from typing import Any

from fantasy_mmorpg.content import (
    CLASS_TEMPLATES,
    ENEMIES,
    FACTIONS,
    ITEMS,
    NPCS,
    QUESTS,
    RANDOM_EVENTS,
    RECIPES,
    SECRET_DEFINITIONS,
    ZONES,
)
from fantasy_mmorpg.models import Enemy, Player, Quest, WorldState


DEFAULT_SAVE_PATH = Path("saves/eldermist_save.json")


def slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.lower()).strip("_")


class GameEngine:
    """Stateful simulator for a single player in a living fantasy world."""

    def __init__(
        self,
        player: Player | None = None,
        world: WorldState | None = None,
        *,
        seed: int | None = None,
    ) -> None:
        self.rng = random.Random(seed)
        self.player = player or self.create_player("Alden", "knight")
        self.world = world or WorldState()
        self.active_enemy: Enemy | None = None
        self.last_messages: list[str] = []
        if self.player.location not in self.player.explored:
            self.player.explored.append(self.player.location)

    @staticmethod
    def create_player(name: str, class_name: str = "knight") -> Player:
        class_key = slugify(class_name)
        if class_key not in CLASS_TEMPLATES:
            class_key = "knight"
        template = CLASS_TEMPLATES[class_key]
        reputation = {faction: 0 for faction in FACTIONS}
        player = Player(
            name=name.strip() or "Nameless Wanderer",
            ancestry=template["ancestry"],
            class_name=class_key,
            background=template["background"],
            level=1,
            xp=0,
            gold=template["gold"],
            location="eldermist_village",
            attributes=dict(template["attributes"]),
            hp=template["hp"],
            max_hp=template["hp"],
            mana=template["mana"],
            max_mana=template["mana"],
            inventory=dict(template["items"]),
            equipment={},
            reputation=reputation,
            world_flags={"story_arc": "embers_before_the_storm"},
        )
        for item_id in list(player.inventory):
            item = ITEMS[item_id]
            if item.equip_slot and item.equip_slot not in player.equipment:
                player.equipment[item.equip_slot] = item_id
        return player

    def handle(self, raw_command: str) -> str:
        command = raw_command.strip()
        if not command:
            return "Type 'help' for a list of commands."

        verb, _, rest = command.partition(" ")
        verb = verb.lower()
        rest = rest.strip()

        if self.active_enemy and verb in {"attack", "cast", "use", "defend", "flee", "inspect"}:
            return self._with_time(self._handle_combat_command(verb, rest), advances=True)
        if self.active_enemy and verb not in {"help", "stats", "inventory", "quit"}:
            return f"{self.active_enemy.name} blocks your attention. Use attack, cast, use, defend, flee, or inspect."

        handlers = {
            "help": lambda: self.help_text(),
            "?": lambda: self.help_text(),
            "look": self.look,
            "l": self.look,
            "map": self.map_text,
            "stats": self.stats,
            "sheet": self.stats,
            "inventory": self.inventory,
            "inv": self.inventory,
            "quests": self.quests_text,
            "journal": self.journal,
            "factions": self.factions,
            "recipes": self.recipes_text,
            "rest": self.rest,
            "search": self.search,
            "gather": lambda: self.gather(rest),
            "hunt": self.start_fight,
            "fight": self.start_fight,
            "shop": self.shop,
        }
        if verb in handlers:
            advances = verb in {"look", "rest", "search", "gather", "hunt", "fight"}
            return self._with_time(handlers[verb](), advances=advances)
        if verb in {"go", "travel", "move"}:
            return self._with_time(self.go(rest), advances=True)
        if verb == "talk":
            return self._with_time(self.talk(rest), advances=True)
        if verb == "ask":
            return self._with_time(self.ask(rest), advances=True)
        if verb == "accept":
            return self._with_time(self.accept_quest(rest), advances=True)
        if verb == "complete":
            return self._with_time(self.complete_quest(rest), advances=True)
        if verb == "equip":
            return self._with_time(self.equip(rest), advances=False)
        if verb == "use":
            return self._with_time(self.use_item(rest), advances=True)
        if verb == "buy":
            return self._with_time(self.buy(rest), advances=True)
        if verb == "sell":
            return self._with_time(self.sell(rest), advances=True)
        if verb == "craft":
            return self._with_time(self.craft(rest), advances=True)
        if verb == "save":
            return self.save(Path(rest) if rest else DEFAULT_SAVE_PATH)
        if verb == "load":
            return self.load_into_self(Path(rest) if rest else DEFAULT_SAVE_PATH)
        return f"Unknown command: {verb}. Type 'help' to see what the world understands."

    def _with_time(self, message: str, *, advances: bool) -> str:
        if not advances:
            return message
        event_text = self.advance_time()
        if event_text:
            return f"{message}\n\nWorld Event: {event_text}"
        return message

    def advance_time(self) -> str | None:
        self.world.turn += 1
        self.world.hour += 1
        if self.world.hour >= 24:
            self.world.hour = 0
            self.world.day += 1

        if self.world.event_duration > 0:
            self.world.event_duration -= 1
            if self.world.event_duration == 0:
                expired = self.world.active_event
                self.world.active_event = None
                if expired:
                    return f"The effects of {expired.replace('_', ' ')} fade from the valley."
            return None

        if self.world.turn > 2 and self.world.turn % 7 == 0:
            event = self.rng.choice(RANDOM_EVENTS)
            self.world.active_event = event["id"]
            self.world.event_duration = event["duration"]
            for faction, amount in event.get("reputation", {}).items():
                self.player.reputation[faction] = self.player.reputation.get(faction, 0) + amount
            return str(event["text"])
        return None

    def help_text(self) -> str:
        return (
            "Core commands:\n"
            "  look, map, go <exit/location>, talk <npc>, ask <npc> about <topic>\n"
            "  accept <quest>, complete <quest>, quests, journal, factions\n"
            "  inventory, equip <item>, use <item>, stats, rest\n"
            "  search, gather [resource], hunt/fight, attack, cast <spell>, defend, flee\n"
            "  shop, buy <item>, sell <item>, recipes, craft <recipe>\n"
            "  save [path], load [path], help, quit\n"
            "Tip: names are fuzzy. 'go woods' and 'talk mira' both work."
        )

    def look(self) -> str:
        zone = ZONES[self.player.location]
        lines = [
            f"{zone.name} ({zone.region}, danger {zone.danger_level})",
            zone.description,
        ]
        if zone.ambience:
            lines.append(self.rng.choice(zone.ambience))
        npcs = [NPCS[npc_id].display_name for npc_id in zone.npc_ids]
        if npcs:
            lines.append("People here: " + ", ".join(npcs))
        if zone.resources:
            lines.append("Resources: " + ", ".join(ITEMS[item].name for item in zone.resources))
        if zone.shop_ids:
            lines.append("Services: " + ", ".join(NPCS[npc_id].name for npc_id in zone.shop_ids))
        lines.append("Exits: " + ", ".join(f"{direction} -> {ZONES[target].name}" for direction, target in zone.exits.items()))
        return "\n".join(lines)

    def map_text(self) -> str:
        zone = ZONES[self.player.location]
        lines = [f"You are at {zone.name}."]
        for direction, target in zone.exits.items():
            target_zone = ZONES[target]
            marker = "visited" if target in self.player.explored else "unknown"
            lines.append(f"  {direction:>5}: {target_zone.name} [{marker}, danger {target_zone.danger_level}]")
        return "\n".join(lines)

    def go(self, destination: str) -> str:
        if not destination:
            return "Go where? Try 'map' to see exits."
        zone = ZONES[self.player.location]
        destination_key = slugify(destination)
        target_id = zone.exits.get(destination_key)
        if not target_id:
            for direction, candidate in zone.exits.items():
                candidate_zone = ZONES[candidate]
                if destination_key in {slugify(direction), slugify(candidate), slugify(candidate_zone.name)}:
                    target_id = candidate
                    break
        if not target_id:
            return f"No route from {zone.name} matches '{destination}'."
        target = ZONES[target_id]
        if target.danger_level > self.player.level + 4:
            return f"The route toward {target.name} feels suicidal at your current level."
        self.player.location = target_id
        if target_id not in self.player.explored:
            self.player.explored.append(target_id)
        return f"You travel to {target.name}.\n\n{self.look()}"

    def talk(self, npc_query: str) -> str:
        npc = self.find_npc(npc_query)
        if not npc:
            return f"No one here matches '{npc_query}'."
        if npc.id not in self.player.talked_to:
            self.player.talked_to.append(npc.id)
        lines = [f"{npc.display_name}: \"{npc.greeting}\""]
        available = [QUESTS[quest_id] for quest_id in npc.quest_ids if self.quest_can_be_offered(QUESTS[quest_id])]
        ready = [QUESTS[quest_id] for quest_id in npc.quest_ids if self.quest_is_ready(QUESTS[quest_id])]
        active = [QUESTS[quest_id] for quest_id in npc.quest_ids if quest_id in self.player.active_quests]
        if ready:
            lines.append("Ready to complete: " + ", ".join(quest.title for quest in ready))
        if available:
            lines.append("Available quests: " + ", ".join(quest.title for quest in available))
        if active and not ready:
            lines.append("Active business: " + ", ".join(quest.title for quest in active))
        if npc.topics:
            lines.append("Ask about: " + ", ".join(sorted(npc.topics)))
        if npc.shop_inventory:
            lines.append("This NPC trades. Use 'shop' or 'buy <item>'.")
        return "\n".join(lines)

    def ask(self, text: str) -> str:
        if " about " in text:
            npc_text, topic_text = text.split(" about ", 1)
        else:
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                return "Ask whom about what? Example: ask mira about rumors"
            npc_text, topic_text = parts
        npc = self.find_npc(npc_text.strip())
        if not npc:
            return f"No one here matches '{npc_text.strip()}'."
        topic_key = self.match_key(topic_text, npc.topics)
        if not topic_key:
            return f"{npc.name} has nothing useful to say about '{topic_text}'. Try: {', '.join(sorted(npc.topics))}."
        if npc.id not in self.player.talked_to:
            self.player.talked_to.append(npc.id)
        response = npc.topics[topic_key]
        extra = self.contextual_dialogue(npc.id, topic_key)
        if extra:
            response = f"{response}\n{extra}"
        return f"{npc.display_name} on {topic_key}: \"{response}\""

    def contextual_dialogue(self, npc_id: str, topic: str) -> str:
        if npc_id == "captain_rowan" and topic == "traitor" and "keep_cipher" in self.player.discoveries:
            return "Rowan lowers his voice. 'That cipher changes everything. Vehn will audit every gate ledger by dawn.'"
        if npc_id == "kael_the_exile" and "chapel_relic" in self.player.inventory:
            return "Kael stares at the reliquary. 'So the chapel still has teeth. Good.'"
        if topic == "dragon" and self.player.reputation.get("Ashen Covenant", 0) <= -5:
            return "The name draws a warm pressure behind your eyes, as if the crater heard."
        return ""

    def accept_quest(self, quest_query: str) -> str:
        quest = self.find_quest(quest_query)
        if not quest:
            return f"No quest matches '{quest_query}'."
        if quest.id in self.player.completed_quests:
            return f"{quest.title} is already complete."
        if quest.id in self.player.active_quests:
            return f"{quest.title} is already in your journal."
        if not self.quest_can_be_offered(quest):
            return self.quest_block_reason(quest)
        giver = NPCS[quest.giver]
        if giver.id not in ZONES[self.player.location].npc_ids:
            return f"Return to {giver.name} to accept {quest.title}."
        self.player.active_quests[quest.id] = "active"
        return f"Quest accepted: {quest.title}\n{quest.description}\n{self.quest_objectives_text(quest)}"

    def complete_quest(self, quest_query: str) -> str:
        quest = self.find_quest(quest_query, active_only=True)
        if not quest:
            return f"No active quest matches '{quest_query}'."
        giver = NPCS[quest.giver]
        if giver.id not in ZONES[self.player.location].npc_ids:
            return f"{quest.title} must be turned in to {giver.display_name}."
        if not self.quest_is_ready(quest):
            return f"{quest.title} is not ready.\n{self.quest_objectives_text(quest)}"

        for objective in quest.objectives:
            if objective["type"] == "collect":
                self.player.remove_item(objective["target"], int(objective.get("count", 1)))
        del self.player.active_quests[quest.id]
        self.player.completed_quests.append(quest.id)
        self.player.world_flags[f"quest_completed:{quest.id}"] = True

        rewards = quest.rewards
        reward_lines = []
        gold = int(rewards.get("gold", 0))
        xp = int(rewards.get("xp", 0))
        if gold:
            self.player.gold += gold
            reward_lines.append(f"{gold} gold")
        if xp:
            level_text = self.gain_xp(xp)
            reward_lines.append(f"{xp} XP")
            if level_text:
                reward_lines.append(level_text)
        for item_id, count in rewards.get("items", {}).items():
            self.player.add_item(item_id, int(count))
            reward_lines.append(f"{ITEMS[item_id].name} x{count}")
        for faction, amount in rewards.get("reputation", {}).items():
            self.player.reputation[faction] = self.player.reputation.get(faction, 0) + int(amount)
            reward_lines.append(f"{faction} reputation {amount:+d}")
        reward_text = ", ".join(reward_lines) if reward_lines else "gratitude"
        return f"{quest.completion_text}\nQuest complete: {quest.title}\nRewards: {reward_text}"

    def quests_text(self) -> str:
        if not self.player.active_quests and not self.player.completed_quests:
            return "Your journal is empty. Talk to NPCs to find work."
        lines: list[str] = []
        if self.player.active_quests:
            lines.append("Active quests:")
            for quest_id in self.player.active_quests:
                quest = QUESTS[quest_id]
                status = "ready" if self.quest_is_ready(quest) else "in progress"
                lines.append(f"- {quest.title} [{status}]\n  {self.quest_objectives_text(quest)}")
        if self.player.completed_quests:
            lines.append("Completed quests:")
            for quest_id in self.player.completed_quests:
                lines.append(f"- {QUESTS[quest_id].title}")
        return "\n".join(lines)

    def quest_objectives_text(self, quest: Quest) -> str:
        parts = []
        for objective in quest.objectives:
            current, needed = self.objective_progress(objective)
            target = objective["target"]
            label = self.objective_label(objective)
            parts.append(f"{label}: {current}/{needed}")
        return "; ".join(parts)

    def objective_label(self, objective: dict[str, Any]) -> str:
        target = objective["target"]
        if objective["type"] == "collect":
            return f"Collect {ITEMS[target].name}"
        if objective["type"] == "kill":
            return f"Defeat {ENEMIES[target].name}"
        if objective["type"] == "explore":
            return f"Explore {ZONES[target].name}"
        if objective["type"] == "talk":
            return f"Speak with {NPCS[target].name}"
        if objective["type"] == "flag":
            return f"Resolve {target.replace('_', ' ')}"
        return target

    def objective_progress(self, objective: dict[str, Any]) -> tuple[int, int]:
        needed = int(objective.get("count", 1))
        target = objective["target"]
        kind = objective["type"]
        if kind == "collect":
            return min(self.player.inventory.get(target, 0), needed), needed
        if kind == "kill":
            return min(self.player.killed.get(target, 0), needed), needed
        if kind == "explore":
            return (1 if target in self.player.explored else 0), needed
        if kind == "talk":
            return (1 if target in self.player.talked_to else 0), needed
        if kind == "flag":
            return (1 if self.player.world_flags.get(target) else 0), needed
        return 0, needed

    def quest_is_ready(self, quest: Quest) -> bool:
        if quest.id not in self.player.active_quests:
            return False
        return all(current >= needed for current, needed in (self.objective_progress(obj) for obj in quest.objectives))

    def quest_can_be_offered(self, quest: Quest) -> bool:
        if quest.id in self.player.active_quests or quest.id in self.player.completed_quests:
            return False
        if self.player.level < quest.required_level:
            return False
        return all(prereq in self.player.completed_quests for prereq in quest.prerequisites)

    def quest_block_reason(self, quest: Quest) -> str:
        if self.player.level < quest.required_level:
            return f"{quest.title} requires level {quest.required_level}. You are level {self.player.level}."
        missing = [q for q in quest.prerequisites if q not in self.player.completed_quests]
        if missing:
            return f"{quest.title} requires: {', '.join(QUESTS[q].title for q in missing)}."
        return f"{quest.title} is not available right now."

    def inventory(self) -> str:
        if not self.player.inventory:
            return "Your pack is empty."
        lines = [f"Gold: {self.player.gold}", "Inventory:"]
        for item_id, count in sorted(self.player.inventory.items(), key=lambda row: ITEMS[row[0]].name):
            item = ITEMS[item_id]
            equipped = " (equipped)" if item_id in self.player.equipment.values() else ""
            lines.append(f"- {item.name} x{count}{equipped}: {item.description}")
        return "\n".join(lines)

    def equip(self, item_query: str) -> str:
        item_id = self.find_item_id(item_query, inventory_only=True)
        if not item_id:
            return f"You do not carry an equippable item matching '{item_query}'."
        item = ITEMS[item_id]
        if not item.equip_slot:
            return f"{item.name} cannot be equipped."
        self.player.equipment[item.equip_slot] = item_id
        self.recalculate_derived_stats()
        return f"Equipped {item.name} in {item.equip_slot}."

    def use_item(self, item_query: str) -> str:
        item_id = self.find_item_id(item_query, inventory_only=True)
        if not item_id:
            return f"You do not have an item matching '{item_query}'."
        item = ITEMS[item_id]
        effects = item.effects
        if not effects:
            return f"{item.name} has no immediate use."
        messages = [f"You use {item.name}."]
        if "heal" in effects:
            before = self.player.hp
            self.player.hp = min(self.max_hp_with_equipment(), self.player.hp + int(effects["heal"]))
            messages.append(f"HP {before} -> {self.player.hp}.")
        if "mana" in effects:
            before = self.player.mana
            self.player.mana = min(self.max_mana_with_equipment(), self.player.mana + int(effects["mana"]))
            messages.append(f"Mana {before} -> {self.player.mana}.")
        if "damage" in effects and self.active_enemy:
            damage = int(effects["damage"])
            self.active_enemy.hp = max(0, self.active_enemy.hp - damage)
            messages.append(f"{self.active_enemy.name} takes {damage} radiant damage.")
        if "flee" in effects and self.active_enemy:
            messages.append("Smoke claws at every eye in the room.")
            if self.rng.randint(1, 100) <= int(effects["flee"]):
                self.active_enemy = None
                messages.append("You escape through the confusion.")
        self.player.remove_item(item_id)
        if self.active_enemy and self.active_enemy.hp <= 0:
            messages.append(self.win_combat())
        return "\n".join(messages)

    def stats(self) -> str:
        attack = self.player_attack()
        defense = self.player_defense()
        speed = self.player_speed()
        lines = [
            f"{self.player.name} - level {self.player.level} {self.player.ancestry} {self.player.class_name}",
            f"Background: {self.player.background}",
            f"XP: {self.player.xp}/{self.next_level_xp()} | Gold: {self.player.gold}",
            f"HP: {self.player.hp}/{self.max_hp_with_equipment()} | Mana: {self.player.mana}/{self.max_mana_with_equipment()}",
            f"Combat: attack {attack}, defense {defense}, speed {speed}",
            "Attributes: " + ", ".join(f"{key} {value}" for key, value in self.player.attributes.items()),
        ]
        if self.player.equipment:
            lines.append("Equipment: " + ", ".join(f"{slot}: {ITEMS[item_id].name}" for slot, item_id in self.player.equipment.items()))
        return "\n".join(lines)

    def rest(self) -> str:
        zone = ZONES[self.player.location]
        if not zone.rest_allowed:
            return "This place is too dangerous to rest."
        self.player.hp = self.max_hp_with_equipment()
        self.player.mana = self.max_mana_with_equipment()
        return f"You rest at {zone.name}. Wounds close, thoughts settle, and the world grows one hour older."

    def search(self) -> str:
        zone = ZONES[self.player.location]
        for secret_id in zone.secrets:
            if secret_id not in self.player.discoveries:
                secret = SECRET_DEFINITIONS[secret_id]
                self.player.discoveries.append(secret_id)
                for item_id, count in secret.get("items", {}).items():
                    self.player.add_item(item_id, int(count))
                lore = secret.get("lore")
                if lore and lore not in self.player.known_lore:
                    self.player.known_lore.append(lore)
                self.player.world_flags[f"secret:{secret_id}"] = True
                items_text = ", ".join(f"{ITEMS[item_id].name} x{count}" for item_id, count in secret.get("items", {}).items())
                if not items_text:
                    items_text = "no items"
                return f"{secret['text']}\nFound: {items_text}\nLore: {lore}"
        return "You search carefully, but find no new secrets here."

    def gather(self, resource_query: str = "") -> str:
        zone = ZONES[self.player.location]
        if not zone.resources:
            return "There is nothing useful to gather here."
        resource_id = None
        if resource_query:
            resource_id = self.find_item_id(resource_query, candidates=zone.resources)
            if not resource_id:
                return f"No local resource matches '{resource_query}'. Available: {', '.join(ITEMS[i].name for i in zone.resources)}."
        else:
            resource_id = self.rng.choice(zone.resources)
        count = 2 if self.rng.random() < 0.25 else 1
        self.player.add_item(resource_id, count)
        return f"You gather {ITEMS[resource_id].name} x{count} from {zone.name}."

    def start_fight(self) -> str:
        zone = ZONES[self.player.location]
        if zone.id == "eldermist_village" and "rats_in_the_cellar" in self.player.active_quests:
            enemy_id = "cellar_rat"
        elif not zone.encounters:
            return "This place has no immediate enemies. That may be the most suspicious thing about it."
        else:
            enemy_id = self.weighted_encounter(zone.encounters)
        template = ENEMIES[enemy_id]
        self.active_enemy = Enemy.from_template(template)
        opening = template.opening_line or self.active_enemy.description
        return (
            f"Encounter: {self.active_enemy.name} (level {self.active_enemy.level}, HP {self.active_enemy.hp})\n"
            f"{opening}\nUse attack, cast <spell>, defend, use <item>, inspect, or flee."
        )

    def _handle_combat_command(self, verb: str, rest: str) -> str:
        if not self.active_enemy:
            return "There is no active fight."
        if verb == "inspect":
            return self.inspect_enemy()
        if verb == "use":
            return self.use_item(rest)
        if verb == "flee":
            return self.flee()
        if verb == "defend":
            return self.enemy_turn(defending=True, prefix="You brace behind guard and terrain.")
        if verb == "cast":
            return self.cast(rest)
        if verb == "attack":
            return self.attack()
        return "Combat command not understood."

    def inspect_enemy(self) -> str:
        enemy = self.active_enemy
        if not enemy:
            return "No enemy to inspect."
        abilities = ", ".join(enemy.abilities) if enemy.abilities else "none"
        return (
            f"{enemy.name}: {enemy.description}\n"
            f"Level {enemy.level}, HP {enemy.hp}/{enemy.max_hp}, attack {enemy.attack}, defense {enemy.defense}, abilities: {abilities}"
        )

    def attack(self) -> str:
        enemy = self.active_enemy
        if not enemy:
            return "You swing at tension and hit only air."
        base = self.player_attack()
        damage = max(1, base + self.rng.randint(0, 6) - enemy.defense)
        crit_chance = 8 + self.player.attributes.get("dexterity", 0)
        critical = self.rng.randint(1, 100) <= crit_chance
        if critical:
            damage = int(damage * 1.75) + 1
        enemy.hp = max(0, enemy.hp - damage)
        crit_text = " Critical hit." if critical else ""
        message = f"You strike {enemy.name} for {damage} damage.{crit_text}"
        if enemy.hp <= 0:
            return f"{message}\n{self.win_combat()}"
        return self.enemy_turn(prefix=message)

    def cast(self, spell: str) -> str:
        spell_key = slugify(spell or "firebolt")
        if spell_key in {"heal", "mend", "blessing"}:
            cost = 6
            if self.player.mana < cost:
                return "You do not have enough mana."
            self.player.mana -= cost
            amount = 10 + self.player.attributes.get("intelligence", 0) + self.player.level * 2
            before = self.player.hp
            self.player.hp = min(self.max_hp_with_equipment(), self.player.hp + amount)
            return self.enemy_turn(prefix=f"You invoke a battlefield blessing. HP {before} -> {self.player.hp}.")
        if spell_key in {"firebolt", "spark", "sunburst", "arcane_bolt"}:
            cost = 5
            if self.player.mana < cost:
                return "You do not have enough mana."
            enemy = self.active_enemy
            if not enemy:
                return "There is no enemy to cast at."
            self.player.mana -= cost
            damage = 8 + self.player.attributes.get("intelligence", 0) * 2 + self.player.level * 2
            if spell_key == "sunburst" and enemy.faction in {"Old Kingdom", "Ashen Covenant"}:
                damage += 8
            enemy.hp = max(0, enemy.hp - damage)
            message = f"You cast {spell_key.replace('_', ' ')}. {enemy.name} takes {damage} damage."
            if enemy.hp <= 0:
                return f"{message}\n{self.win_combat()}"
            return self.enemy_turn(prefix=message)
        return "Known spells: firebolt, sunburst, heal."

    def enemy_turn(self, *, defending: bool = False, prefix: str = "") -> str:
        enemy = self.active_enemy
        if not enemy:
            return prefix
        defense = self.player_defense() + (4 if defending else 0)
        damage = max(1, enemy.attack + self.rng.randint(0, enemy.level + 3) - defense // 2)
        if "regenerate" in enemy.abilities and enemy.hp > 0:
            healed = min(4, enemy.max_hp - enemy.hp)
            enemy.hp += healed
            regen = f" {enemy.name} regenerates {healed} HP."
        else:
            regen = ""
        self.player.hp = max(0, self.player.hp - damage)
        suffix = f"{regen}\n{enemy.name} hits you for {damage}. HP {self.player.hp}/{self.max_hp_with_equipment()}."
        if self.player.hp <= 0:
            suffix += "\nYou collapse. A passing pilgrim drags you back to Eldermist at dawn, poorer but alive."
            self.player.gold = max(0, self.player.gold - 10)
            self.player.location = "eldermist_village"
            self.player.hp = max(1, self.max_hp_with_equipment() // 2)
            self.player.mana = max(0, self.max_mana_with_equipment() // 2)
            self.active_enemy = None
        return f"{prefix}\n{suffix}" if prefix else suffix

    def flee(self) -> str:
        enemy = self.active_enemy
        if not enemy:
            return "There is nothing to flee."
        chance = 45 + self.player_speed() * 2 - enemy.level * 4
        roll = self.rng.randint(1, 100)
        if roll <= chance:
            self.active_enemy = None
            return f"You break away from {enemy.name} and escape into the terrain."
        return self.enemy_turn(prefix=f"You try to flee, but {enemy.name} cuts off the route.")

    def win_combat(self) -> str:
        enemy = self.active_enemy
        if not enemy:
            return "The fight is already over."
        self.player.killed[enemy.template_id] = self.player.killed.get(enemy.template_id, 0) + 1
        lines = [f"{enemy.name} falls."]
        level_text = self.gain_xp(enemy.xp_reward)
        lines.append(f"Gained {enemy.xp_reward} XP.")
        if level_text:
            lines.append(level_text)
        loot = self.roll_loot(enemy)
        if loot:
            for item_id, count in loot.items():
                self.player.add_item(item_id, count)
            lines.append("Loot: " + ", ".join(f"{ITEMS[item_id].name} x{count}" for item_id, count in loot.items()))
        else:
            lines.append("Loot: nothing but hard breathing.")
        self.active_enemy = None
        return "\n".join(lines)

    def roll_loot(self, enemy: Enemy) -> dict[str, int]:
        loot: dict[str, int] = {}
        for item_id, chance in enemy.loot_table:
            if self.rng.random() <= chance:
                loot[item_id] = loot.get(item_id, 0) + 1
        return loot

    def weighted_encounter(self, encounters: tuple[tuple[str, int], ...]) -> str:
        total = sum(weight for _, weight in encounters)
        roll = self.rng.randint(1, total)
        running = 0
        for enemy_id, weight in encounters:
            running += weight
            if roll <= running:
                return enemy_id
        return encounters[-1][0]

    def shop(self) -> str:
        merchants = self.current_merchants()
        if not merchants:
            return "No one nearby is selling anything."
        lines = ["Available goods:"]
        for npc in merchants:
            lines.append(f"{npc.display_name}:")
            for item_id in npc.shop_inventory:
                item = ITEMS[item_id]
                lines.append(f"  - {item.name}: {self.buy_price(item_id)} gold ({item.rarity} {item.type})")
        return "\n".join(lines)

    def buy(self, item_query: str) -> str:
        merchants = self.current_merchants()
        shop_items = tuple(item for npc in merchants for item in npc.shop_inventory)
        item_id = self.find_item_id(item_query, candidates=shop_items)
        if not item_id:
            return f"No local merchant sells '{item_query}'."
        price = self.buy_price(item_id)
        if self.player.gold < price:
            return f"{ITEMS[item_id].name} costs {price} gold. You have {self.player.gold}."
        self.player.gold -= price
        self.player.add_item(item_id)
        return f"Bought {ITEMS[item_id].name} for {price} gold."

    def sell(self, item_query: str) -> str:
        item_id = self.find_item_id(item_query, inventory_only=True)
        if not item_id:
            return f"You do not carry '{item_query}'."
        if item_id in self.player.equipment.values():
            return "Unequip by equipping something else before selling that."
        item = ITEMS[item_id]
        price = max(1, item.value // 2)
        self.player.remove_item(item_id)
        self.player.gold += price
        return f"Sold {item.name} for {price} gold."

    def craft(self, recipe_query: str) -> str:
        recipe_id = self.match_key(recipe_query, RECIPES)
        if not recipe_id:
            return f"No recipe matches '{recipe_query}'. Use 'recipes' to browse known crafting."
        recipe = RECIPES[recipe_id]
        missing = [
            f"{ITEMS[item_id].name} {self.player.inventory.get(item_id, 0)}/{count}"
            for item_id, count in recipe.ingredients.items()
            if self.player.inventory.get(item_id, 0) < count
        ]
        if missing:
            return "Missing ingredients: " + ", ".join(missing)
        for item_id, count in recipe.ingredients.items():
            self.player.remove_item(item_id, count)
        self.player.add_item(recipe.result_item, recipe.result_count)
        return f"Crafted {recipe.name}: {ITEMS[recipe.result_item].name} x{recipe.result_count}."

    def recipes_text(self) -> str:
        lines = ["Known recipes:"]
        for recipe in RECIPES.values():
            ingredients = ", ".join(f"{ITEMS[item_id].name} x{count}" for item_id, count in recipe.ingredients.items())
            lines.append(f"- {recipe.name}: {ingredients} -> {ITEMS[recipe.result_item].name} x{recipe.result_count}")
        return "\n".join(lines)

    def journal(self) -> str:
        lines = [self.quests_text()]
        if self.player.discoveries:
            lines.append("\nDiscoveries:")
            lines.extend(f"- {secret.replace('_', ' ')}" for secret in self.player.discoveries)
        if self.player.known_lore:
            lines.append("\nLore:")
            lines.extend(f"- {lore}" for lore in self.player.known_lore)
        return "\n".join(lines)

    def factions(self) -> str:
        lines = ["Faction reputation:"]
        for faction, description in FACTIONS.items():
            score = self.player.reputation.get(faction, 0)
            lines.append(f"- {faction}: {score:+d} ({self.reputation_rank(score)}) - {description}")
        return "\n".join(lines)

    def current_merchants(self) -> list[Any]:
        zone = ZONES[self.player.location]
        return [NPCS[npc_id] for npc_id in zone.npc_ids if NPCS[npc_id].shop_inventory]

    def buy_price(self, item_id: str) -> int:
        item = ITEMS[item_id]
        zone = ZONES[self.player.location]
        rep = self.player.reputation.get(zone.faction, 0)
        discount = min(0.25, max(0.0, rep * 0.015))
        return max(1, int(item.value * (1.15 - discount)))

    def gain_xp(self, amount: int) -> str:
        self.player.xp += amount
        messages = []
        while self.player.xp >= self.next_level_xp():
            self.player.level += 1
            self.player.max_hp += 6 + self.player.attributes.get("endurance", 0) // 2
            self.player.max_mana += 3 + self.player.attributes.get("intelligence", 0) // 3
            if self.player.level % 2 == 0:
                self.player.attributes["strength"] += 1
                self.player.attributes["endurance"] += 1
            else:
                self.player.attributes["dexterity"] += 1
                self.player.attributes["intelligence"] += 1
            self.player.hp = self.max_hp_with_equipment()
            self.player.mana = self.max_mana_with_equipment()
            messages.append(f"Level up! You are now level {self.player.level}.")
        return " ".join(messages)

    def next_level_xp(self) -> int:
        return self.player.level * 100

    def recalculate_derived_stats(self) -> None:
        self.player.hp = min(self.player.hp, self.max_hp_with_equipment())
        self.player.mana = min(self.player.mana, self.max_mana_with_equipment())

    def equipment_stats(self) -> dict[str, int]:
        totals: dict[str, int] = {}
        for item_id in self.player.equipment.values():
            item = ITEMS[item_id]
            for key, value in item.stats.items():
                totals[key] = totals.get(key, 0) + value
        return totals

    def max_hp_with_equipment(self) -> int:
        return self.player.max_hp + self.equipment_stats().get("max_hp", 0)

    def max_mana_with_equipment(self) -> int:
        stats = self.equipment_stats()
        return self.player.max_mana + stats.get("mana", 0) + stats.get("max_mana", 0)

    def player_attack(self) -> int:
        stats = self.equipment_stats()
        return self.player.attributes.get("strength", 0) + stats.get("attack", 0) + self.player.level * 2

    def player_defense(self) -> int:
        stats = self.equipment_stats()
        return self.player.attributes.get("endurance", 0) // 2 + stats.get("defense", 0) + self.player.level

    def player_speed(self) -> int:
        stats = self.equipment_stats()
        return self.player.attributes.get("dexterity", 0) + stats.get("speed", 0)

    def reputation_rank(self, score: int) -> str:
        if score <= -8:
            return "hostile"
        if score <= -3:
            return "distrusted"
        if score < 3:
            return "neutral"
        if score < 7:
            return "friendly"
        if score < 12:
            return "honored"
        return "revered"

    def find_npc(self, query: str) -> Any | None:
        zone = ZONES[self.player.location]
        query_key = slugify(query)
        for npc_id in zone.npc_ids:
            npc = NPCS[npc_id]
            keys = {slugify(npc.id), slugify(npc.name), slugify(npc.display_name)}
            if query_key in keys or any(query_key and query_key in key for key in keys):
                return npc
        return None

    def find_quest(self, query: str, *, active_only: bool = False) -> Quest | None:
        query_key = slugify(query)
        candidates = self.player.active_quests.keys() if active_only else QUESTS.keys()
        for quest_id in candidates:
            quest = QUESTS[quest_id]
            keys = {slugify(quest.id), slugify(quest.title)}
            if query_key in keys or any(query_key and query_key in key for key in keys):
                return quest
        return None

    def find_item_id(
        self,
        query: str,
        *,
        inventory_only: bool = False,
        candidates: tuple[str, ...] | list[str] | None = None,
    ) -> str | None:
        if not query:
            return None
        query_key = slugify(query)
        if candidates is None:
            candidates = tuple(self.player.inventory) if inventory_only else tuple(ITEMS)
        for item_id in candidates:
            item = ITEMS[item_id]
            keys = {slugify(item.id), slugify(item.name)}
            if query_key in keys or any(query_key and query_key in key for key in keys):
                if inventory_only and self.player.inventory.get(item_id, 0) <= 0:
                    continue
                return item_id
        return None

    def match_key(self, query: str, mapping: dict[str, Any]) -> str | None:
        query_key = slugify(query)
        for key in mapping:
            key_slug = slugify(key)
            if query_key == key_slug or (query_key and query_key in key_slug):
                return key
        return None

    def save(self, path: Path = DEFAULT_SAVE_PATH) -> str:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "player": self.player.to_dict(),
            "world": self.world.to_dict(),
            "active_enemy": self.active_enemy.to_dict() if self.active_enemy else None,
        }
        path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
        return f"Saved game to {path}."

    @classmethod
    def load(cls, path: Path = DEFAULT_SAVE_PATH) -> "GameEngine":
        data = json.loads(path.read_text(encoding="utf-8"))
        engine = cls(Player.from_dict(data["player"]), WorldState.from_dict(data["world"]))
        if data.get("active_enemy"):
            engine.active_enemy = Enemy.from_dict(data["active_enemy"])
        return engine

    def load_into_self(self, path: Path = DEFAULT_SAVE_PATH) -> str:
        if not path.exists():
            return f"No save exists at {path}."
        loaded = self.load(path)
        self.player = loaded.player
        self.world = loaded.world
        self.active_enemy = loaded.active_enemy
        return f"Loaded game from {path}."
