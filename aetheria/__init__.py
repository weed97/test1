"""Aetheria — a sophisticated text-based medieval-fantasy NPC-conversational MMORPG simulator.

Aetheria simulates a *living* medieval fantasy world: dozens of NPCs with their own
personalities, moods, memories, daily routines and relationships go about their lives
while the player explores regions, talks to characters, fights monsters, casts spells,
trades on a dynamic market, crafts gear, completes quests and earns faction reputation.

The package is organised as a small game engine plus authored content:

    aetheria.rng          deterministic, seedable randomness
    aetheria.gametime     in-world clock, calendar, seasons, day/night
    aetheria.stats        attributes & derived combat statistics
    aetheria.items        items, equipment, inventories
    aetheria.skills       classes, skills and spells
    aetheria.combat       turn-based combat resolution
    aetheria.character    Player and NPC actors
    aetheria.dialogue     the conversational NPC engine
    aetheria.world        regions, locations and the world graph
    aetheria.economy      merchants and a fluctuating market
    aetheria.quest        quests, objectives and journals
    aetheria.faction      factions and reputation
    aetheria.crafting     recipes and professions
    aetheria.events       world events that ripple through the simulation
    aetheria.simulation   the autonomous world-simulation loop
    aetheria.persistence  save / load of the full world state
    aetheria.content.*    authored game content (world, npcs, items, quests, spells)
    aetheria.game.*       the playable command-line client
"""

__version__ = "1.0.0"
__all__ = ["__version__"]
