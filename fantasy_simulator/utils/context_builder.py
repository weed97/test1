"""Assemble token-efficient prompts from rules, world state, character & memory.

The builder is the bridge between the *documents* (rules, prompts) and the *live data*
(world_state, characters).  For each role it injects only the relevant slices — a major
optimisation for a large world where dumping everything would blow the context window.
"""

from __future__ import annotations

import json
import os


def _read(path: str) -> str:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return fh.read().strip()
    except FileNotFoundError:
        return ""


class ContextBuilder:
    def __init__(self, prompts_dir: str, rules_dir: str) -> None:
        self.prompts_dir = prompts_dir
        self.rules_dir = rules_dir
        self._prompt_cache: dict[str, str] = {}
        self._rule_cache: dict[str, str] = {}

    # -- loading -------------------------------------------------------------
    def prompt(self, role: str) -> str:
        if role not in self._prompt_cache:
            self._prompt_cache[role] = _read(os.path.join(self.prompts_dir, f"{role}.md"))
        return self._prompt_cache[role]

    def rule(self, name: str, max_chars: int = 1800) -> str:
        if name not in self._rule_cache:
            self._rule_cache[name] = _read(os.path.join(self.rules_dir, f"{name}.md"))
        text = self._rule_cache[name]
        return text[:max_chars]

    def rules_block(self, names: list[str]) -> str:
        parts = [self.rule(n) for n in names]
        return "\n\n".join(p for p in parts if p)

    # -- compact views of live state ----------------------------------------
    @staticmethod
    def world_snapshot(world: dict) -> str:
        t = world.get("time", {})
        facs = world.get("factions", {})
        flags = world.get("global_flags", {})
        tensions = ", ".join(f"{k}:{v.get('standing','?')}" for k, v in facs.items())
        recent = world.get("recent_events", [])[-4:]
        lines = [
            f"World: {world.get('meta', {}).get('name', 'Aldermere')} | "
            f"Day {t.get('day', 1)}, {t.get('season', 'Spring')}, "
            f"{t.get('time_of_day', 'Day')} (tick {t.get('tick', 0)})",
            f"Factions: {tensions}" if tensions else "",
            f"Flags: {json.dumps(flags)}" if flags else "",
        ]
        if recent:
            lines.append("Recent events: " + " | ".join(recent))
        return "\n".join(l for l in lines if l)

    @staticmethod
    def character_sheet(char: dict) -> str:
        p = char.get("personality", {})
        mem = char.get("memory", {})
        sheet = [
            f"Name: {char.get('name')} ({char.get('role')}, {char.get('faction','—')})",
            f"Species: {char.get('species','human')} | Home: {char.get('home_location','')}",
            f"Mood: {char.get('mood','content')} | "
            f"Disposition to player: {char.get('disposition','neutral')} "
            f"(score {char.get('relationship_to_player', 0)})",
            f"Personality: warmth {p.get('warmth',50)}, bravery {p.get('bravery',50)}, "
            f"honesty {p.get('honesty',50)}, greed {p.get('greed',50)}, "
            f"curiosity {p.get('curiosity',50)}",
        ]
        if char.get("traits"):
            sheet.append("Traits: " + ", ".join(char["traits"]))
        if char.get("voice"):
            sheet.append("Voice: " + char["voice"])
        if char.get("goals"):
            sheet.append("Goals: " + "; ".join(char["goals"]))
        if mem.get("summary"):
            sheet.append("Memory summary: " + mem["summary"])
        recent = mem.get("recent", [])[-4:]
        if recent:
            sheet.append("Recent memories: " + " | ".join(recent))
        if char.get("knowledge"):
            sheet.append("Knows: " + "; ".join(char["knowledge"][:4]))
        return "\n".join(sheet)

    # -- builders per role ---------------------------------------------------
    def build_npc(self, char: dict, world: dict, scene: str, player_line: str,
                  topic: str = "greeting") -> tuple[str, str, dict]:
        system = "\n\n".join([
            self.prompt("npc_roleplay"),
            "## World rules you must respect\n" + self.rules_block(["social_system"]),
            "## World state\n" + self.world_snapshot(world),
            "## Your character sheet\n" + self.character_sheet(char),
        ])
        user = (f"## Scene\n{scene}\n\n"
                f"## The adventurer says/does\n{player_line}\n\n"
                f"Respond in character with a single short spoken line (and minimal action "
                f"beats). Stay consistent with your mood, disposition and memory.")
        ctx = {
            "role": "npc", "name": char.get("name"), "mood": char.get("mood", "content"),
            "disposition": char.get("disposition", "neutral"), "topic": topic,
            "voice": char.get("voice", ""), "traits": char.get("traits", []),
            "location": self._location_name(world, char.get("current_location", "")),
            "self_line": (char.get("goals") or ["I get by, same as anyone."])[0],
            "seed_key": f"{char.get('id')}:{world.get('time',{}).get('tick',0)}:{topic}",
        }
        return system, user, ctx

    def build_narrator(self, world: dict, location: dict, present: list[str]) -> tuple[str, str, dict]:
        system = "\n\n".join([
            self.prompt("narrator"),
            "## World state\n" + self.world_snapshot(world),
            "## World lore\n" + self.rule("world_lore", max_chars=1200),
        ])
        user = (f"## Location\n{location.get('name','?')}: {location.get('description','')}\n"
                f"Present: {', '.join(present) if present else 'no one of note'}\n\n"
                f"Describe the scene in 2-3 evocative sentences.")
        t = world.get("time", {})
        ctx = {
            "role": "narrator", "location": location.get("name", "the road"),
            "time_of_day": t.get("time_of_day", "Day"), "season": t.get("season", "Spring"),
            "present": present, "seed_key": f"narr:{location.get('id')}:{t.get('tick',0)}",
        }
        return system, user, ctx

    def build_world_event(self, world: dict) -> tuple[str, str, dict]:
        system = "\n\n".join([
            self.prompt("world_event"),
            "## Simulation rules\n" + self.rule("simulation_loop", max_chars=1200),
            "## World state\n" + self.world_snapshot(world),
        ])
        user = ("Generate ONE plausible world event as strict JSON with keys: "
                '"headline" (string), "rumor" (string), "mood_shift" (int -8..8), '
                '"market" (object of tag->multiplier). No prose outside the JSON.')
        ctx = {"role": "world_event",
               "seed_key": f"event:{world.get('time',{}).get('tick',0)}"}
        return system, user, ctx

    def build_referee(self, action: str, success: bool, detail: str = "") -> tuple[str, str, dict]:
        system = "\n\n".join([
            self.prompt("referee"),
            "## Combat & magic rules\n" + self.rules_block(["combat_rules", "magic_system"]),
        ])
        user = (f"Action attempted: {action}\nMechanical result: "
                f"{'SUCCESS' if success else 'FAILURE'}. {detail}\n"
                f"Narrate the outcome in one or two sentences, consistent with the result.")
        ctx = {"role": "referee", "action": action, "success": success,
               "seed_key": f"ref:{action[:24]}"}
        return system, user, ctx

    def build_memory_summary(self, char: dict) -> tuple[str, str, dict]:
        system = self.prompt("memory_summarizer")
        recent = char.get("memory", {}).get("recent", [])
        prior = char.get("memory", {}).get("summary", "")
        user = (f"Prior summary: {prior or '(none)'}\n"
                f"New events:\n- " + "\n- ".join(recent) +
                "\nProduce a concise (<=3 sentence) updated summary capturing what matters "
                "for this character going forward.")
        ctx = {"role": "memory_summarizer", "events": recent,
               "seed_key": f"mem:{char.get('id')}"}
        return system, user, ctx

    def build_director(self, world: dict) -> tuple[str, str, dict]:
        system = "\n\n".join([
            self.prompt("director"),
            "## Simulation rules\n" + self.rule("simulation_loop", max_chars=1000),
            "## World state\n" + self.world_snapshot(world),
        ])
        user = ("Choose the next simulation beat. Reply with exactly one of: "
                "advance_time, npc_activity, world_event, rumor_spread.")
        ctx = {"role": "director", "seed_key": f"dir:{world.get('time',{}).get('tick',0)}"}
        return system, user, ctx

    # -- helpers -------------------------------------------------------------
    @staticmethod
    def _location_name(world: dict, loc_id: str) -> str:
        return world.get("locations", {}).get(loc_id, {}).get("name", loc_id or "somewhere")
