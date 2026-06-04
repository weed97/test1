"""The bestiary — combat templates spawned for encounters and skirmishes."""

from __future__ import annotations

from ..state import World


BESTIARY: dict[str, dict] = {
    "giant_rat": {
        "name": "Giant Rat", "species": "beast", "role": "monster",
        "level": 1, "strength": 8, "dexterity": 11, "constitution": 7,
        "abilities": ["bite"], "xp_reward": 8, "gold": 0,
        "loot_table": [("rat_tail", 0.9)],
    },
    "wolf": {
        "name": "Grey Wolf", "species": "beast", "role": "monster", "faction": "redhand",
        "level": 1, "strength": 11, "dexterity": 13, "constitution": 10,
        "abilities": ["bite", "rend"], "xp_reward": 14, "gold": 0,
        "loot_table": [("wolf_pelt", 0.7), ("venison", 0.3)],
    },
    "frost_wolf": {
        "name": "Frost Wolf", "species": "beast", "role": "monster",
        "level": 4, "strength": 14, "dexterity": 14, "constitution": 13,
        "abilities": ["bite", "rend"], "xp_reward": 36, "gold": 0,
        "loot_table": [("wolf_pelt", 0.9), ("venison", 0.4)],
    },
    "giant_spider": {
        "name": "Giant Spider", "species": "beast", "role": "monster",
        "level": 2, "strength": 12, "dexterity": 15, "constitution": 11,
        "abilities": ["venom_bite"], "xp_reward": 22, "gold": 0,
        "loot_table": [("spider_silk", 0.8)],
    },
    "bandit": {
        "name": "Redhand Bandit", "species": "human", "role": "bandit", "faction": "redhand",
        "level": 2, "strength": 13, "dexterity": 12, "constitution": 11,
        "abilities": ["power_strike"], "xp_reward": 25, "gold": 18,
        "equipment": ["rusty_sword", "leather_armor"],
        "loot_table": [("bandit_insignia", 0.6), ("minor_health_potion", 0.3),
                       ("ancient_coin", 0.2), ("lost_locket", 0.12)],
    },
    "bandit_chief": {
        "name": "Redhand Chief", "species": "human", "role": "bandit", "faction": "redhand",
        "level": 5, "strength": 16, "dexterity": 13, "constitution": 14,
        "abilities": ["power_strike", "cleave", "second_wind"], "xp_reward": 90, "gold": 80,
        "equipment": ["iron_sword", "chain_mail", "wooden_shield"],
        "loot_table": [("bandit_insignia", 1.0), ("silver_goblet", 0.5),
                       ("health_potion", 0.4), ("steel_longsword", 0.15)],
    },
    "skeleton": {
        "name": "Skeleton Warrior", "species": "undead", "role": "monster",
        "level": 3, "strength": 13, "dexterity": 10, "constitution": 12,
        "abilities": ["power_strike"], "xp_reward": 30, "gold": 5,
        "equipment": ["rusty_sword"],
        "loot_table": [("ancient_coin", 0.5), ("iron_ingot", 0.2)],
    },
    "wraith": {
        "name": "Fen Wraith", "species": "undead", "role": "monster",
        "level": 5, "strength": 10, "dexterity": 16, "constitution": 12,
        "intelligence": 14, "abilities": ["frost_lance", "poison_dart"],
        "xp_reward": 80, "gold": 30,
        "loot_table": [("mana_crystal", 0.4), ("ancient_coin", 0.6)],
    },
    "kobold": {
        "name": "Cave Kobold", "species": "beast", "role": "monster",
        "level": 1, "strength": 9, "dexterity": 13, "constitution": 9,
        "abilities": ["backstab"], "xp_reward": 12, "gold": 6,
        "equipment": ["dagger"],
        "loot_table": [("iron_ore", 0.5), ("coal", 0.4)],
    },
    "stone_golem": {
        "name": "Stone Golem", "species": "construct", "role": "monster",
        "level": 6, "strength": 18, "dexterity": 6, "constitution": 18,
        "abilities": ["power_strike"], "xp_reward": 120, "gold": 0,
        "loot_table": [("iron_ore", 1.0), ("ruby", 0.3), ("mana_crystal", 0.3)],
    },
    "bog_lurker": {
        "name": "Bog Lurker", "species": "plant", "role": "monster",
        "level": 3, "strength": 14, "dexterity": 8, "constitution": 14,
        "abilities": ["venom_bite", "rend"], "xp_reward": 40, "gold": 0,
        "loot_table": [("redroot", 0.6), ("moonpetal", 0.4)],
    },
    "dragon": {
        "name": "Skorvaxis, the Frostpeak Wyrm", "species": "demon", "role": "monster",
        "level": 10, "strength": 22, "dexterity": 14, "constitution": 22,
        "intelligence": 16, "wisdom": 14,
        "abilities": ["fire_breath", "rend", "power_strike"], "xp_reward": 500, "gold": 1200,
        "loot_table": [("dragon_scale", 1.0), ("ruby", 1.0), ("gold_idol", 0.8),
                       ("dragonfang", 1.0)],
    },
}


def register_bestiary(world: World) -> None:
    world.bestiary = {k: dict(v) for k, v in BESTIARY.items()}
