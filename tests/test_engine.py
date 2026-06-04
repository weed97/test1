"""Unit tests for the Aetheria engine and content."""

from __future__ import annotations

import os
import tempfile

import pytest

from aetheria import persistence
from aetheria.combat import ActionType, Battle, CombatAction
from aetheria.content import build_world
from aetheria.economy import format_coins
from aetheria.gametime import GameClock, Season
from aetheria.game.factory import create_player
from aetheria.items import EquipSlot, Inventory, ItemRegistry, ItemTemplate, ItemType
from aetheria.quest import ObjectiveType
from aetheria.rng import GameRandom
from aetheria.simulation import Simulation
from aetheria.stats import Attribute, AttributeBlock, DerivedStats


# --------------------------------------------------------------------------- #
#  RNG                                                                         #
# --------------------------------------------------------------------------- #
def test_rng_is_deterministic():
    a = GameRandom("hello")
    b = GameRandom("hello")
    assert a.seed == b.seed
    assert [a.randint(1, 100) for _ in range(20)] == [b.randint(1, 100) for _ in range(20)]


def test_rng_string_seed_stable():
    assert GameRandom("aldermere").seed == GameRandom("aldermere").seed


# --------------------------------------------------------------------------- #
#  Game time                                                                   #
# --------------------------------------------------------------------------- #
def test_clock_progression():
    clock = GameClock(total_hours=6)
    assert clock.day_index == 0
    assert clock.year == 1
    clock.advance(24)
    assert clock.day_index == 1
    assert clock.hour == 6


def test_clock_seasons_cycle():
    clock = GameClock(total_hours=0)
    assert clock.season == Season.SPRING
    clock.advance(24 * 30)  # one season
    assert clock.season == Season.SUMMER


# --------------------------------------------------------------------------- #
#  Stats                                                                       #
# --------------------------------------------------------------------------- #
def test_attribute_modifier():
    attrs = AttributeBlock(strength=16, dexterity=8)
    assert attrs.modifier(Attribute.STRENGTH) == 3
    assert attrs.modifier(Attribute.DEXTERITY) == -1


def test_derived_scales_with_level():
    attrs = AttributeBlock(constitution=14)
    low = DerivedStats.compute(attrs, 1)
    high = DerivedStats.compute(attrs, 5)
    assert high.max_health > low.max_health


# --------------------------------------------------------------------------- #
#  Inventory                                                                   #
# --------------------------------------------------------------------------- #
def _mini_registry() -> ItemRegistry:
    reg = ItemRegistry()
    reg.register(ItemTemplate("sword", "Sword", ItemType.WEAPON, slot=EquipSlot.MAIN_HAND,
                              attack_bonus=3, damage_dice=(1, 8)))
    reg.register(ItemTemplate("potion", "Potion", ItemType.CONSUMABLE, stackable=True,
                              max_stack=10, heal_amount=20))
    return reg


def test_inventory_stacking_and_removal():
    inv = Inventory(_mini_registry())
    inv.add("potion", 5)
    inv.add("potion", 7)
    assert inv.count("potion") == 12
    assert inv.remove("potion", 4)
    assert inv.count("potion") == 8
    assert not inv.remove("potion", 100)


def test_inventory_equip_swaps():
    inv = Inventory(_mini_registry())
    inv.add("sword", 1)
    ok, _ = inv.equip("sword")
    assert ok
    assert inv.total_attack_bonus() == 3
    assert inv.equipment[EquipSlot.MAIN_HAND] == "sword"


# --------------------------------------------------------------------------- #
#  World content                                                               #
# --------------------------------------------------------------------------- #
@pytest.fixture
def world():
    return build_world("pytest-seed")


def test_world_builds_with_content(world):
    assert len(world.items.all()) > 30
    assert len(world.map.locations) > 20
    assert len(world.npcs) >= 10
    assert len(world.quests.all()) >= 6
    assert world.player is None


