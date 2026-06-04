"""simulation_engine.py — the orchestrator main loop for the fantasy simulator.

This is the conductor. It owns the tick loop, routes every creative act to the right
model via :class:`LLMClient`, adjudicates mechanics with :class:`Dice`, and keeps
``world_state.json`` + ``characters/`` as the single, resumable source of truth.

Run it::

    python -m fantasy_simulator.simulation_engine --simulate 24      # autonomous
    python -m fantasy_simulator.simulation_engine --play             # interactive
    python -m fantasy_simulator.simulation_engine --reset --seed foo # (re)generate world
    python -m fantasy_simulator.simulation_engine --provider mock    # force a provider
"""

from __future__ import annotations

import argparse
import json
import os
import sys

# Allow both "python -m fantasy_simulator.simulation_engine" and direct execution.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fantasy_simulator import (CHARACTERS_DIR, LOGS_DIR, PROMPTS_DIR, RULES_DIR,
                               WORLD_STATE_PATH)
from fantasy_simulator.utils import (ContextBuilder, Dice, LLMClient, MemoryManager,
                                     StateStore, get_logger)
from fantasy_simulator.utils import engine_bridge

ASSIGNMENTS_PATH = os.path.join(PROMPTS_DIR, "model_assignments.json")

SEASONS = ["Spring", "Summer", "Autumn", "Winter"]


def _time_of_day(hour: int) -> str:
    if 5 <= hour < 7:
        return "Dawn"
    if 7 <= hour < 11:
        return "Morning"
    if 11 <= hour < 13:
        return "Noon"
    if 13 <= hour < 17:
        return "Afternoon"
    if 17 <= hour < 20:
        return "Dusk"
    if 20 <= hour < 24:
        return "Night"
    return "Midnight"


def _mood_label(score: int) -> str:
    if score <= -60:
        return "angry"
    if score <= -25:
        return "grumpy"
    if score < 25:
        return "content"
    if score < 60:
        return "happy"
    return "cheerful"


def _disposition_label(score: int) -> str:
    if score <= -50:
        return "hostile"
    if score < -10:
        return "wary"
    if score < 25:
        return "neutral"
    if score < 75:
        return "friendly"
    return "devoted"


