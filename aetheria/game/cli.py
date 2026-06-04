"""The interactive command-line client that ties Aetheria together.

The :class:`Game` drives exploration, conversation, combat, trade, crafting and the
living-world simulation.  Input and output are injectable (``read`` / ``out``) so the
same game can be played interactively or driven by a scripted command source for
demos and tests.
"""

from __future__ import annotations

import os
from typing import Callable

from ..character import NPC, Player
from ..combat import ActionType, Battle, CombatAction
from ..economy import format_coins
from ..items import EquipSlot
from ..quest import ObjectiveType
from ..simulation import Simulation
from ..state import World
from ..stats import Attribute
from .. import persistence
from .factory import create_player, START_LOCATION

SAVE_DIR = os.path.join(os.path.expanduser("~"), ".aetheria", "saves")

BANNER = r"""
   _    _____ _____ _   _ _____ ____  ___    _
  / \  | ____|_   _| | | | ____|  _ \|_ _|  / \
 / _ \ |  _|   | | | |_| |  _| | |_) || |  / _ \
/ ___ \| |___  | | |  _  | |___|  _ < | | / ___ \
\_/   \_\_____| |_| |_| |_|_____|_| \_\___/_/   \_\

        A living medieval-fantasy world simulator
"""

HELP_TEXT = """
Commands
  Exploration
    look (l)              describe where you stand
    go <exit> / <dir>     travel through an exit (e.g. 'go north', 'go tavern')
    map                   show this region and known exits
    explore / search      search the area (find secrets; risk an encounter)
    gather / mine         harvest herbs / ore at the right spot
    rest [hours]          wait and recover (time passes)
  People
    talk <name>           speak with someone here
    who / npcs            list who is present
  Character
    status (st)           your character sheet
    inventory (i)         your belongings
    equip <item>          wear or wield an item
    unequip <slot>        remove equipped gear
    use <item>            use a consumable
    abilities (ab)        list your skills and spells
  Quests & World
    journal (j)           your active quests
    rumors               rumours you've heard
    news / chronicle      headlines from across the realm
    recipes              what you can craft here
    craft <recipe>        craft an item at a station
    time                 the date and hour
  System
    save [slot] / load [slot]
    help (h)             this list
    quit / exit
"""