def test_map_is_connected(world):
    # every location should be reachable from the start
    start = "brackenford_square"
    reachable = {start}
    frontier = [start]
    while frontier:
        cur = frontier.pop()
        for dest in world.map.locations[cur].exits.values():
            if dest not in reachable:
                reachable.add(dest)
                frontier.append(dest)
    assert reachable == set(world.map.locations.keys())


def test_npc_schedule_locations_exist(world):
    for npc in world.npcs.values():
        for loc_id in npc.schedule.values():
            assert loc_id in world.map.locations


def test_spawn_table_references_valid_monsters(world):
    for loc in world.map.locations.values():
        for template_id, _ in loc.spawn_table:
            assert template_id in world.bestiary


def test_shop_items_exist(world):
    for npc in world.npcs.values():
        for item_id in npc.shop_inventory:
            assert world.items.exists(item_id)


# --------------------------------------------------------------------------- #
#  Player creation                                                             #
# --------------------------------------------------------------------------- #
def test_create_player_each_class(world):
    for cls in world.classes.all():
        w = build_world("pytest-seed")
        player = create_player(w, "Tester", cls.id)
        assert player.health > 0
        assert player.abilities
        assert player.location_id == "brackenford_square"


# --------------------------------------------------------------------------- #
#  Combat                                                                      #
# --------------------------------------------------------------------------- #
def test_combat_resolves(world):
    hero = create_player(world, "Hero", "warrior")
    rat = world.spawn_monster("giant_rat")
    battle = Battle([hero], [rat], world.abilities, world.rng)
    outcome = battle.auto_resolve()
    assert outcome in ("players", "enemies", "draw")
    assert battle.over


def test_strong_hero_beats_weak_monster(world):
    hero = create_player(world, "Hero", "warrior")
    hero.level = 8
    hero.attrs.strength = 20
    hero.full_restore()
    rat = world.spawn_monster("giant_rat")
    battle = Battle([hero], [rat], world.abilities, world.rng)
    assert battle.auto_resolve() == "players"


def test_ability_consumes_resource(world):
    hero = create_player(world, "Mage", "mage")
    firebolt = world.abilities.get("firebolt")
    rat = world.spawn_monster("giant_rat")
    battle = Battle([hero], [rat], world.abilities, world.rng)
    before = hero.mana
    battle.perform(CombatAction(hero, ActionType.ABILITY, target=rat, ability=firebolt))
    assert hero.mana == before - firebolt.cost


# --------------------------------------------------------------------------- #
#  Dialogue                                                                    #
# --------------------------------------------------------------------------- #
def test_dialogue_topics_and_response(world):
    player = create_player(world, "Hero", "rogue")
    bram = world.npcs["bram"]
    topics = world.dialogue.available_topics(bram, player)
    assert any(t.key == "trade" for t in topics)
    result = world.dialogue.handle(bram, player, world.clock, "compliment", world=world)
    assert result.lines


def test_gift_improves_relationship(world):
    player = create_player(world, "Hero", "rogue")
    player.inventory.add("ruby", 1)
    bram = world.npcs["bram"]
    before = bram.relationship
    world.dialogue.handle(bram, player, world.clock, "gift", world=world, gift_item="ruby")
    assert bram.relationship > before
    assert not player.inventory.has("ruby")


# --------------------------------------------------------------------------- #
#  Quests                                                                      #
# --------------------------------------------------------------------------- #
def test_quest_lifecycle(world):
    player = create_player(world, "Hero", "warrior")
    qm = world.quest_manager
    assert qm.can_start(player, "q_rats")
    qm.start(player, "q_rats")
    assert "q_rats" in player.active_quests
    for _ in range(5):
        qm.record_event(player, ObjectiveType.KILL, "giant_rat")
    assert qm.is_complete(player, "q_rats")
    qm.turn_in(player, "q_rats", world)
    assert "q_rats" in player.completed_quests
    assert player.gold > 0


