"""Bridge to the Aetheria engine: generate world_state.json + characters/ from content.

This is the *exporter* that turns the rich, code-defined Aetheria content (regions,
locations, NPCs, factions, rumours) into the data-driven files this orchestrator
consumes.  It also offers a small, seeded combat resolver the referee can call.  The
bridge degrades gracefully: if the engine is unavailable a compact fallback world is
written instead, so the simulator still runs.
"""

from __future__ import annotations

from .dice import Dice

try:
    from aetheria.content import build_world  # type: ignore
    HAS_ENGINE = True
except Exception:  # pragma: no cover
    HAS_ENGINE = False


VOICE_BY_ROLE = {
    "innkeeper": "warm, talkative, fond of a good rumour",
    "blacksmith": "blunt, proud, economical with words",
    "priest": "gentle, devout, speaks in blessings",
    "guard": "stern, dutiful, clipped sentences",
    "merchant": "shrewd, smooth, always selling",
    "villager": "earnest, easily excited",
    "hunter": "quiet, watchful, sparing with words",
    "mage": "precise, aloof, fond of arcane metaphor",
    "noble": "formal, measured, faintly weary",
    "scholar": "verbose, tangential, delighted by detail",
    "monster": "feral, wordless or guttural",
}

GOALS_BY_ROLE = {
    "innkeeper": ["keep the Stag prosperous and lively", "hear every rumour first"],
    "blacksmith": ["forge the finest steel in the Vale", "secure a steady ore supply"],
    "priest": ["tend the faithful", "see the restless dead laid to rest"],
    "guard": ["keep the roads safe", "earn the Crown's favour"],
    "merchant": ["turn a tidy profit", "corner a lucrative market"],
    "villager": ["see real adventure one day"],
    "hunter": ["read the wood's moods", "keep the packs in check"],
    "mage": ["unravel the Wyrm's secret", "advance the Conclave's knowledge"],
    "noble": ["protect the realm", "manage the Crown's many burdens"],
    "scholar": ["decode the old runes", "finish just one more treatise"],
}

MAJOR_ROLES = {"noble", "mage", "priest", "guard", "blacksmith", "innkeeper"}


def _npc_to_character(npc) -> dict:
    role = npc.role
    return {
        "id": npc.id,
        "name": npc.name,
        "role": role,
        "faction": npc.faction,
        "species": npc.species,
        "alive": True,
        "home_location": npc.home_location,
        "current_location": npc.current_location,
        "personality": npc.personality.to_dict(),
        "traits": list(npc.personality.traits),
        "mood": npc.mood.value,
        "disposition": npc.disposition.value,
        "relationship_to_player": npc.relationship,
        "stats": {
            "level": npc.level,
            "strength": npc.attrs.strength, "dexterity": npc.attrs.dexterity,
            "constitution": npc.attrs.constitution, "intelligence": npc.attrs.intelligence,
            "wisdom": npc.attrs.wisdom, "charisma": npc.attrs.charisma,
            "max_health": npc.max_health,
        },
        "schedule": dict(npc.schedule),
        "voice": VOICE_BY_ROLE.get(role, "plainspoken"),
        "goals": GOALS_BY_ROLE.get(role, ["live another quiet day"]),
        "knowledge": list(npc.known_rumors),
        "is_merchant": npc.is_merchant,
        "shop": list(npc.shop_inventory),
        "quests_offered": list(npc.quests_offered),
        "model_role": "npc_major" if role in MAJOR_ROLES else "npc_minor",
        "memory": {"summary": "", "recent": []},
    }


def _default_player(start_location: str) -> dict:
    return {
        "id": "player",
        "name": "Aria",
        "role": "adventurer",
        "faction": "",
        "species": "human",
        "alive": True,
        "is_player": True,
        "home_location": start_location,
        "current_location": start_location,
        "personality": {"warmth": 55, "bravery": 60, "honesty": 60, "greed": 45,
                        "curiosity": 70, "traits": []},
        "traits": [],
        "mood": "content",
        "stats": {"level": 1, "strength": 12, "dexterity": 12, "constitution": 12,
                  "intelligence": 12, "wisdom": 12, "charisma": 12, "max_health": 40},
        "inventory": ["iron_sword", "minor_health_potion", "bread"],
        "gold": 75,
        "voice": "the player's own",
        "goals": ["make a name in Aldermere"],
        "reputation": {},
        "active_quests": [],
        "completed_quests": [],
        "memory": {"summary": "", "recent": []},
    }


def generate_world_files(store, seed=None, start_location: str = "brackenford_square") -> dict:
    """Build the engine world and write world_state.json + characters/*.json."""
    if HAS_ENGINE:
        return _generate_from_engine(store, seed, start_location)
    return _generate_fallback(store, seed, start_location)


