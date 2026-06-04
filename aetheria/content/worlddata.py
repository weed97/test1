"""The geography of Aldermere: five regions and the places within them."""

from __future__ import annotations

from ..state import World
from ..world import Location, Region, Terrain


def register_world(world: World) -> None:
    wm = world.map

    # ---- regions -----------------------------------------------------------
    wm.add_region(Region("vale", "The Verdant Vale",
                         "Rolling farmland and the bustling town of Brackenford.",
                         controlling_faction="crown", danger_level=1,
                         lore="The Vale has known peace for thirty years, since the last war."))
    wm.add_region(Region("wilds", "Thornwood",
                         "A dark and tangled forest where bandits and beasts roam.",
                         controlling_faction="redhand", danger_level=2,
                         lore="They say the Thornwood swallows those who wander from the path."))
    wm.add_region(Region("mountains", "The Frostpeak Range",
                         "Jagged peaks, old mines, and colder things in the high passes.",
                         controlling_faction="", danger_level=4,
                         lore="A wyrm is said to slumber atop the highest peak."))
    wm.add_region(Region("marsh", "Mirewater Fen",
                         "A brooding wetland of black water and creeping mist.",
                         controlling_faction="fenfolk", danger_level=3,
                         lore="The Fen keeps its secrets, and its dead, close."))
    wm.add_region(Region("capital", "Highcrown",
                         "The grand capital, seat of the Crown and the Conclave.",
                         controlling_faction="crown", danger_level=0,
                         lore="Highcrown's white walls have never been breached."))

    def L(*args, **kwargs) -> None:
        wm.add_location(Location(*args, **kwargs))

    # ---- the Verdant Vale --------------------------------------------------
    L("brackenford_square", "Brackenford Square", "vale", Terrain.TOWN,
      "The cobbled heart of Brackenford. A well stands at its centre, ringed by "
      "shops and the comings and goings of townsfolk.",
      exits={"tavern": "gilded_stag", "inn": "the_rest", "smithy": "smithy",
             "market": "market", "temple": "temple", "north": "north_gate"},
      is_safe=True, points_of_interest=["notice_board", "well"],
      ambient=["A pair of children chase a dog across the square.",
               "A town crier clears his throat and thinks better of it.",
               "Pigeons scatter as a cart rumbles past."])
    L("gilded_stag", "The Gilded Stag", "vale", Terrain.TOWN,
      "A warm, smoky tavern loud with laughter and the clink of tankards.",
      exits={"out": "brackenford_square", "cellar": "stag_cellar"}, is_safe=True,
      points_of_interest=["cookfire", "hearth"],
      ambient=["Someone is butchering a drinking song by the fire.",
               "The smell of stew and spilled ale hangs thick."])
    L("stag_cellar", "The Stag's Cellar", "vale", Terrain.CAVE,
      "A dank cellar of ale barrels and crates — and the scrabble of vermin.",
      exits={"up": "gilded_stag"}, spawn_table=[("giant_rat", 2.0)],
      ambient=["Something with too many legs darts behind a barrel."])
    L("the_rest", "The Weary Rest", "vale", Terrain.TOWN,
      "A modest inn with creaking beds and a sleepy cat by the door.",
      exits={"out": "brackenford_square"}, is_safe=True,
      points_of_interest=["beds"],
      ambient=["The innkeeper's cat regards you with supreme indifference."])
    L("smithy", "Brackenford Smithy", "vale", Terrain.TOWN,
      "Heat rolls from the forge. Tools and half-finished blades line the walls.",
      exits={"out": "brackenford_square"}, is_safe=True,
      points_of_interest=["forge", "anvil"],
      ambient=["The ring of hammer on steel sets a steady rhythm."])
    L("market", "Brackenford Market", "vale", Terrain.TOWN,
      "Stalls crowd together, hawking everything from turnips to trinkets.",
      exits={"out": "brackenford_square"}, is_safe=True,
      ambient=["A fishmonger bellows the day's prices.",
               "Someone tries to sell you a 'genuine' dragon tooth."])
    L("temple", "Temple of the Dawn", "vale", Terrain.TOWN,
      "Sunlight streams through stained glass onto a quiet stone altar.",
      exits={"out": "brackenford_square"}, is_safe=True,
      points_of_interest=["altar"],
      ambient=["A hush of incense and murmured prayer fills the air."])
    L("north_gate", "Brackenford North Gate", "vale", Terrain.TOWN,
      "The town's timber gate, guarded and opening onto the King's Road.",
      exits={"square": "brackenford_square", "road": "kings_road"}, is_safe=True,
      ambient=["A bored guard waves travellers through."])
    L("kings_road", "The King's Road", "vale", Terrain.ROAD,
      "A broad dirt road winding between the realm's regions.",
      exits={"brackenford": "north_gate", "thornwood": "thornwood_edge",
             "mountains": "mountain_foot", "fen": "fen_road", "capital": "capital_gate",
             "fields": "millfield"},
      spawn_table=[("wolf", 1.0), ("bandit", 1.2)],
      ambient=["Dust rises behind a distant merchant caravan.",
               "A crow watches you from a fencepost."])
    L("millfield", "Millfield", "vale", Terrain.PLAINS,
      "Golden fields of grain ripple in the wind around an old mill.",
      exits={"road": "kings_road"}, spawn_table=[("wolf", 1.0)],
      ambient=["The mill's great wheel turns with a slow groan."])

    # ---- Thornwood ---------------------------------------------------------
    L("thornwood_edge", "Thornwood Edge", "wilds", Terrain.FOREST,
      "The treeline looms dark and close. The road dwindles to a path.",
      exits={"road": "kings_road", "deeper": "deep_thornwood"},
      spawn_table=[("wolf", 1.5), ("bandit", 1.0)],
      ambient=["Branches creak overhead though there is no wind.",
               "Something rustles in the undergrowth, then stills."])
    L("deep_thornwood", "Deep Thornwood", "wilds", Terrain.FOREST,
      "Ancient trees blot out the sky. It is easy to lose one's way here.",
      exits={"edge": "thornwood_edge", "shrine": "old_shrine", "camp": "bandit_camp"},
      spawn_table=[("wolf", 1.5), ("giant_spider", 1.2), ("bandit", 0.8)],
      ambient=["Spiderwebs as thick as rope stretch between the trunks.",
               "A distant howl raises the hairs on your neck."])
    L("old_shrine", "The Forgotten Shrine", "wilds", Terrain.RUINS,
      "A crumbling shrine reclaimed by moss and root. Bones litter the ground.",
      exits={"forest": "deep_thornwood"},
      spawn_table=[("skeleton", 1.5), ("giant_spider", 0.6)],
      points_of_interest=["altar"],
      ambient=["The air is cold and still, as if holding its breath."])
    L("bandit_camp", "Redhand Camp", "wilds", Terrain.RUINS,
      "A squalid camp of lean-tos and cookfires, marked by red-painted handprints.",
      exits={"forest": "deep_thornwood"},
      spawn_table=[("bandit", 2.0), ("bandit_chief", 0.4)],
      ambient=["A captured banner hangs torn above the largest tent."])

    # ---- Frostpeak Range ---------------------------------------------------
    L("mountain_foot", "Foot of the Frostpeaks", "mountains", Terrain.MOUNTAIN,
      "The road gives way to rocky switchbacks climbing into the heights.",
      exits={"road": "kings_road", "mine": "mine_entrance", "pass": "frostpeak_pass"},
      spawn_table=[("wolf", 1.2), ("kobold", 1.0)],
      ambient=["Loose scree skitters down the slope.",
               "The wind carries the bite of distant snow."])
    L("mine_entrance", "Old Mine Entrance", "mountains", Terrain.CAVE,
      "A timber-framed shaft descends into darkness. Rusted carts lie abandoned.",
      exits={"out": "mountain_foot", "deeper": "deep_mine"},
      spawn_table=[("kobold", 1.5), ("giant_spider", 1.0)],
      points_of_interest=["ore_vein"],
      ambient=["Water drips somewhere in the dark beyond your light."])
    L("deep_mine", "The Deep Mine", "mountains", Terrain.DUNGEON,
      "Black tunnels twist down into the mountain's roots. Something stirs.",
      exits={"up": "mine_entrance"},
      spawn_table=[("kobold", 1.0), ("stone_golem", 0.8)],
      points_of_interest=["ore_vein", "gem_vein"],
      ambient=["A deep grinding echoes, like stone moving against stone."])
    L("frostpeak_pass", "Frostpeak Pass", "mountains", Terrain.MOUNTAIN,
      "A knife-edge pass through wind-scoured ice and bare grey rock.",
      exits={"down": "mountain_foot", "summit": "dragon_lair"},
      spawn_table=[("frost_wolf", 1.5)],
      ambient=["Ice glitters on every surface. Your breath fogs and freezes."])
    L("dragon_lair", "The Wyrm's Roost", "mountains", Terrain.DUNGEON,
      "A vast cavern of scorched stone and gleaming hoarded gold. Heat shimmers.",
      exits={"pass": "frostpeak_pass"},
      spawn_table=[("dragon", 1.0)],
      points_of_interest=["hoard"],
      ambient=["The ground is warm. A slow, vast breathing fills the dark."])

    # ---- Mirewater Fen -----------------------------------------------------
    L("fen_road", "Mirewater Causeway", "marsh", Terrain.SWAMP,
      "A rotting boardwalk threads across black, reed-choked water.",
      exits={"road": "kings_road", "hut": "witch_hut", "ruins": "sunken_ruins"},
      spawn_table=[("bog_lurker", 1.2), ("giant_spider", 0.6)],
      ambient=["Bubbles rise and pop in the murk.",
               "A heron stabs at something beneath the surface."])
    L("witch_hut", "The Hedge-Witch's Hut", "marsh", Terrain.SWAMP,
      "A stilted shack hung with drying herbs, charms and stranger things.",
      exits={"out": "fen_road"}, is_safe=True,
      points_of_interest=["alchemy_table", "cauldron"],
      ambient=["Something in a jar on the shelf appears to be watching you."])
    L("sunken_ruins", "The Sunken Ruins", "marsh", Terrain.DUNGEON,
      "Drowned halls of a forgotten people, half-swallowed by the fen.",
      exits={"out": "fen_road"},
      spawn_table=[("skeleton", 1.2), ("wraith", 0.8), ("bog_lurker", 0.6)],
      points_of_interest=["relic_pedestal"],
      ambient=["Water laps at toppled columns carved with unknown runes."])

    # ---- Highcrown ---------------------------------------------------------
    L("capital_gate", "Highcrown Gates", "capital", Terrain.CASTLE,
      "Towering white walls and a portcullis flanked by the Crown's knights.",
      exits={"road": "kings_road", "market": "grand_market", "cathedral": "cathedral",
             "conclave": "conclave_tower", "castle": "castle_keep"},
      is_safe=True,
      ambient=["Knights in polished plate stand watch, impassive."])
    L("grand_market", "The Grand Bazaar", "capital", Terrain.CASTLE,
      "A sprawling covered market where fortunes change hands hourly.",
      exits={"gate": "capital_gate"}, is_safe=True,
      points_of_interest=["loom"],
      ambient=["A hundred languages of coin and barter fill the air."])
    L("cathedral", "Cathedral of the Dawn", "capital", Terrain.CASTLE,
      "A soaring nave of white stone and gold, hymns echoing from the choir.",
      exits={"out": "capital_gate"}, is_safe=True,
      points_of_interest=["altar", "reliquary"],
      ambient=["Light falls in coloured shafts from windows high above."])
    L("conclave_tower", "The Conclave Spire", "capital", Terrain.CASTLE,
      "A slender tower crackling with contained magic and quiet scholarship.",
      exits={"out": "capital_gate"}, is_safe=True,
      points_of_interest=["arcane_font", "library"],
      ambient=["Books drift past of their own accord, pages whispering."])
    L("castle_keep", "Highcrown Keep", "capital", Terrain.CASTLE,
      "The throne room of Aldermere, all banners, marble and cold authority.",
      exits={"out": "capital_gate"}, is_safe=True,
      points_of_interest=["throne"],
      ambient=["Courtiers murmur and scheme in the long shadows of the pillars."])
