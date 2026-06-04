from __future__ import annotations

import random
from typing import Dict, Tuple

from .models import (
    Faction,
    Item,
    NPC,
    Player,
    Quest,
    QuestObjective,
    Region,
    WorldState,
)


def build_items() -> Dict[str, Item]:
    return {
        "iron_ore": Item(
            key="iron_ore",
            name="Iron Ore",
            category="resource",
            base_price=22,
            description="Unrefined ore used by blacksmiths.",
        ),
        "silver_ingot": Item(
            key="silver_ingot",
            name="Silver Ingot",
            category="resource",
            base_price=54,
            description="Smelted silver used by artisans and mages.",
        ),
        "herb_bundle": Item(
            key="herb_bundle",
            name="Herb Bundle",
            category="material",
            base_price=17,
            description="Field herbs for alchemy and medicine.",
        ),
        "wolf_pelt": Item(
            key="wolf_pelt",
            name="Wolf Pelt",
            category="trophy",
            base_price=31,
            description="Durable pelt from northern wolves.",
        ),
        "boar_tusk": Item(
            key="boar_tusk",
            name="Boar Tusk",
            category="trophy",
            base_price=25,
            description="A heavy tusk coveted by craftsmen.",
        ),
        "mana_crystal": Item(
            key="mana_crystal",
            name="Mana Crystal",
            category="arcane",
            base_price=70,
            description="Charged crystal fragment used by enchanters.",
        ),
        "ration_pack": Item(
            key="ration_pack",
            name="Ration Pack",
            category="supply",
            base_price=8,
            description="Travel food for long journeys.",
        ),
        "healing_draught": Item(
            key="healing_draught",
            name="Healing Draught",
            category="consumable",
            base_price=46,
            description="A medicinal drink that restores vitality.",
        ),
    }


def build_regions() -> Dict[str, Region]:
    return {
        "cinderfall": Region(
            key="cinderfall",
            name="Cinderfall Bastion",
            biome="Volcanic Highlands",
            danger=7,
            prosperity=6,
            resources=["iron_ore", "silver_ingot", "mana_crystal"],
            neighbors=["eldenhaven", "thornmarch"],
        ),
        "eldenhaven": Region(
            key="eldenhaven",
            name="Eldenhaven",
            biome="Fertile Riverlands",
            danger=3,
            prosperity=8,
            resources=["herb_bundle", "ration_pack"],
            neighbors=["cinderfall", "moonmere", "goldmeadow"],
        ),
        "thornmarch": Region(
            key="thornmarch",
            name="Thornmarch Frontier",
            biome="Darkwood Border",
            danger=8,
            prosperity=4,
            resources=["wolf_pelt", "boar_tusk", "herb_bundle"],
            neighbors=["cinderfall", "stormwatch", "moonmere"],
        ),
        "moonmere": Region(
            key="moonmere",
            name="Moonmere Conclave",
            biome="Arcane Wetlands",
            danger=5,
            prosperity=7,
            resources=["mana_crystal", "herb_bundle"],
            neighbors=["eldenhaven", "thornmarch", "stormwatch"],
        ),
        "stormwatch": Region(
            key="stormwatch",
            name="Stormwatch Cliffs",
            biome="Coastal Bluffs",
            danger=6,
            prosperity=5,
            resources=["silver_ingot", "ration_pack"],
            neighbors=["thornmarch", "moonmere", "goldmeadow"],
        ),
        "goldmeadow": Region(
            key="goldmeadow",
            name="Goldmeadow League",
            biome="Trade Plains",
            danger=2,
            prosperity=9,
            resources=["ration_pack", "herb_bundle", "silver_ingot"],
            neighbors=["eldenhaven", "stormwatch"],
        ),
    }


