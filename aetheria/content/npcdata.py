"""The named, living population of Aldermere: townsfolk, merchants and powers."""

from __future__ import annotations

from ..character import NPC, Personality
from ..state import World


def _npc(world: World, npc_id: str, name: str, *, role: str, faction: str = "",
         home: str, level: int = 1, species: str = "human",
         personality: Personality, greeting: str = "",
         schedule: dict[str, str] | None = None, merchant: bool = False,
         shop: list[str] | None = None, quests: list[str] | None = None,
         rumors: list[str] | None = None, gold: int = 30,
         titles: tuple[str, ...] = (),
         strength: int = 10, dexterity: int = 10, constitution: int = 10,
         intelligence: int = 10, wisdom: int = 10, charisma: int = 10) -> NPC:
    npc = NPC(npc_id, name, world.items, role=role, faction=faction,
              home_location=home, level=level)
    npc.species = species
    npc.attrs.strength = strength
    npc.attrs.dexterity = dexterity
    npc.attrs.constitution = constitution
    npc.attrs.intelligence = intelligence
    npc.attrs.wisdom = wisdom
    npc.attrs.charisma = charisma
    npc.personality = personality
    npc.greeting = greeting
    npc.current_location = home
    npc.schedule = schedule or {}
    npc.is_merchant = merchant
    npc.shop_inventory = shop or []
    npc.quests_offered = quests or []
    npc.known_rumors = rumors or []
    npc.gold = gold
    npc.titles = titles
    npc.full_restore()
    world.add_npc(npc)
    return npc