def test_collect_objective_reads_inventory(world):
    player = create_player(world, "Hero", "ranger")
    qm = world.quest_manager
    qm.start(player, "q_herbs")
    assert not qm.is_complete(player, "q_herbs")
    player.inventory.add("moonpetal", 4)
    assert qm.is_complete(player, "q_herbs")


def test_quest_prerequisite_blocks(world):
    player = create_player(world, "Hero", "paladin")
    assert not world.quest_manager.can_start(player, "q_dragon")  # needs q_tome


# --------------------------------------------------------------------------- #
#  Economy                                                                     #
# --------------------------------------------------------------------------- #
def test_format_coins():
    assert format_coins(0) == "0c"
    assert format_coins(105) == "1s 5c"
    assert format_coins(10000) == "1g 0c"


def test_buy_and_sell(world):
    player = create_player(world, "Hero", "warrior")
    player.gold = 1000
    mira = world.npcs["mira"]
    ok, _ = world.trade.buy(world.items, "iron_helm", player, mira, 1)
    assert ok
    assert player.inventory.has("iron_helm")
    ok, _ = world.trade.sell(world.items, "iron_helm", player, mira, 1)
    assert ok


def test_market_drift_bounded(world):
    world.market.shock("iron_sword", 2.0)
    for _ in range(200):
        world.market.drift()
    assert 0.5 <= world.market.index.get("iron_sword", 1.0) <= 2.5


# --------------------------------------------------------------------------- #
#  Crafting                                                                    #
# --------------------------------------------------------------------------- #
def test_crafting_consumes_inputs(world):
    player = create_player(world, "Hero", "warrior")
    player.inventory.add("iron_ore", 2)
    player.inventory.add("coal", 1)
    ok, msg = world.crafting.craft(player, "smelt_iron", {"forge"})
    assert ok, msg
    assert player.inventory.has("iron_ingot")
    assert not player.inventory.has("iron_ore")


def test_crafting_requires_station(world):
    player = create_player(world, "Hero", "warrior")
    player.inventory.add("iron_ore", 2)
    player.inventory.add("coal", 1)
    ok, _ = world.crafting.craft(player, "smelt_iron", set())
    assert not ok


# --------------------------------------------------------------------------- #
#  Faction / reputation                                                        #
# --------------------------------------------------------------------------- #
def test_reputation_ripples_to_rivals(world):
    player = create_player(world, "Hero", "warrior")
    world.factions.apply_reputation(player, "crown", 40)
    assert player.reputation_with("crown") == 40
    assert player.reputation_with("redhand") < 0  # crown's rival


# --------------------------------------------------------------------------- #
#  Simulation                                                                  #
# --------------------------------------------------------------------------- #
def test_simulation_advances_time(world):
    sim = Simulation(world)
    start = world.clock.total_hours
    sim.advance(24)
    assert world.clock.total_hours == start + 24


def test_simulation_moves_npcs_on_schedule(world):
    sim = Simulation(world)
    sim.advance(24)
    # all npcs should still be in valid locations
    for npc in world.npcs.values():
        assert npc.current_location in world.map.locations


# --------------------------------------------------------------------------- #
#  Persistence                                                                 #
# --------------------------------------------------------------------------- #
def test_save_load_roundtrip(world):
    player = create_player(world, "Saver", "cleric")
    player.gold = 321
    world.npcs["bram"].adjust_relationship(15)
    world.quest_manager.start(player, "q_rats")
    world.clock.advance(50)
    with tempfile.TemporaryDirectory() as tmp:
        path = os.path.join(tmp, "save.json")
        persistence.save(world, path)
        reloaded = persistence.load(path, build_world)
    assert reloaded.player.gold == 321
    assert reloaded.player.name == "Saver"
    assert reloaded.npcs["bram"].relationship == 15
    assert "q_rats" in reloaded.player.active_quests
    assert reloaded.clock.total_hours == world.clock.total_hours