class Game:
    def __init__(self, world: World, out: Callable[[str], None] = print,
                 read: Callable[[str], str] | None = None) -> None:
        self.world = world
        self.sim = Simulation(world)
        self.out = out
        self._read = read or input
        self.running = True
        self.commands = self._build_dispatch()

    # -- io helpers ----------------------------------------------------------
    def say(self, text: str = "") -> None:
        self.out(text)

    def read(self, prompt: str = "> ") -> str:
        try:
            return self._read(prompt)
        except EOFError:
            return "quit"

    @property
    def player(self) -> Player:
        return self.world.player

    @property
    def here(self):
        return self.world.map.get_location(self.player.location_id)

    # =====================================================================
    #  Setup
    # =====================================================================
    def title_screen(self) -> None:
        self.say(BANNER)
        self.say("Type 'help' at any time for commands.\n")

    def create_character_interactive(self) -> None:
        self.say("Forge your legend.\n")
        name = self.read("What is your name, adventurer? ").strip() or "Aerith"
        classes = self.world.classes.all()
        self.say("\nChoose your calling:")
        for idx, cls in enumerate(classes, 1):
            self.say(f"  {idx}) {cls.name} — {cls.description}")
        choice = ""
        while True:
            choice = self.read("\nClass (number or name): ").strip().lower()
            selected = self._match_class(choice, classes)
            if selected:
                break
            self.say("I don't know that calling. Try again.")
        create_player(self.world, name, selected.id)
        self.say(f"\nWelcome to Aldermere, {name} the {selected.name}.\n")
        self.describe_location(full=True)

    def _match_class(self, choice: str, classes):
        if choice.isdigit():
            idx = int(choice) - 1
            if 0 <= idx < len(classes):
                return classes[idx]
            return None
        for cls in classes:
            if cls.id == choice or cls.name.lower() == choice or choice in cls.name.lower():
                return cls
        return None

    def start_new(self, name: str | None = None, class_id: str | None = None) -> None:
        if name and class_id:
            create_player(self.world, name, class_id)
            self.say(f"Welcome to Aldermere, {name}.\n")
            self.describe_location(full=True)
        else:
            self.create_character_interactive()

    # =====================================================================
    #  Time & world
    # =====================================================================
    def pass_time(self, hours: int, announce_news: bool = True) -> None:
        log = self.sim.advance(hours)
        # gentle player regeneration while time passes
        self.player.restore_stamina(2 * hours)
        self.player.restore_mana(1 * hours)
        self.player.heal(2 * hours)
        if announce_news:
            for line in log:
                if line.startswith("[NEWS]"):
                    self.say(line)

    # =====================================================================
    #  Description
    # =====================================================================
    def describe_location(self, full: bool = False) -> None:
        loc = self.here
        region = self.world.map.get_region(loc.region_id)
        self.player.discovered_locations.add(loc.id)
        self.say(f"\n=== {loc.name} — {region.name} ===")
        self.say(f"[{self.world.clock.stamp()}]")
        self.say(loc.description)
        if full and loc.discovered_desc:
            self.say(loc.discovered_desc)
        if loc.ambient:
            self.say(self.world.rng.choice(loc.ambient))
        # people
        present = [n for n in self.world.living_npcs_at(loc.id) if n.id != "player"]
        if present:
            names = ", ".join(self._npc_label(n) for n in present)
            self.say(f"Here: {names}")
        # exits
        exits = loc.exits
        if exits:
            pretty = ", ".join(f"{name} (-> {self.world.map.get_location(dest).name})"
                               for name, dest in exits.items())
            self.say(f"Exits: {pretty}")
        if not loc.is_safe:
            self.say("(This place feels dangerous.)")

    def _npc_label(self, npc: NPC) -> str:
        tag = "merchant" if npc.is_merchant else npc.role
        mood = npc.mood.value
        return f"{npc.name} [{tag}, {mood}]"

    # =====================================================================
    #  Command dispatch
    # =====================================================================
    def _build_dispatch(self) -> dict:
        d = {
            "look": self.cmd_look, "l": self.cmd_look,
            "go": self.cmd_go, "move": self.cmd_go, "travel": self.cmd_go,
            "north": self.cmd_go, "south": self.cmd_go, "east": self.cmd_go,
            "west": self.cmd_go, "up": self.cmd_go, "out": self.cmd_go,
            "map": self.cmd_map,
            "explore": self.cmd_explore, "search": self.cmd_explore,
            "gather": self.cmd_gather, "mine": self.cmd_gather,
            "rest": self.cmd_rest, "wait": self.cmd_rest,
            "talk": self.cmd_talk, "speak": self.cmd_talk,
            "who": self.cmd_who, "npcs": self.cmd_who,
            "status": self.cmd_status, "st": self.cmd_status, "char": self.cmd_status,
            "inventory": self.cmd_inventory, "inv": self.cmd_inventory, "i": self.cmd_inventory,
            "equip": self.cmd_equip, "wield": self.cmd_equip, "wear": self.cmd_equip,
            "unequip": self.cmd_unequip, "remove": self.cmd_unequip,
            "use": self.cmd_use, "drink": self.cmd_use, "eat": self.cmd_use,
            "abilities": self.cmd_abilities, "ab": self.cmd_abilities, "spells": self.cmd_abilities,
            "journal": self.cmd_journal, "j": self.cmd_journal, "quests": self.cmd_journal,
            "rumors": self.cmd_rumors, "rumours": self.cmd_rumors,
            "news": self.cmd_news, "chronicle": self.cmd_news,
            "recipes": self.cmd_recipes, "craft": self.cmd_craft,
            "time": self.cmd_time,
            "save": self.cmd_save, "load": self.cmd_load,
            "help": self.cmd_help, "h": self.cmd_help, "?": self.cmd_help,
            "quit": self.cmd_quit, "exit": self.cmd_quit,
        }
        return d

    def dispatch(self, line: str) -> None:
        line = line.strip()
        if not line:
            return
        parts = line.split()
        verb = parts[0].lower()
        args = parts[1:]
        # bare-direction shortcuts pass the verb itself as the argument
        if verb in ("north", "south", "east", "west", "up", "out") and not args:
            args = [verb]
        handler = self.commands.get(verb)
        if handler is None:
            self.say(f"I don't understand '{verb}'. Try 'help'.")
            return
        handler(args)

    # =====================================================================
    #  Exploration commands
    # =====================================================================
    def cmd_look(self, args) -> None:
        self.describe_location(full=True)

    def cmd_map(self, args) -> None:
        loc = self.here
        region = self.world.map.get_region(loc.region_id)
        self.say(f"\n--- {region.name} ---")
        self.say(region.description)
        self.say(f"You are at: {loc.name}")
        self.say("Known places nearby:")
        for name, dest in loc.exits.items():
            target = self.world.map.get_location(dest)
            seen = "visited" if dest in self.player.discovered_locations else "unexplored"
            self.say(f"  {name:>10} -> {target.name} ({target.terrain.value}, {seen})")

    def cmd_go(self, args) -> None:
        if not args:
            self.say("Go where? (try 'look' for exits)")
            return
        direction = " ".join(args)
        dest_id = self.world.map.resolve_exit(self.player.location_id, direction)
        if not dest_id:
            self.say(f"There's no way to '{direction}' from here.")
            return
        dest = self.world.map.get_location(dest_id)
        self.say(f"You travel to {dest.name}...")
        self.pass_time(max(1, dest.travel_hours))
        self.player.location_id = dest_id
        first_visit = dest_id not in self.player.discovered_locations
        self.player.discovered_locations.add(dest_id)
        # quest: reaching a location
        for line in self.world.quest_manager.record_event(self.player, ObjectiveType.REACH, dest_id):
            self.say(line)
        self.describe_location(full=first_visit)
        self._maybe_encounter(dest)

    def cmd_rest(self, args) -> None:
        hours = 6
        if args and args[0].isdigit():
            hours = max(1, min(24, int(args[0])))
        self.say(f"You rest for {hours} hours...")
        if self.here.is_safe:
            self.player.full_restore()
            self.say("You wake refreshed, fully restored.")
        else:
            self.player.heal(6 * hours)
            self.player.restore_stamina(5 * hours)
            self.player.restore_mana(4 * hours)
            self.say("You rest fitfully, one eye open.")
        self.pass_time(hours)
        self.cmd_status([])

    def cmd_explore(self, args) -> None:
        loc = self.here
        self.pass_time(1)
        found_something = False
        for poi in loc.points_of_interest:
            reward = self._search_poi(poi)
            if reward:
                found_something = True
        if not found_something:
            self.say("You search the area but find nothing of note.")
        self._maybe_encounter(loc, force_chance=0.5)

    def _search_poi(self, poi: str) -> bool:
        player = self.world.items
        key = f"{self.here.id}:{poi}"
        once = poi in ("altar", "relic_pedestal", "hoard", "reliquary")
        if once and key in self.player.looted_pois:
            return False
        rewards = {
            "altar": ("ancient_tome", 1, "Hidden beneath the altar stone, you find an Ancient Tome!"),
            "relic_pedestal": ("sunken_relic", 1, "On the drowned pedestal rests the Sunken Relic. You take it."),
            "hoard": ("gold_idol", 1, "You pry a Golden Idol from the great hoard."),
            "reliquary": ("ancient_coin", 5, "The reliquary yields a handful of ancient coins."),
        }
        if poi in rewards and self.here.id in ("old_shrine", "sunken_ruins", "dragon_lair", "cathedral"):
            item_id, qty, msg = rewards[poi]
            # gate the tome/relic to the right ruins
            valid = (
                (poi == "altar" and self.here.id == "old_shrine") or
                (poi == "relic_pedestal" and self.here.id == "sunken_ruins") or
                (poi == "hoard" and self.here.id == "dragon_lair") or
                (poi == "reliquary" and self.here.id == "cathedral")
            )
            if not valid:
                return False
            self.player.inventory.add(item_id, qty)
            self.say(msg)
            if once:
                self.player.looted_pois.add(key)
            return True
        return False

    def cmd_gather(self, args) -> None:
        loc = self.here
        rng = self.world.rng
        self.pass_time(1)
        found = []
        if "ore_vein" in loc.points_of_interest:
            for _ in range(rng.randint(1, 3)):
                found.append(rng.choices(["iron_ore", "coal"], weights=[2, 1])[0])
        if "gem_vein" in loc.points_of_interest:
            if rng.chance(0.5):
                found.append(rng.choices(["ruby", "mana_crystal"], weights=[1, 1])[0])
        terrain = loc.terrain.value
        if terrain in ("forest", "plains", "swamp") and not loc.is_safe:
            if self.world.clock.is_night and terrain == "forest":
                found += ["moonpetal"] * rng.randint(1, 2)
            if rng.chance(0.6):
                found.append(rng.choices(["redroot", "moonpetal", "linen"],
                                         weights=[3, 1, 1])[0])
        if not found:
            self.say("There's nothing to gather here.")
            return
        for item_id in found:
            self.player.inventory.add(item_id, 1)
        names = ", ".join(self.world.items.get(i).name for i in found)
        self.say(f"You gather: {names}.")
        self._maybe_encounter(loc, force_chance=0.3)

    # =====================================================================
    #  Encounters & combat
    # =====================================================================
    def _maybe_encounter(self, loc, force_chance: float | None = None) -> None:
        if loc.is_safe or not loc.spawn_table:
            return
        base = 0.18 + 0.06 * loc.terrain.danger
        chance = force_chance if force_chance is not None else base
        if not self.world.rng.chance(chance):
            return
        templates = [t for t, _ in loc.spawn_table]
        weights = [w for _, w in loc.spawn_table]
        count = 1
        if self.world.rng.chance(0.35):
            count = self.world.rng.randint(2, 3)
        monsters = []
        for _ in range(count):
            tid = self.world.rng.choices(templates, weights=weights)[0]
            m = self.world.spawn_monster(tid)
            if m:
                m.template_id = tid
                monsters.append(m)
        if monsters:
            names = ", ".join(m.name for m in monsters)
            self.say(f"\n!!! Ambush! You are set upon by {names}!")
            self.run_combat(monsters)

    def run_combat(self, enemies: list[NPC]) -> str:
        battle = Battle([self.player], enemies, self.world.abilities, self.world.rng)
        battle.begin_round()
        self._flush(battle)
        while not battle.over:
            order = battle.turn_order()
            for actor in order:
                if battle.over or not actor.alive:
                    continue
                if actor is self.player:
                    self._player_combat_turn(battle)
                else:
                    battle.perform(battle.choose_ai_action(actor))
                self._flush(battle)
                if battle.player_won() or battle.player_lost():
                    battle.over = True
                    break
            if battle.over:
                break
            battle.end_round()
            self._flush(battle)
            if not battle.over:
                battle.begin_round()
                self._flush(battle)
        return self._resolve_combat(battle, enemies)

    def _flush(self, battle: Battle) -> None:
        for line in battle.drain_log():
            self.say(line)

    def _player_combat_turn(self, battle: Battle) -> None:
        if self.player.is_stunned():
            return
        self._combat_status(battle)
        while True:
            raw = self.read("battle> ").strip().lower()
            if not raw:
                continue
            parts = raw.split()
            verb, rest = parts[0], parts[1:]
            enemies = battle.living(battle.enemies)
            if verb in ("attack", "a", "hit"):
                target = self._pick_target(rest, enemies)
                battle.perform(CombatAction(self.player, ActionType.ATTACK, target=target))
                return
            if verb in ("cast", "use", "ability", "skill") and rest:
                self._combat_ability(battle, rest, enemies)
                return
            if verb in ("item", "drink", "quaff") and rest:
                item_id = self._find_item(" ".join(rest))
                if item_id:
                    battle.perform(CombatAction(self.player, ActionType.ITEM, item_id=item_id))
                    return
                self.say("You don't have that.")
                continue
            if verb in ("defend", "d", "block"):
                battle.perform(CombatAction(self.player, ActionType.DEFEND))
                return
            if verb in ("flee", "run", "escape"):
                battle.perform(CombatAction(self.player, ActionType.FLEE))
                return
            if verb in ("look", "status", "s"):
                self._combat_status(battle)
                continue
            if verb in ("abilities", "ab", "spells"):
                self._list_combat_abilities()
                continue
            if verb in ("help", "h", "?"):
                self.say("Battle: attack [foe] | cast <ability> [foe] | item <name> | defend | flee")
                continue
            self.say("Unknown battle command. (attack / cast / item / defend / flee / help)")

    def _combat_ability(self, battle, rest, enemies) -> None:
        ability_name = rest[0]
        ability = self._find_ability(ability_name)
        if not ability:
            self.say("You don't know that ability.")
            return self._player_combat_turn(battle)
        if not self.player.can_use(ability):
            self.say(f"You can't use {ability.name} (not enough resource or on cooldown).")
            return self._player_combat_turn(battle)
        target = None
        if ability.is_offensive and not ability.aoe:
            target = self._pick_target(rest[1:], enemies)
        elif ability.heal or ability.shield or ability.target.value in ("self", "ally"):
            target = self.player
        battle.perform(CombatAction(self.player, ActionType.ABILITY, target=target, ability=ability))

    def _pick_target(self, tokens, enemies):
        if not enemies:
            return None
        if tokens:
            name = " ".join(tokens)
            for e in enemies:
                if name in e.name.lower():
                    return e
        return min(enemies, key=lambda e: e.health)

    def _combat_status(self, battle: Battle) -> None:
        p = self.player
        self.say(f"  [You] HP {p.health}/{p.max_health}  MP {p.mana}/{p.max_mana}  "
                 f"SP {p.stamina}/{p.max_stamina}"
                 + (f"  ({', '.join(e.name for e in p.effects)})" if p.effects else ""))
        for e in battle.living(battle.enemies):
            fx = f" [{', '.join(x.name for x in e.effects)}]" if e.effects else ""
            self.say(f"  [Foe] {e.name}: {e.health}/{e.max_health} HP{fx}")

    def _list_combat_abilities(self) -> None:
        for aid in self.player.abilities:
            ab = self.world.abilities.get(aid)
            ready = "ready" if self.player.can_use(ab) else "unavailable"
            self.say(f"  {ab.name} — {ab.describe()} [{ready}]")

    def _resolve_combat(self, battle: Battle, enemies: list[NPC]) -> str:
        if battle.fled:
            self.say("You escaped with your life.")
            return "fled"
        if battle.player_lost():
            self.say("\nDarkness takes you... You have fallen in battle.")
            self.say("(You awaken later at the Temple of the Dawn, weakened but alive.)")
            self.player.full_restore()
            self.player.health = max(1, self.player.max_health // 2)
            lost = self.player.gold // 4
            self.player.gold -= lost
            if lost:
                self.say(f"You lost {format_coins(lost)} recovering.")
            self.player.location_id = "temple"
            return "lost"
        # victory
        self.say("\nVictory!")
        total_xp = 0
        for enemy in enemies:
            total_xp += enemy.xp_reward
            self.player.gold += enemy.gold
            tid = getattr(enemy, "template_id", enemy.id)
            self.player.kills[tid] = self.player.kills.get(tid, 0) + 1
            for line in self.world.quest_manager.record_event(self.player, ObjectiveType.KILL, tid):
                self.say(line)
            # loot
            for item_id, prob in enemy.loot_table:
                if self.world.rng.chance(prob):
                    self.player.inventory.add(item_id, 1)
                    self.say(f"  Loot: {self.world.items.get(item_id).name}")
        if any(e.gold for e in enemies):
            self.say(f"  You scavenge {format_coins(sum(e.gold for e in enemies))}.")
        for line in self.player.add_xp(total_xp):
            self.say("  " + line)
        self.say(f"  Gained {total_xp} XP.")
        self._check_new_abilities()
        return "won"

    def _check_new_abilities(self) -> None:
        """Auto-learn class abilities unlocked by the new level."""
        cls = self.world.classes.get(self.player.char_class)
        # learn any starting-tree ability that becomes available; here we simply
        # surface a hint — explicit learning happens via quests/trainers.
        return

    # =====================================================================
    #  Social / dialogue
    # =====================================================================
    def cmd_who(self, args) -> None:
        present = [n for n in self.world.living_npcs_at(self.player.location_id)]
        if not present:
            self.say("There is no one here to talk to.")
            return
        for n in present:
            self.say(f"  {self._npc_label(n)} — {n.disposition.value} toward you")

    def cmd_talk(self, args) -> None:
        if not args:
            self.say("Talk to whom?")
            return
        name = " ".join(args)
        npc = self.world.find_npc_by_name(name, self.player.location_id)
        if not npc:
            self.say(f"There's no one called '{name}' here.")
            return
        self.converse(npc)

    def converse(self, npc: NPC) -> None:
        engine = self.world.dialogue
        self.say("")
        self.say(engine.greeting(npc, self.player, self.world.clock))
        npc.remember(self.world.clock.day_index, "spoke with the adventurer")
        while True:
            topics = engine.available_topics(npc, self.player)
            # offer to turn in completed quests for this NPC
            ready = self.world.quest_manager.completable_for(self.player, npc.id)
            self.say("")
            for idx, topic in enumerate(topics, 1):
                self.say(f"  {idx}) {topic.label}")
            base = len(topics)
            for j, qid in enumerate(ready, 1):
                quest = self.world.quests.get(qid)
                self.say(f"  {base + j}) [Turn in] {quest.name}")
            choice = self.read("say> ").strip().lower()
            if choice in ("bye", "leave", "farewell", "exit", "back", ""):
                self.say(engine.handle(npc, self.player, self.world.clock, "farewell",
                                       world=self.world).lines[0])
                break
            if not choice.isdigit():
                # allow typing the topic key directly
                matched = next((t for t in topics if t.key == choice), None)
                if not matched:
                    self.say("(choose a number)")
                    continue
                index = topics.index(matched) + 1
            else:
                index = int(choice)
            if 1 <= index <= base:
                topic = topics[index - 1]
                if self._handle_topic(npc, topic):
                    break
            elif base < index <= base + len(ready):
                qid = ready[index - base - 1]
                for line in self.world.quest_manager.turn_in(self.player, qid, self.world):
                    self.say(line)
                npc.adjust_relationship(6)
                npc.remember(self.world.clock.day_index,
                             f"was helped with '{self.world.quests.get(qid).name}'", weight=3)
            else:
                self.say("(choose a listed number)")

    def _handle_topic(self, npc: NPC, topic) -> bool:
        engine = self.world.dialogue
        gift_item = None
        if topic.key == "gift":
            gift_item = self._choose_gift()
            if gift_item is None:
                self.say("(You decide not to give anything.)")
                return False
        result = engine.handle(npc, self.player, self.world.clock, topic.key,
                               world=self.world, gift_item=gift_item)
        for line in result.lines:
            self.say(line)
        if result.learned_rumor and result.learned_rumor not in self.player.journal:
            tag = f"Rumour: {result.learned_rumor}"
            if tag not in self.player.journal:
                self.player.journal.append(tag)
        if result.offered_quest:
            self._offer_quest(npc, result.offered_quest)
        if result.opened_trade:
            self.trade_with(npc)
        if result.started_combat:
            monster = npc
            monster.template_id = npc.id
            self.run_combat([monster])
            return True
        return result.ended

    def _offer_quest(self, npc: NPC, quest_id: str) -> None:
        if not self.world.quests.exists(quest_id):
            return
        quest = self.world.quests.get(quest_id)
        if not self.world.quest_manager.can_start(self.player, quest_id):
            if quest_id in self.player.active_quests:
                self.say("(You've already accepted this task.)")
            return
        self.say(f"\n  QUEST: {quest.name}")
        self.say(f"  {quest.summary}")
        ans = self.read("  Accept this quest? (y/n) ").strip().lower()
        if ans in ("y", "yes"):
            for line in self.world.quest_manager.start(self.player, quest_id):
                self.say("  " + line)
            npc.adjust_relationship(3)
        else:
            self.say("  (Perhaps another time.)")

    def _choose_gift(self):
        items = self.player.inventory.items()
        if not items:
            self.say("You have nothing to give.")
            return None
        self.say("  Give what?")
        for idx, (tmpl, qty) in enumerate(items, 1):
            self.say(f"    {idx}) {tmpl.name} x{qty}")
        ans = self.read("  gift> ").strip().lower()
        if ans.isdigit():
            i = int(ans) - 1
            if 0 <= i < len(items):
                return items[i][0].id
        item_id = self._find_item(ans)
        return item_id

    # =====================================================================
    #  Trade
    # =====================================================================
    def trade_with(self, npc: NPC) -> None:
        trade = self.world.trade
        self.say(f"\n--- {npc.name}'s Wares --- (your purse: {format_coins(self.player.gold)})")
        while True:
            self.say("\n  For sale:")
            for idx, item_id in enumerate(npc.shop_inventory, 1):
                q = trade.quote(self.world.items, item_id, self.player, npc)
                self.say(f"    {idx}) {q.item.name} — {format_coins(q.buy_price)}  "
                         f"({q.item.describe()})")
            self.say("  Commands: buy <number/name> [qty] | sell <item> [qty] | "
                     "list | done")
            raw = self.read("trade> ").strip().lower()
            if raw in ("done", "leave", "exit", "back", ""):
                self.say(f"{npc.name}: \"Pleasure doing business.\"")
                return
            parts = raw.split()
            verb = parts[0]
            if verb == "list":
                continue
            if verb == "buy" and len(parts) >= 2:
                item_id = self._resolve_shop_item(parts[1], npc)
                qty = int(parts[2]) if len(parts) > 2 and parts[2].isdigit() else 1
                if not item_id:
                    self.say("They don't sell that.")
                    continue
                ok, msg = trade.buy(self.world.items, item_id, self.player, npc, qty)
                self.say("  " + msg)
            elif verb == "sell" and len(parts) >= 2:
                item_id = self._find_item(" ".join(parts[1:]))
                qty = 1
                if parts[-1].isdigit():
                    qty = int(parts[-1])
                    item_id = self._find_item(" ".join(parts[1:-1]))
                if not item_id:
                    self.say("You don't have that.")
                    continue
                ok, msg = trade.sell(self.world.items, item_id, self.player, npc, qty)
                self.say("  " + msg)
            else:
                self.say("  (buy <item> [qty] | sell <item> [qty] | done)")

    def _resolve_shop_item(self, token: str, npc: NPC):
        if token.isdigit():
            i = int(token) - 1
            if 0 <= i < len(npc.shop_inventory):
                return npc.shop_inventory[i]
            return None
        for item_id in npc.shop_inventory:
            if token in self.world.items.get(item_id).name.lower() or token == item_id:
                return item_id
        return None

    # =====================================================================
    #  Character commands
    # =====================================================================
    def cmd_status(self, args) -> None:
        p = self.player
        ds = p.derived_stats()
        cls = self.world.classes.get(p.char_class)
        self.say(f"\n=== {p.name}, the {p.play_title} ({cls.name}) ===")
        self.say(f"Level {p.level}  XP {p.xp}  Gold {format_coins(p.gold)}")
        self.say(f"HP {p.health}/{ds.max_health}  MP {p.mana}/{ds.max_mana}  "
                 f"SP {p.stamina}/{ds.max_stamina}")
        self.say("Attributes: " + "  ".join(
            f"{a.value[:3].upper()} {p.attrs.get(a)}" for a in Attribute))
        self.say(f"Attack {ds.attack}  SpellPower {ds.spell_power}  Defense {ds.defense}  "
                 f"Acc {ds.accuracy}  Eva {ds.evasion}  Crit {int(ds.crit_chance*100)}%")
        eq = p.inventory.equipment
        if eq:
            self.say("Equipped:")
            for slot, item_id in eq.items():
                self.say(f"  {slot.value:>10}: {self.world.items.get(item_id).name}")
        if p.professions:
            self.say("Professions: " + ", ".join(f"{k} {v}" for k, v in p.professions.items()))
        if p.effects:
            self.say("Effects: " + ", ".join(e.name for e in p.effects))
        if p.reputation:
            from ..faction import Standing
            reps = []
            for fid, score in p.reputation.items():
                fac = self.world.factions.get(fid)
                fname = fac.name if fac else fid
                reps.append(f"{fname}: {Standing.from_score(score).value}")
            self.say("Standing: " + " | ".join(reps))

    def cmd_inventory(self, args) -> None:
        inv = self.player.inventory
        items = inv.items()
        self.say(f"\n=== Inventory ({inv.total_weight()}/"
                 f"{self.player.derived_stats().carry_capacity} weight) ===")
        self.say(f"Purse: {format_coins(self.player.gold)}")
        if not items:
            self.say("(empty)")
            return
        for tmpl, qty in sorted(items, key=lambda x: x[0].item_type.value):
            mark = "*" if tmpl.id in inv.equipment.values() else " "
            qtxt = f" x{qty}" if qty > 1 else ""
            self.say(f" {mark}[{tmpl.item_type.value:>10}] {tmpl.name}{qtxt} — {tmpl.describe()}")

    def cmd_equip(self, args) -> None:
        if not args:
            self.say("Equip what?")
            return
        item_id = self._find_item(" ".join(args))
        if not item_id:
            self.say("You don't carry that.")
            return
        ok, msg = self.player.inventory.equip(item_id)
        self.say(msg)

    def cmd_unequip(self, args) -> None:
        if not args:
            self.say("Unequip which slot? " + ", ".join(s.value for s in EquipSlot))
            return
        token = args[0].lower()
        slot = next((s for s in EquipSlot if s.value == token or token in s.value), None)
        if not slot:
            self.say("No such slot.")
            return
        ok, msg = self.player.inventory.unequip(slot)
        self.say(msg)

    def cmd_use(self, args) -> None:
        if not args:
            self.say("Use what?")
            return
        item_id = self._find_item(" ".join(args))
        if not item_id:
            self.say("You don't have that.")
            return
        tmpl = self.world.items.get(item_id)
        if tmpl.item_type.value not in ("consumable", "food"):
            self.say(f"You can't use {tmpl.name} that way.")
            return
        self.player.inventory.remove(item_id, 1)
        notes = []
        if tmpl.heal_amount:
            notes.append(f"recover {self.player.heal(tmpl.heal_amount)} HP")
        if tmpl.mana_amount:
            self.player.restore_mana(tmpl.mana_amount)
            notes.append(f"restore {tmpl.mana_amount} mana")
        if tmpl.stamina_amount:
            self.player.restore_stamina(tmpl.stamina_amount)
            notes.append(f"restore {tmpl.stamina_amount} stamina")
        if tmpl.effect:
            from ..effects import StatusEffect
            self.player.add_effect(StatusEffect.create(tmpl.effect))
            notes.append(f"gain {tmpl.effect}")
        self.say(f"You use {tmpl.name}" + (": " + ", ".join(notes) if notes else "."))

    def cmd_abilities(self, args) -> None:
        if not self.player.abilities:
            self.say("You have no special abilities yet.")
            return
        self.say("\n=== Abilities ===")
        for aid in self.player.abilities:
            ab = self.world.abilities.get(aid)
            self.say(f"  {ab.name}: {ab.describe()}")

    # =====================================================================
    #  Quests / world info
    # =====================================================================
    def cmd_journal(self, args) -> None:
        self.say("\n=== Quest Journal ===")
        for line in self.world.quest_manager.journal_lines(self.player):
            self.say(line)
        if self.player.completed_quests:
            self.say(f"Completed: {len(self.player.completed_quests)} quest(s).")

    def cmd_rumors(self, args) -> None:
        heard = [j for j in self.player.journal if j.startswith("Rumour:")]
        self.say("\n=== Rumours You've Heard ===")
        if not heard:
            self.say("(Talk to people and ask for news.)")
        for r in heard[-10:]:
            self.say("  - " + r[len("Rumour: "):])

    def cmd_news(self, args) -> None:
        self.say("\n=== Chronicle of Aldermere ===")
        if not self.world.chronicle:
            self.say("(The realm has been quiet... so far.)")
        for line in self.world.chronicle[-12:]:
            self.say("  " + line)

    def cmd_time(self, args) -> None:
        self.say(self.world.clock.stamp())
        self.say(self.world.clock.season.flavour)

    def cmd_recipes(self, args) -> None:
        stations = set(self.here.points_of_interest)
        recipes = self.world.recipes.craftable_at(stations)
        self.say("\n=== Recipes you can make here ===")
        if not recipes:
            self.say("(No crafting station here. Try a forge, alchemy table, loom or cookfire.)")
            return
        for r in recipes:
            ok, _ = self.world.crafting.can_craft(self.player, r.id, stations)
            mark = "+" if ok else "-"
            self.say(f" {mark} {r.id}: {r.describe(self.world.items)}")

    def cmd_craft(self, args) -> None:
        if not args:
            self.say("Craft what? (see 'recipes')")
            return
        recipe_id = args[0]
        stations = set(self.here.points_of_interest)
        ok, msg = self.world.crafting.craft(self.player, recipe_id, stations)
        self.say(msg)
        if ok:
            self.pass_time(1)

    # =====================================================================
    #  System
    # =====================================================================
    def cmd_save(self, args) -> None:
        slot = args[0] if args else "save1"
        path = os.path.join(SAVE_DIR, f"{slot}.json")
        persistence.save(self.world, path)
        self.say(f"Game saved to slot '{slot}'.")

    def cmd_load(self, args) -> None:
        slot = args[0] if args else "save1"
        path = os.path.join(SAVE_DIR, f"{slot}.json")
        if not os.path.exists(path):
            self.say(f"No save in slot '{slot}'.")
            return
        from ..content import build_world
        self.world = persistence.load(path, build_world)
        self.sim = Simulation(self.world)
        self.say(f"Loaded slot '{slot}'.")
        self.describe_location()

    def cmd_help(self, args) -> None:
        self.say(HELP_TEXT)

    def cmd_quit(self, args) -> None:
        self.say("\nMay your road be ever golden. Farewell.")
        self.running = False

    # =====================================================================
    #  Lookups
    # =====================================================================
    def _find_item(self, name: str):
        name = name.strip().lower()
        for tmpl, _ in self.player.inventory.items():
            if tmpl.id == name or name == tmpl.name.lower():
                return tmpl.id
        for tmpl, _ in self.player.inventory.items():
            if name in tmpl.name.lower():
                return tmpl.id
        return None

    def _find_ability(self, name: str):
        name = name.strip().lower()
        for aid in self.player.abilities:
            ab = self.world.abilities.get(aid)
            if ab.id == name or name == ab.name.lower():
                return ab
        for aid in self.player.abilities:
            ab = self.world.abilities.get(aid)
            if name in ab.name.lower():
                return ab
        return None

    # =====================================================================
    #  Main loop
    # =====================================================================
    def loop(self) -> None:
        while self.running:
            if not self.player.alive:
                self.player.full_restore()
            line = self.read(f"\n[{self.world.clock.time_of_day.value}] > ")
            self.dispatch(line)
