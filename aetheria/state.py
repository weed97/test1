"""The central :class:`World` container that wires every subsystem together.

Almost every other module takes a ``world`` and reaches into it for registries, the
clock, the RNG, the living NPC population, the market, factions and quests.  Keeping
this wiring in one place makes save/load and the simulation loop straightforward.
"""

from __future__ import annotations

from .crafting import CraftingManager, RecipeRegistry
from .dialogue import DialogueEngine
from .economy import Market, TradeSession
from .events import EventDeck
from .faction import FactionRegistry
from .gametime import GameClock
from .items import ItemRegistry
from .quest import QuestManager, QuestRegistry
from .rng import GameRandom
from .skills import AbilityRegistry, ClassRegistry
from .world import WorldMap


class World:
    def __init__(self, seed: int | str | None = None) -> None:
        self.rng = GameRandom(seed)
        self.seed = self.rng.seed
        self.clock = GameClock()

        # static registries (content)
        self.items = ItemRegistry()
        self.abilities = AbilityRegistry()
        self.classes = ClassRegistry()
        self.recipes = RecipeRegistry()
        self.quests = QuestRegistry()
        self.map = WorldMap()
        self.factions = FactionRegistry()
        self.event_deck = EventDeck()

        # dynamic systems
        self.market = Market(self.rng)
        self.trade = TradeSession(self.market, self.factions, self.rng)
        self.crafting = CraftingManager(self.recipes, self.items, self.rng)
        self.quest_manager = QuestManager(self.quests)
        self.dialogue = DialogueEngine(self.rng)

        # living world state
        self.npcs: dict = {}
        self.player = None
        self.rumor_pool: list[str] = []
        self.chronicle: list[str] = []
        self.tick_count = 0
        self.bestiary: dict = {}        # monster_template_id -> spawn spec
        self._monster_serial = 0

    def spawn_monster(self, template_id: str):
        """Instantiate a fresh combat NPC from a bestiary template."""
        from .character import NPC, Personality
        spec = self.bestiary.get(template_id)
        if not spec:
            return None
        self._monster_serial += 1
        npc = NPC(f"{template_id}#{self._monster_serial}", spec["name"], self.items,
                  role=spec.get("role", "monster"),
                  faction=spec.get("faction", ""),
                  level=spec.get("level", 1))
        npc.species = spec.get("species", "beast")
        npc.attrs.strength = spec.get("strength", 10)
        npc.attrs.dexterity = spec.get("dexterity", 10)
        npc.attrs.constitution = spec.get("constitution", 10)
        npc.attrs.intelligence = spec.get("intelligence", 8)
        npc.attrs.wisdom = spec.get("wisdom", 8)
        npc.attrs.charisma = spec.get("charisma", 6)
        npc.abilities = list(spec.get("abilities", []))
        npc.loot_table = list(spec.get("loot_table", []))
        npc.xp_reward = spec.get("xp_reward", 10)
        npc.gold = spec.get("gold", 0)
        npc.hostile_by_default = True
        for item_id in spec.get("equipment", []):
            npc.inventory.add(item_id)
            npc.inventory.equip(item_id)
        npc.full_restore()
        return npc

    # -- population helpers --------------------------------------------------
    def add_npc(self, npc) -> None:
        self.npcs[npc.id] = npc

    def get_npc(self, npc_id: str):
        return self.npcs.get(npc_id)

    def npcs_at(self, location_id: str) -> list:
        return [n for n in self.npcs.values()
                if n.current_location == location_id and n.alive]

    def living_npcs_at(self, location_id: str) -> list:
        return [n for n in self.npcs_at(location_id) if n.alive]

    def find_npc_by_name(self, name: str, location_id: str | None = None):
        name = name.lower().strip()
        candidates = list(self.npcs.values())
        if location_id is not None:
            candidates = self.npcs_at(location_id)
        for npc in candidates:
            if npc.name.lower() == name:
                return npc
        for npc in candidates:
            if name in npc.name.lower():
                return npc
        return None