def register_npcs(world: World) -> None:
    # ===================== The Verdant Vale ============================== #
    _npc(world, "bram", "Bram Tunnel", role="innkeeper", faction="merchants",
         home="gilded_stag", charisma=14, constitution=13,
         personality=Personality(warmth=85, bravery=40, honesty=70, greed=45,
                                  curiosity=60, traits=("jovial", "gossip")),
         greeting="Welcome to the Gilded Stag! Pull up a stool, friend.",
         schedule={"Dawn": "gilded_stag", "Morning": "gilded_stag",
                   "Noon": "gilded_stag", "Afternoon": "gilded_stag",
                   "Dusk": "gilded_stag", "Night": "gilded_stag",
                   "Midnight": "the_rest"},
         merchant=True, shop=["ale", "bread", "cheese", "venison",
                              "minor_health_potion", "stamina_draught"],
         quests=["q_rats"], gold=120,
         rumors=["the cellar's overrun with rats the size of cats",
                 "Captain Doran's been losing sleep over the road bandits"])

    _npc(world, "mira", "Mira Emberhand", role="blacksmith", faction="merchants",
         home="smithy", strength=15, constitution=14, level=4,
         personality=Personality(warmth=55, bravery=70, honesty=80, greed=50,
                                  curiosity=40, traits=("blunt", "proud")),
         greeting="Mind the sparks. What do you need?",
         schedule={"Dawn": "smithy", "Morning": "smithy", "Noon": "gilded_stag",
                   "Afternoon": "smithy", "Dusk": "smithy", "Night": "the_rest",
                   "Midnight": "the_rest"},
         merchant=True, shop=["rusty_sword", "iron_sword", "steel_longsword",
                              "war_axe", "wooden_shield", "iron_shield",
                              "leather_armor", "chain_mail", "iron_helm",
                              "iron_ingot"],
         quests=["q_ore"], gold=200,
         rumors=["good steel needs good ore, and the mine's gone quiet",
                 "they're paying well in Highcrown for dragon scale"])

    _npc(world, "elin", "Sister Elin", role="priest", faction="dawn",
         home="temple", wisdom=15, charisma=13, level=3,
         personality=Personality(warmth=80, bravery=55, honesty=90, greed=20,
                                  curiosity=50, traits=("kind", "devout")),
         greeting="Light keep you, traveller. How may I ease your burden?",
         schedule={"Dawn": "temple", "Morning": "temple", "Noon": "temple",
                   "Afternoon": "market", "Dusk": "temple", "Night": "the_rest",
                   "Midnight": "the_rest"},
         merchant=True, shop=["minor_health_potion", "health_potion", "antidote",
                              "mana_potion"],
         quests=["q_herbs"], gold=90,
         rumors=["the old shrine in the Thornwood has been... restless",
                 "moonpetal only blooms by night, out past the treeline"])

    _npc(world, "doran", "Captain Doran", role="guard", faction="crown",
         home="north_gate", strength=15, constitution=15, level=5,
         personality=Personality(warmth=45, bravery=85, honesty=85, greed=30,
                                  curiosity=35, traits=("dutiful", "stern")),
         greeting="State your business, citizen. The road's not safe these days.",
         schedule={"Dawn": "north_gate", "Morning": "north_gate", "Noon": "north_gate",
                   "Afternoon": "kings_road", "Dusk": "north_gate",
                   "Night": "gilded_stag", "Midnight": "the_rest"},
         quests=["q_bandits"], gold=60,
         rumors=["the Redhand have a camp deep in the Thornwood",
                 "lose enough good men and a captain stops sleeping"])

    _npc(world, "tilda", "Goodwife Tilda", role="merchant", faction="merchants",
         home="market", charisma=13,
         personality=Personality(warmth=65, bravery=30, honesty=55, greed=70,
                                  curiosity=55, traits=("shrewd", "chatty")),
         greeting="Finest goods in the Vale, dearie — for a fair price, mind.",
         schedule={"Dawn": "the_rest", "Morning": "market", "Noon": "market",
                   "Afternoon": "market", "Dusk": "market", "Night": "gilded_stag",
                   "Midnight": "the_rest"},
         merchant=True, shop=["bread", "cheese", "linen", "oak_wood", "coal",
                              "redroot", "leather_scrap", "leather_boots",
                              "minor_health_potion", "silver_goblet"],
         gold=150,
         rumors=["prices on weapons climb every time war's mentioned",
                 "a hooded woman in the market asks odd questions"])

    _npc(world, "pip", "Pip", role="villager", faction="",
         home="brackenford_square", level=1, charisma=10,
         personality=Personality(warmth=75, bravery=25, honesty=60, greed=40,
                                  curiosity=95, traits=("curious", "underfoot")),
         greeting="Are you a real adventurer? Have you got a sword? Can I see?!",
         schedule={"Dawn": "the_rest", "Morning": "brackenford_square",
                   "Noon": "market", "Afternoon": "brackenford_square",
                   "Dusk": "gilded_stag", "Night": "the_rest", "Midnight": "the_rest"},
         gold=2,
         rumors=["I saw lights in the marsh at night, all green and floaty",
                 "the witch in the fen turns folk into toads, my cousin says"])

    _npc(world, "wat", "Wat the Hunter", role="hunter", faction="",
         home="thornwood_edge", dexterity=15, wisdom=13, level=3,
         personality=Personality(warmth=50, bravery=65, honesty=75, greed=40,
                                  curiosity=45, traits=("watchful", "laconic")),
         greeting="Quiet, now. The wood's listening. ...What is it?",
         schedule={"Dawn": "thornwood_edge", "Morning": "deep_thornwood",
                   "Noon": "thornwood_edge", "Afternoon": "kings_road",
                   "Dusk": "gilded_stag", "Night": "gilded_stag", "Midnight": "the_rest"},
         merchant=True, shop=["hunting_bow", "venison", "wolf_pelt", "leather_armor"],
         gold=70,
         rumors=["wolves are running in bigger packs than they ought",
                 "saw spider-silk strung thick near the old shrine"])

    # ===================== Mirewater Fen ================================= #
    _npc(world, "morwenna", "Morwenna the Hedge-Witch", role="mage", faction="fenfolk",
         home="witch_hut", intelligence=16, wisdom=15, level=6, species="human",
         personality=Personality(warmth=35, bravery=60, honesty=50, greed=55,
                                  curiosity=90, traits=("cryptic", "clever")),
         greeting="Mm. The fen told me someone was coming. It's seldom wrong.",
         schedule={"Dawn": "witch_hut", "Morning": "witch_hut", "Noon": "fen_road",
                   "Afternoon": "witch_hut", "Dusk": "witch_hut", "Night": "witch_hut",
                   "Midnight": "witch_hut"},
         merchant=True, shop=["mana_potion", "health_potion", "antidote",
                              "elixir_might", "moonpetal", "mana_crystal", "oak_staff"],
         quests=["q_relic"], gold=140,
         rumors=["the sunken ruins drowned for a reason — leave their relic be",
                 "the dead in the fen do not always stay where they're put"])

    # ===================== Highcrown ===================================== #
    _npc(world, "velian", "Archmagus Velian", role="mage", faction="conclave",
         home="conclave_tower", intelligence=18, wisdom=16, level=9,
         personality=Personality(warmth=40, bravery=70, honesty=70, greed=30,
                                  curiosity=95, traits=("brilliant", "aloof")),
         greeting="Ah. A new variable enters the equation. Speak, then.",
         schedule={"Dawn": "conclave_tower", "Morning": "conclave_tower",
                   "Noon": "conclave_tower", "Afternoon": "castle_keep",
                   "Dusk": "conclave_tower", "Night": "conclave_tower",
                   "Midnight": "conclave_tower"},
         merchant=True, shop=["mana_potion", "mana_crystal", "amulet_focus",
                              "ancient_tome", "oak_staff"],
         quests=["q_tome"], gold=400, titles=("Archmagus",),
         rumors=["the Wyrm of Frostpeak is no legend; the Conclave has proof",
                 "an artefact sleeps in the fen that could wake far worse things"])

    _npc(world, "aldous", "High Priest Aldous", role="priest", faction="dawn",
         home="cathedral", wisdom=17, charisma=15, level=8,
         personality=Personality(warmth=70, bravery=75, honesty=95, greed=15,
                                  curiosity=50, traits=("serene", "righteous")),
         greeting="The Dawn's blessing upon you, child. What brings you to the light?",
         schedule={"Dawn": "cathedral", "Morning": "cathedral", "Noon": "cathedral",
                   "Afternoon": "cathedral", "Dusk": "cathedral", "Night": "cathedral",
                   "Midnight": "cathedral"},
         merchant=True, shop=["health_potion", "antidote", "mace_of_dawn"],
         gold=300, titles=("High Priest",),
         rumors=["undeath festers in the fen; the Order would see it cleansed",
                 "a blessed blade can lay the restless dead to rest for good"])

    _npc(world, "coyne", "Master Coyne", role="merchant", faction="merchants",
         home="grand_market", charisma=16,
         personality=Personality(warmth=55, bravery=35, honesty=40, greed=85,
                                  curiosity=60, traits=("smooth", "avaricious")),
         greeting="Welcome, welcome! Whatever you seek, Coyne can procure it.",
         schedule={"Dawn": "grand_market", "Morning": "grand_market",
                   "Noon": "grand_market", "Afternoon": "grand_market",
                   "Dusk": "grand_market", "Night": "castle_keep",
                   "Midnight": "grand_market"},
         merchant=True, shop=["steel_longsword", "war_axe", "plate_armor",
                              "iron_shield", "ring_vigor", "amulet_focus",
                              "health_potion", "mana_potion", "elixir_might",
                              "gold_idol", "ruby"],
         gold=1000,
         rumors=["everything has a price; even kings, given enough of it",
                 "dragon scale fetches a small fortune, if one could get it"])

    _npc(world, "halric", "Steward Halric", role="noble", faction="crown",
         home="castle_keep", charisma=15, wisdom=14, level=6,
         personality=Personality(warmth=45, bravery=60, honesty=75, greed=35,
                                  curiosity=55, traits=("formal", "burdened")),
         greeting="You stand in the Keep of Aldermere. Make your petition briefly.",
         schedule={"Dawn": "castle_keep", "Morning": "castle_keep",
                   "Noon": "castle_keep", "Afternoon": "castle_keep",
                   "Dusk": "castle_keep", "Night": "castle_keep",
                   "Midnight": "castle_keep"},
         quests=["q_dragon"], gold=500, titles=("Royal Steward",),
         rumors=["the Crown will richly reward whoever ends the Wyrm's threat",
                 "the eastern lords watch our troubles with hungry eyes"])

    _npc(world, "lysa", "Lysa Quill", role="merchant", faction="shadowhand",
         home="grand_market", dexterity=15, charisma=15, level=4,
         personality=Personality(warmth=50, bravery=55, honesty=30, greed=65,
                                  curiosity=70, traits=("sly", "charming")),
         greeting="Don't look so alarmed. I only deal in... information. And favours.",
         schedule={"Dawn": "the_rest", "Morning": "grand_market",
                   "Noon": "gilded_stag", "Afternoon": "grand_market",
                   "Dusk": "grand_market", "Night": "gilded_stag",
                   "Midnight": "grand_market"},
         merchant=True, shop=["dagger", "leather_armor", "minor_health_potion",
                              "antidote", "ancient_coin"],
         quests=["q_locket"], gold=180,
         rumors=["the Shadow Hand pays better than the Crown, and asks fewer questions",
                 "a certain locket went missing on the Thornwood road"])

    _npc(world, "bartholomew", "Bartholomew the Scribe", role="scholar", faction="conclave",
         home="conclave_tower", intelligence=15, wisdom=14,
         personality=Personality(warmth=60, bravery=20, honesty=85, greed=25,
                                  curiosity=98, traits=("bookish", "tangent-prone")),
         greeting="Oh! A visitor. Do mind the levitating folios. Now, what was I— yes?",
         schedule={"Dawn": "conclave_tower", "Morning": "conclave_tower",
                   "Noon": "grand_market", "Afternoon": "conclave_tower",
                   "Dusk": "conclave_tower", "Night": "the_rest", "Midnight": "the_rest"},
         gold=40,
         rumors=["the runes in the sunken ruins predate the Kingdom itself",
                 "Skorvaxis the Wyrm has slept three hundred years — and may be waking"])
