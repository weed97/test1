# Aetheria — A Living Medieval-Fantasy MMORPG Simulator

Aetheria is a **text-based, NPC-conversational fantasy MMORPG simulator** written in
pure Python (standard library only). It models a *living* medieval-fantasy realm —
**Aldermere** — where dozens of NPCs with their own personalities, moods, memories,
daily routines and relationships go about their lives while you explore five regions,
talk your way through conversations, fight monsters, cast spells, trade on a dynamic
market, craft gear, complete quests and earn faction reputation.

The world keeps turning whether or not you are watching: merchants restock, prices
drift, rumours spread from tavern to tavern, world events ripple through the economy,
and the realm builds toward the awakening of **Skorvaxis, the Frostpeak Wyrm**.

```
   _    _____ _____ _   _ _____ ____  ___    _
  / \  | ____|_   _| | | | ____|  _ \|_ _|  / \
 / _ \ |  _|   | | | |_| |  _| | |_) || |  / _ \
/ ___ \| |___  | | |  _  | |___|  _ < | | / ___ \
\_/   \_\_____| |_| |_| |_|_____|_| \_\___/_/   \_\
```

## Quick start

Requires **Python 3.10+** (developed on 3.12). No third-party runtime dependencies.

```bash
# Play interactively (character creation, then explore)
python -m aetheria

# Skip creation
python -m aetheria --name Aria --class mage --seed myworld

# Watch the world simulate itself for N days (head-less)
python -m aetheria --simulate 10 --seed aldermere

# Run a short scripted, no-input demo of every system
python -m aetheria --demo

# Load a save
python -m aetheria --load save1
```

## What makes it a *simulator*

### Conversational, reactive NPCs (the core feature)
Conversations are **generated from each NPC's living state**, not from a fixed script.
An NPC's reply is shaped by:

* their **disposition** toward you (hostile → wary → neutral → friendly → devoted),
* their current **mood** (angry, content, cheerful, drunk, tired …),
* a five-axis **personality** (warmth, bravery, honesty, greed, curiosity),
* their **memories** of past interactions with you,
* the **time of day** and the **place** they are standing in,
* your **reputation** with their faction.

You can ask about themselves, fish for rumours, ask about the area, take on work,
trade, compliment, **persuade** (a charisma check), **intimidate** (a strength/charisma
check), give **gifts** (greed-weighted relationship gains) — or draw steel.

### A living world that runs without you
Every in-world hour the [`Simulation`](aetheria/simulation.py):

* advances the clock and moves NPCs along their **daily schedules**,
* drifts moods back toward each NPC's temperament and regenerates resources,
* breathes the **market** (a mean-reverting random walk per item),
* may fire a **world event** (war scares, good harvests, dragon sightings, festivals …)
  that shocks prices and shifts moods,
* lets co-located NPCs **gossip**, spreading rumours through the population,
* resolves **skirmishes** between hostile and peaceful NPCs in dangerous places.

### Deep RPG systems
* **6 classes** (warrior, mage, rogue, ranger, cleric, paladin), six attributes and
  derived combat stats, XP and levelling.
* **Turn-based combat** with basic attacks, **22 abilities/spells**, status effects
  (poison, burning, bleed, stun, regen, blessed, shielded …), criticals, and an
  **elemental resistance** table (undead, beasts, constructs, demons …).
* **50+ items** across weapons, armour, shields, trinkets, consumables, food,
  materials, treasures and quest items, with rarities from common to legendary.
* **Inventory & equipment** with weight, slots, and stacking.
* **A dynamic economy**: merchant buy/sell spreads modulated by reputation and
  charisma, with prices that move over time and react to events.
* **Crafting** across smithing, alchemy, tailoring and cooking, gated by stations
  (forge, alchemy table, loom, cookfire) and growing profession skill.
* **Quests** with typed objectives (kill / collect / talk / reach / deliver),
  prerequisites, rewards (gold, items, XP, abilities, titles, reputation) and a
  journal — from *Cellar Pests* to the climactic *Frostpeak Wyrm*.
* **7 factions** with allies/rivals and reputation that ripples between them.
* **Save / load** of the entire dynamic world state to JSON.
* **Deterministic seeding** — the same world seed reproduces the same world.

### The realm of Aldermere
Five hand-authored regions and **27 locations**:

* **The Verdant Vale** — the town of Brackenford (tavern, smithy, market, temple, inn, cellar).
* **Thornwood** — a bandit-haunted forest with a forgotten shrine and a Redhand camp.
* **The Frostpeak Range** — mines, ice passes and a sleeping dragon's roost.
* **Mirewater Fen** — a hedge-witch, drowned ruins and restless dead.
* **Highcrown** — the capital: grand bazaar, cathedral, the Arcane Conclave and the Keep.

…populated by **14 named NPCs** (and a bestiary of monsters) including Bram the
jovial innkeeper, Mira the blunt blacksmith, Captain Doran of the Crown, Morwenna
the cryptic hedge-witch, Archmagus Velian, and the avaricious Master Coyne.

## In-game commands

```
Exploration : look · go <exit> · map · explore/search · gather/mine · rest [hours]
People      : talk <name> · who
Character   : status · inventory · equip/unequip · use · abilities
Quests/World: journal · rumors · news · recipes · craft <recipe> · time
System      : save [slot] · load [slot] · help · quit
Battle      : attack [foe] · cast <ability> [foe] · item <name> · defend · flee
```

## Architecture

```
aetheria/
  rng.py          deterministic, seedable randomness
  gametime.py     clock, calendar, seasons, day/night
  stats.py        attributes & derived combat statistics
  effects.py      status effects (buffs / debuffs / DoTs)
  items.py        items, equipment, inventories
  skills.py       classes, skills & spells
  combat.py       turn-based combat resolution + AI
  character.py    Actor / Player / NPC (personality, mood, memory, schedule)
  dialogue.py     the generative conversational engine
  world.py        regions, locations and the world graph
  economy.py      merchants and a fluctuating market
  quest.py        quests, objectives and the journal
  faction.py      factions and reputation
  crafting.py     recipes and professions
  events.py       world events
  simulation.py   the autonomous world-simulation loop
  state.py        the World container wiring everything together
  persistence.py  save / load
  content/        authored content (items, abilities, classes, recipes,
                  factions, world map, monsters, NPCs, quests, rumours)
  game/           the playable CLI client (factory + cli)
  demo.py         a scripted, no-input showcase playthrough
tests/            pytest suite (engine + content)
```

## Development

```bash
pip install pytest
python -m pytest -q          # run the test suite (31 tests)
python -m aetheria --demo    # end-to-end smoke test
```

## License

Released under the MIT License — see [LICENSE](LICENSE).