class SimulationEngine:
    def __init__(self, force_provider: str | None = None, *,
                 world_state_path: str = WORLD_STATE_PATH,
                 characters_dir: str = CHARACTERS_DIR,
                 logs_dir: str = LOGS_DIR) -> None:
        self.world_state_path = world_state_path
        self.characters_dir = characters_dir
        self.store = StateStore(world_state_path, characters_dir)
        self.llm = LLMClient(ASSIGNMENTS_PATH, force_provider=force_provider)
        self.ctx = ContextBuilder(PROMPTS_DIR, RULES_DIR)
        self.logger = get_logger(logs_dir)
        self.memory = MemoryManager(self.store, self.llm, self.ctx, self.logger)
        self.dice = Dice("aldermere")

    # =====================================================================
    #  World lifecycle
    # =====================================================================
    def world_exists(self) -> bool:
        return os.path.exists(self.world_state_path)

    def generate(self, seed=None) -> dict:
        info = engine_bridge.generate_world_files(self.store, seed=seed)
        self.logger.line(f"Generated world (engine={info['engine']}): "
                         f"{info['locations']} locations, {info['regions']} regions, "
                         f"{info['factions']} factions, {info['characters']} characters.")
        return info

    def load(self) -> None:
        self.store.load_world()
        self.store.load_characters()
        seed = self.store.world.get("meta", {}).get("seed", "aldermere")
        tick = self.store.world.get("time", {}).get("tick", 0)
        self.dice = Dice(f"{seed}:{tick}")

    @property
    def world(self) -> dict:
        return self.store.world

    # =====================================================================
    #  Time
    # =====================================================================
    def _refresh_clock(self) -> None:
        t = self.world["time"]
        total = t["total_hours"]
        hour = total % 24
        day = total // 24 + 1
        day_of_year = (total // 24) % 120
        season = SEASONS[(day_of_year // 30) % 4]
        t.update({"hour": hour, "day": day, "season": season,
                  "time_of_day": _time_of_day(hour)})

    def advance_time(self, hours: int = 1) -> None:
        t = self.world["time"]
        t["total_hours"] += hours
        t["tick"] += hours
        self._refresh_clock()

    # =====================================================================
    #  NPC scheduling & mood
    # =====================================================================
    def _active_npcs(self) -> list[dict]:
        return [self.store.get_character(cid)
                for cid in self.world.get("active_characters", [])
                if self.store.get_character(cid)]

    def move_npcs(self) -> None:
        tod = self.world["time"]["time_of_day"]
        for npc in self._active_npcs():
            if not npc.get("alive", True):
                continue
            target = npc.get("schedule", {}).get(tod) or npc.get("home_location")
            if target and target in self.world["locations"]:
                npc["current_location"] = target

    def drift_moods(self) -> None:
        for npc in self._active_npcs():
            score = npc.get("mood_score", 0)
            baseline = (npc.get("personality", {}).get("warmth", 50) - 50) // 5
            if score > baseline:
                score -= 1
            elif score < baseline:
                score += 1
            npc["mood_score"] = score
            npc["mood"] = _mood_label(score)

    # =====================================================================
    #  Director beats
    # =====================================================================
    def director_beat(self) -> str:
        system, user, ctx = self.ctx.build_director(self.world)
        resp = self.llm.complete("director", system, user, ctx)
        beat = resp.text.strip().split()[0] if resp.text.strip() else "advance_time"
        if beat not in ("advance_time", "npc_activity", "world_event", "rumor_spread"):
            beat = "advance_time"
        return beat

    def beat_world_event(self) -> str | None:
        system, user, ctx = self.ctx.build_world_event(self.world)
        resp = self.llm.complete("world_event", system, user, ctx)
        try:
            event = json.loads(resp.text)
        except (json.JSONDecodeError, ValueError):
            return None
        headline = event.get("headline", "Something stirs in the realm.")
        self.memory.record_world_event(self.world, headline)
        if event.get("rumor"):
            self.memory.add_rumor(self.world, event["rumor"])
        shift = int(event.get("mood_shift", 0))
        if shift:
            for npc in self._active_npcs():
                npc["mood_score"] = max(-100, min(100, npc.get("mood_score", 0) + shift))
                npc["mood"] = _mood_label(npc["mood_score"])
        pressure = self.world.setdefault("market", {}).setdefault("pressure", {})
        for tag, mult in (event.get("market", {}) or {}).items():
            pressure[tag] = round(max(0.6, min(2.0, pressure.get(tag, 1.0) * float(mult))), 3)
        # dragon dread builds toward the awakening
        if "dragon" in headline.lower() or "wyrm" in headline.lower():
            self.world["global_flags"]["dragon_dread"] = \
                self.world["global_flags"].get("dragon_dread", 0) + 1
        self.logger.event("world_event", headline=headline, tick=self.world["time"]["tick"])
        return headline

    def beat_npc_activity(self) -> str | None:
        groups: dict[str, list[dict]] = {}
        for npc in self._active_npcs():
            if npc.get("alive", True):
                groups.setdefault(npc["current_location"], []).append(npc)
        candidates = [g for g in groups.values() if len(g) >= 2]
        if not candidates:
            return None
        group = self.dice.choice(candidates)
        a, b = self.dice.choices(group, k=2)[:2]
        if a is b:
            return None
        loc = self.world["locations"].get(a["current_location"], {})
        scene = (f"{a['name']} and {b['name']} cross paths in "
                 f"{loc.get('name', 'town')}.")
        system, user, ctx = self.ctx.build_npc(
            a, self.world, scene, f"{b['name']} is here. Exchange a brief word.",
            topic="about")
        role = a.get("model_role", "npc")
        resp = self.llm.complete(role, system, user, ctx)
        # a small mood exchange
        shift = 1 if (a["personality"]["warmth"] + b["personality"]["warmth"]) > 100 else -1
        for c in (a, b):
            c["mood_score"] = max(-100, min(100, c.get("mood_score", 0) + shift))
            c["mood"] = _mood_label(c["mood_score"])
        self.memory.remember(a, f"chatted with {b['name']}")
        return resp.text

    def beat_rumor_spread(self) -> str | None:
        groups: dict[str, list[dict]] = {}
        for npc in self._active_npcs():
            if npc.get("alive", True):
                groups.setdefault(npc["current_location"], []).append(npc)
        for group in groups.values():
            if len(group) < 2:
                continue
            speaker = self.dice.choice(group)
            pool = list(speaker.get("knowledge", [])) + list(self.world.get("rumor_pool", []))
            if not pool:
                continue
            rumor = self.dice.choice(pool)
            spread_to = [c for c in group if c is not speaker]
            listener = self.dice.choice(spread_to)
            known = listener.setdefault("knowledge", [])
            if rumor not in known:
                known.append(rumor)
                if len(known) > 10:
                    known.pop(0)
                return f"{speaker['name']} tells {listener['name']}: \"{rumor}\""
        return None

    def resolve_skirmishes(self) -> list[str]:
        out = []
        groups: dict[str, list[dict]] = {}
        for npc in self._active_npcs():
            if npc.get("alive", True):
                groups.setdefault(npc["current_location"], []).append(npc)
        for loc_id, group in groups.items():
            loc = self.world["locations"].get(loc_id, {})
            if loc.get("is_safe", False):
                continue
            hostiles = [c for c in group if c.get("faction") == "redhand"
                        or c.get("role") in ("bandit", "monster")]
            victims = [c for c in group if c not in hostiles]
            if not hostiles or not victims:
                continue
            if not self.dice.chance(0.3):
                continue
            atk = self.dice.choice(hostiles)
            vic = self.dice.choice(victims)
            result = engine_bridge.resolve_skirmish(atk, vic, self.dice)
            winner = atk if result["winner"] == atk["id"] else vic
            loser = vic if winner is atk else atk
            verb = "drove off" if winner is vic else "waylaid"
            line = f"In {loc.get('name', loc_id)}, {winner['name']} {verb} {loser['name']}."
            out.append(line)
            loser["mood_score"] = max(-100, loser.get("mood_score", 0) - 10)
            self.memory.remember(loser, f"was {verb} by {winner['name']}")
        return out

    # =====================================================================
    #  The tick
    # =====================================================================
    def tick(self, verbose: bool = True) -> list[str]:
        self.advance_time(1)
        self.move_npcs()
        self.drift_moods()
        log: list[str] = []
        beat = self.director_beat()
        if beat == "world_event":
            headline = self.beat_world_event()
            if headline:
                log.append(f"[EVENT] {headline}")
        elif beat == "npc_activity":
            line = self.beat_npc_activity()
            if line:
                log.append(f"[SCENE] {line}")
        elif beat == "rumor_spread":
            line = self.beat_rumor_spread()
            if line:
                log.append(f"[RUMOR] {line}")
        log.extend(f"[FIGHT] {l}" for l in self.resolve_skirmishes())
        if verbose:
            for line in log:
                self.logger.line(line)
        return log

    def simulate(self, ticks: int, verbose: bool = True, save_every: int = 6) -> None:
        self.logger.section(f"Simulating {ticks} tick(s) — provider routing active")
        for i in range(ticks):
            self.tick(verbose=verbose)
            if (i + 1) % save_every == 0:
                self.store.save_all()
        self.store.save_all()
        t = self.world["time"]
        self.logger.line(f"\nReached Day {t['day']}, {t['season']} {t['time_of_day']} "
                         f"(tick {t['tick']}).")
        self.logger.line(self.llm.summary())

    # =====================================================================
    #  Interactive play
    # =====================================================================
    def _player(self) -> dict:
        return self.store.get_character(self.world.get("player", "player"))

    def describe_here(self) -> None:
        player = self._player()
        loc_id = player.get("current_location", "")
        loc = self.world["locations"].get(loc_id, {})
        present = [c["name"] for c in self.store.characters_at(loc_id)
                   if c["id"] != player["id"]]
        system, user, ctx = self.ctx.build_narrator(self.world, loc, present)
        resp = self.llm.complete("narrator", system, user, ctx)
        t = self.world["time"]
        self.logger.line(f"\n[Day {t['day']}, {t['season']} {t['time_of_day']}] "
                         f"— {loc.get('name','?')}")
        self.logger.line(resp.text)
        exits = loc.get("exits", {})
        if exits:
            pretty = ", ".join(f"{k} -> {self.world['locations'].get(v,{}).get('name',v)}"
                               for k, v in exits.items())
            self.logger.line(f"Exits: {pretty}")
        if present:
            self.logger.line("Here: " + ", ".join(present))

    def talk(self, name: str, line: str) -> None:
        player = self._player()
        npc = self._find_npc_here(name)
        if not npc:
            self.logger.line(f"There's no one called '{name}' here.")
            return
        loc = self.world["locations"].get(npc["current_location"], {})
        scene = f"You are with {npc['name']} in {loc.get('name','town')}."
        topic = self._infer_topic(line)
        system, user, ctx = self.ctx.build_npc(npc, self.world, scene, line, topic=topic)
        role = npc.get("model_role", "npc")
        resp = self.llm.complete(role, system, user, ctx)
        self.logger.line(resp.text)
        self._apply_social(npc, line, topic)
        self.memory.remember(npc, f"the adventurer said: {line[:60]}")
        self.store.save_character(npc["id"])

    def _apply_social(self, npc: dict, line: str, topic: str) -> None:
        lower = line.lower()
        delta = 0
        if any(w in lower for w in ("thank", "please", "friend", "help you")):
            delta += 2
        if topic == "compliment":
            delta += 2
        if topic == "threaten":
            ok, total = self.dice.check(2, 12 + (npc["personality"]["bravery"] - 50) // 10)
            delta += -4 if ok else -12
            self.logger.line(f"(intimidation check: {total})")
        if topic == "persuade":
            dc = 12 + max(0, -npc.get("relationship_to_player", 0) // 10)
            ok, total = self.dice.check(2, dc)
            delta += 8 if ok else -3
            self.logger.line(f"(persuasion check: {total} vs {dc} — "
                             f"{'success' if ok else 'failure'})")
        npc["relationship_to_player"] = max(-100, min(100,
                                            npc.get("relationship_to_player", 0) + delta))
        npc["disposition"] = _disposition_label(npc["relationship_to_player"])

    @staticmethod
    def _infer_topic(line: str) -> str:
        l = line.lower()
        if any(w in l for w in ("rumor", "rumour", "news", "heard")):
            return "rumors"
        if any(w in l for w in ("buy", "sell", "trade", "wares", "shop")):
            return "trade"
        if any(w in l for w in ("quest", "work", "task", "job")):
            return "quest"
        if any(w in l for w in ("threaten", "or else", "kill you")):
            return "threaten"
        if any(w in l for w in ("convince", "persuade", "reconsider")):
            return "persuade"
        if any(w in l for w in ("nice", "lovely", "well done", "wonderful", "thank")):
            return "compliment"
        if any(w in l for w in ("who are you", "about you", "yourself")):
            return "about"
        if any(w in l for w in ("where", "this place", "area")):
            return "area"
        return "greeting"

    def _find_npc_here(self, name: str) -> dict | None:
        player = self._player()
        here = self.store.characters_at(player.get("current_location", ""))
        name = name.lower()
        for c in here:
            if c["id"] == player["id"]:
                continue
            if c["name"].lower() == name or name in c["name"].lower():
                return c
        return None

    def move_player(self, direction: str) -> None:
        player = self._player()
        loc = self.world["locations"].get(player.get("current_location", ""), {})
        exits = loc.get("exits", {})
        dest = None
        d = direction.lower()
        for k, v in exits.items():
            if k.lower() == d or d in k.lower():
                dest = v
                break
            target = self.world["locations"].get(v, {})
            if d in target.get("name", "").lower():
                dest = v
                break
        if not dest:
            self.logger.line(f"You can't go '{direction}' from here.")
            return
        player["current_location"] = dest
        self.tick(verbose=True)  # the world moves while you travel
        self.describe_here()

    def play(self) -> None:
        self.logger.line("\nInteractive mode. Commands: look, go <exit>, talk <name> | "
                         "<line>, who, status, wait [n], save, quit")
        self.describe_here()
        while True:
            try:
                raw = input("\n> ").strip()
            except EOFError:
                break
            if not raw:
                continue
            cmd, _, rest = raw.partition(" ")
            cmd = cmd.lower()
            if cmd in ("quit", "exit"):
                self.store.save_all()
                self.logger.line("World saved. Farewell.")
                break
            if cmd == "look":
                self.describe_here()
            elif cmd in ("go", "move"):
                self.move_player(rest)
            elif cmd in ("talk", "say"):
                name, _, line = rest.partition("|")
                self.talk(name.strip(), line.strip() or "Hello.")
            elif cmd == "who":
                player = self._player()
                here = [c for c in self.store.characters_at(player["current_location"])
                        if c["id"] != player["id"]]
                if not here:
                    self.logger.line("No one of note is here.")
                for c in here:
                    self.logger.line(f"  {c['name']} ({c['role']}) — "
                                     f"{c.get('disposition','neutral')}, {c.get('mood','content')}")
            elif cmd == "status":
                p = self._player()
                self.logger.line(f"{p['name']} the {p['role']} — "
                                 f"at {p.get('current_location')}, "
                                 f"gold {p.get('gold', 0)}")
            elif cmd == "wait":
                n = int(rest) if rest.isdigit() else 1
                for _ in range(n):
                    self.tick(verbose=True)
                self.describe_here()
            elif cmd == "save":
                self.store.save_all()
                self.logger.line("Saved.")
            else:
                self.logger.line("Unknown command. (look/go/talk/who/status/wait/save/quit)")


# ------------------------------------------------------------------------- #
#  CLI                                                                       #
# ------------------------------------------------------------------------- #
def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="fantasy_simulator",
        description="LLM-orchestrated medieval-fantasy world simulator.")
    parser.add_argument("--simulate", type=int, default=None,
                        help="run N autonomous ticks (hours) and exit")
    parser.add_argument("--play", action="store_true", help="interactive mode")
    parser.add_argument("--reset", action="store_true",
                        help="(re)generate world_state.json and characters/")
    parser.add_argument("--seed", default=None, help="world seed (used with --reset)")
    parser.add_argument("--provider", default=None,
                        help="force a provider: mock / openai / anthropic")
    parser.add_argument("--quiet", action="store_true", help="less console output")
    args = parser.parse_args(argv)

    engine = SimulationEngine(force_provider=args.provider)

    freshly_generated = False
    if args.reset or not engine.world_exists():
        engine.generate(seed=args.seed)
        freshly_generated = True
    engine.load()

    if args.play:
        engine.play()
    elif args.simulate is not None:
        engine.simulate(args.simulate, verbose=not args.quiet)
    elif freshly_generated:
        engine.logger.line("World generated. Run with --simulate N or --play.")
    else:
        engine.simulate(24, verbose=not args.quiet)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