def build_factions() -> Dict[str, Faction]:
    order = Faction(
        key="ashen_order",
        name="Ashen Order",
        doctrine="Discipline and frontier defense.",
        military=82,
        wealth=52,
        influence=75,
    )
    guild = Faction(
        key="verdant_guild",
        name="Verdant Guild",
        doctrine="Commerce and civic growth.",
        military=38,
        wealth=90,
        influence=80,
    )
    circle = Faction(
        key="moonlit_circle",
        name="Moonlit Circle",
        doctrine="Arcane balance and old rites.",
        military=44,
        wealth=61,
        influence=70,
    )
    cabal = Faction(
        key="black_sail_cabal",
        name="Black Sail Cabal",
        doctrine="Smuggling, leverage, and sabotage.",
        military=56,
        wealth=74,
        influence=53,
    )
    factions = {
        order.key: order,
        guild.key: guild,
        circle.key: circle,
        cabal.key: cabal,
    }
    pairings = {
        (order.key, guild.key): 20,
        (order.key, circle.key): -8,
        (order.key, cabal.key): -72,
        (guild.key, circle.key): 24,
        (guild.key, cabal.key): -36,
        (circle.key, cabal.key): -29,
    }
    for (left, right), value in pairings.items():
        factions[left].relations[right] = value
        factions[right].relations[left] = value
    return factions


def build_npcs() -> Dict[str, NPC]:
    return {
        "captain_brann": NPC(
            key="captain_brann",
            name="Captain Brann",
            role="garrison commander",
            region_key="cinderfall",
            faction_key="ashen_order",
            personality={"honor": 9, "warmth": 4, "greed": 2, "mystic": 1},
            dialogue_tags=["military", "frontier", "discipline"],
        ),
        "seer_liora": NPC(
            key="seer_liora",
            name="Seer Liora",
            role="oracle",
            region_key="moonmere",
            faction_key="moonlit_circle",
            personality={"honor": 6, "warmth": 7, "greed": 1, "mystic": 10},
            dialogue_tags=["prophecy", "ritual", "mana"],
        ),
        "guildmaster_tovin": NPC(
            key="guildmaster_tovin",
            name="Guildmaster Tovin",
            role="merchant patriarch",
            region_key="goldmeadow",
            faction_key="verdant_guild",
            personality={"honor": 5, "warmth": 6, "greed": 9, "mystic": 2},
            dialogue_tags=["market", "coin", "contracts"],
        ),
        "warden_nyra": NPC(
            key="warden_nyra",
            name="Warden Nyra",
            role="forest ranger",
            region_key="thornmarch",
            faction_key="ashen_order",
            personality={"honor": 8, "warmth": 5, "greed": 3, "mystic": 5},
            dialogue_tags=["beasts", "tracks", "frontier"],
        ),
        "docklord_rhek": NPC(
            key="docklord_rhek",
            name="Docklord Rhek",
            role="harbor broker",
            region_key="stormwatch",
            faction_key="black_sail_cabal",
            personality={"honor": 2, "warmth": 5, "greed": 8, "mystic": 2},
            dialogue_tags=["smuggling", "ships", "blackmail"],
        ),
        "abbess_mirelle": NPC(
            key="abbess_mirelle",
            name="Abbess Mirelle",
            role="healer",
            region_key="eldenhaven",
            faction_key="moonlit_circle",
            personality={"honor": 8, "warmth": 9, "greed": 1, "mystic": 7},
            dialogue_tags=["healing", "pilgrims", "spirits"],
        ),
        "scribe_fenn": NPC(
            key="scribe_fenn",
            name="Scribe Fenn",
            role="royal archivist",
            region_key="eldenhaven",
            faction_key="verdant_guild",
            personality={"honor": 7, "warmth": 6, "greed": 4, "mystic": 6},
            dialogue_tags=["history", "records", "lore"],
        ),
        "blade_saric": NPC(
            key="blade_saric",
            name="Blade Saric",
            role="sell-sword",
            region_key="stormwatch",
            faction_key="ashen_order",
            personality={"honor": 6, "warmth": 3, "greed": 6, "mystic": 1},
            dialogue_tags=["duel", "contracts", "war"],
        ),
        "mistmother_erva": NPC(
            key="mistmother_erva",
            name="Mistmother Erva",
            role="bog witch",
            region_key="moonmere",
            faction_key="moonlit_circle",
            personality={"honor": 4, "warmth": 5, "greed": 2, "mystic": 9},
            dialogue_tags=["fog", "omens", "ritual"],
        ),
        "factor_dorr": NPC(
            key="factor_dorr",
            name="Factor Dorr",
            role="caravan steward",
            region_key="goldmeadow",
            faction_key="verdant_guild",
            personality={"honor": 5, "warmth": 5, "greed": 7, "mystic": 2},
            dialogue_tags=["trade", "routes", "supply"],
        ),
    }