def _generate_from_engine(store, seed, start_location) -> dict:
    world = build_world(seed)
    clock = world.clock

    locations = {}
    for lid, loc in world.map.locations.items():
        locations[lid] = {
            "id": lid, "name": loc.name, "region": loc.region_id,
            "terrain": loc.terrain.value, "description": loc.description,
            "exits": dict(loc.exits), "is_safe": loc.is_safe,
            "points_of_interest": list(loc.points_of_interest),
            "spawn_table": [list(x) for x in loc.spawn_table],
        }
    regions = {rid: {"id": rid, "name": r.name, "description": r.description,
                     "controlling_faction": r.controlling_faction,
                     "danger_level": r.danger_level, "lore": r.lore}
               for rid, r in world.map.regions.items()}
    factions = {}
    for f in world.factions.all():
        factions[f.id] = {"id": f.id, "name": f.name, "description": f.description,
                          "rivals": list(f.rivals), "allies": list(f.allies),
                          "standing": "neutral"}

    world_state = {
        "meta": {"name": "Aldermere", "seed": str(world.seed), "schema": 1,
                 "engine": "aetheria", "version": 1},
        "time": {"tick": 0, "total_hours": clock.total_hours, "hour": clock.hour,
                 "day": clock.day_index + 1, "season": clock.season.value,
                 "time_of_day": clock.time_of_day.value, "weekday": clock.weekday},
        "locations": locations,
        "regions": regions,
        "factions": factions,
        "global_flags": {"dragon_awake": False, "war_footing": False},
        "recent_events": [],
        "rumor_pool": list(world.rumor_pool),
        "market": {"pressure": {}},
        "player": "player",
        "active_characters": sorted(world.npcs.keys()),
    }
    store._world = world_state
    store.save_world()

    count = 0
    for npc in world.npcs.values():
        char = _npc_to_character(npc)
        store.upsert_character(char)
        count += 1
    player = _default_player(start_location)
    store.upsert_character(player)
    store.save_all_characters()
    return {"locations": len(locations), "regions": len(regions),
            "factions": len(factions), "characters": count + 1, "engine": True}


def _generate_fallback(store, seed, start_location) -> dict:  # pragma: no cover
    locations = {
        "brackenford_square": {
            "id": "brackenford_square", "name": "Brackenford Square", "region": "vale",
            "terrain": "town", "description": "The cobbled heart of a small town.",
            "exits": {"tavern": "gilded_stag"}, "is_safe": True,
            "points_of_interest": ["well"], "spawn_table": []},
        "gilded_stag": {
            "id": "gilded_stag", "name": "The Gilded Stag", "region": "vale",
            "terrain": "town", "description": "A warm, smoky tavern.",
            "exits": {"out": "brackenford_square"}, "is_safe": True,
            "points_of_interest": ["hearth"], "spawn_table": []},
    }
    world_state = {
        "meta": {"name": "Aldermere", "seed": str(seed), "schema": 1,
                 "engine": "fallback", "version": 1},
        "time": {"tick": 0, "total_hours": 6, "hour": 6, "day": 1,
                 "season": "Spring", "time_of_day": "Dawn", "weekday": "Sunday"},
        "locations": locations,
        "regions": {"vale": {"id": "vale", "name": "The Verdant Vale",
                             "description": "Rolling farmland.", "controlling_faction": "crown",
                             "danger_level": 1, "lore": ""}},
        "factions": {"crown": {"id": "crown", "name": "The Crown", "description": "",
                               "rivals": [], "allies": [], "standing": "neutral"}},
        "global_flags": {"dragon_awake": False},
        "recent_events": [], "rumor_pool": ["a dragon stirs in the north"],
        "market": {"pressure": {}}, "player": "player",
        "active_characters": ["bram"],
    }
    store._world = world_state
    store.save_world()
    bram = {
        "id": "bram", "name": "Bram Tunnel", "role": "innkeeper", "faction": "merchants",
        "species": "human", "alive": True, "home_location": "gilded_stag",
        "current_location": "gilded_stag",
        "personality": {"warmth": 85, "bravery": 40, "honesty": 70, "greed": 45,
                        "curiosity": 60, "traits": ["jovial"]},
        "traits": ["jovial"], "mood": "content", "disposition": "neutral",
        "relationship_to_player": 0, "stats": {"level": 1, "max_health": 30},
        "schedule": {}, "voice": VOICE_BY_ROLE["innkeeper"],
        "goals": GOALS_BY_ROLE["innkeeper"], "knowledge": ["a dragon stirs in the north"],
        "is_merchant": True, "shop": ["ale", "bread"], "quests_offered": [],
        "model_role": "npc_major", "memory": {"summary": "", "recent": []},
    }
    store.upsert_character(bram)
    store.upsert_character(_default_player(start_location))
    store.save_all_characters()
    return {"locations": len(locations), "regions": 1, "factions": 1,
            "characters": 2, "engine": False}


# --------------------------------------------------------------------------- #
#  A small, seeded combat resolver for the referee                            #
# --------------------------------------------------------------------------- #
def resolve_skirmish(attacker: dict, defender: dict, dice: Dice) -> dict:
    """Resolve a quick deterministic fight between two character dicts."""
    def power(c):
        s = c.get("stats", {})
        return (s.get("strength", 10) + s.get("dexterity", 10) + s.get("level", 1) * 3
                + s.get("max_health", 30) // 5)
    pa, pd = power(attacker), power(defender)
    roll_a = dice.roll(2, 6) + pa
    roll_d = dice.roll(2, 6) + pd
    winner, loser = (attacker, defender) if roll_a >= roll_d else (defender, attacker)
    margin = abs(roll_a - roll_d)
    return {"winner": winner["id"], "loser": loser["id"], "margin": margin,
            "decisive": margin >= 8}