def build_quests() -> Dict[str, Quest]:
    return {
        "q_frontier_pelts": Quest(
            key="q_frontier_pelts",
            title="Pelts for the Winter Wall",
            giver_npc_key="warden_nyra",
            region_key="thornmarch",
            description="Hunt wolves in Thornmarch and deliver quality pelts.",
            reward_gold=145,
            reward_reputation={"ashen_order": 6},
            objective=QuestObjective(action="hunt", target="wolf_pelt", required=4),
        ),
        "q_arcane_shards": Quest(
            key="q_arcane_shards",
            title="Moonmere Resonance",
            giver_npc_key="seer_liora",
            region_key="moonmere",
            description="Gather mana crystals for the Circle's warding lattice.",
            reward_gold=210,
            reward_reputation={"moonlit_circle": 8},
            objective=QuestObjective(action="collect", target="mana_crystal", required=3),
        ),
        "q_port_tusks": Quest(
            key="q_port_tusks",
            title="Tusks for the Shipwrights",
            giver_npc_key="docklord_rhek",
            region_key="stormwatch",
            description="Deliver boar tusks for decorative prow carvings.",
            reward_gold=118,
            reward_reputation={"black_sail_cabal": 5},
            objective=QuestObjective(action="collect", target="boar_tusk", required=5),
        ),
        "q_ironsurge": Quest(
            key="q_ironsurge",
            title="Cinderfall Forge Surge",
            giver_npc_key="captain_brann",
            region_key="cinderfall",
            description="Supply raw iron ore to reinforce defensive outposts.",
            reward_gold=170,
            reward_reputation={"ashen_order": 7},
            objective=QuestObjective(action="collect", target="iron_ore", required=6),
        ),
        "q_relief_brew": Quest(
            key="q_relief_brew",
            title="Pilgrim Relief Brew",
            giver_npc_key="abbess_mirelle",
            region_key="eldenhaven",
            description="Provide herb bundles for medicine distributed to refugees.",
            reward_gold=130,
            reward_reputation={"moonlit_circle": 6, "verdant_guild": 2},
            objective=QuestObjective(action="collect", target="herb_bundle", required=6),
        ),
    }


def build_world(player_name: str, rng: random.Random) -> Tuple[WorldState, Player, Dict[str, Item]]:
    items = build_items()
    regions = build_regions()
    factions = build_factions()
    npcs = build_npcs()
    quests = build_quests()
    world = WorldState(
        day=1,
        weather="clear",
        regions=regions,
        factions=factions,
        npcs=npcs,
        quests=quests,
    )
    starting_region = rng.choice(list(regions.keys()))
    player = Player(
        name=player_name,
        region_key=starting_region,
        gold=220,
        health=100,
        max_health=100,
        level=1,
        experience=0,
        inventory={"ration_pack": 3},
        reputation={key: 0 for key in factions},
    )
    world.log_event(
        f"Day {world.day}: {player.name} enters {regions[starting_region].name}, seeking fame and fortune."
    )
    return world, player, items
