"""Tests for the LLM-orchestrated fantasy_simulator layer (offline / mock provider)."""

from __future__ import annotations

import os

import pytest

from fantasy_simulator import PROMPTS_DIR, RULES_DIR
from fantasy_simulator.simulation_engine import SimulationEngine, _time_of_day
from fantasy_simulator.utils import ContextBuilder, LLMClient, StateStore
from fantasy_simulator.utils import engine_bridge
from fantasy_simulator.utils.memory import MemoryManager

ASSIGNMENTS = os.path.join(PROMPTS_DIR, "model_assignments.json")


@pytest.fixture
def temp_world(tmp_path):
    ws = str(tmp_path / "world_state.json")
    cdir = str(tmp_path / "characters")
    store = StateStore(ws, cdir)
    info = engine_bridge.generate_world_files(store, seed="test")
    store.load_world()
    store.load_characters()
    return store, info, ws, cdir


# --------------------------------------------------------------------------- #
#  Time
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("hour,label", [
    (6, "Dawn"), (8, "Morning"), (12, "Noon"), (15, "Afternoon"),
    (18, "Dusk"), (22, "Night"), (2, "Midnight"), (0, "Midnight"),
])
def test_time_of_day(hour, label):
    assert _time_of_day(hour) == label


# --------------------------------------------------------------------------- #
#  World generation / state IO
# --------------------------------------------------------------------------- #
def test_generate_world_files(temp_world):
    store, info, ws, cdir = temp_world
    assert os.path.exists(ws)
    assert info["locations"] > 20
    assert info["characters"] >= 10
    assert "player" in store.characters
    # every character references a real location
    locs = set(store.world["locations"].keys())
    for c in store.characters.values():
        assert c.get("current_location") in locs


def test_state_roundtrip_atomic(temp_world):
    store, info, ws, cdir = temp_world
    store.world["global_flags"]["test_flag"] = True
    store.save_world()
    fresh = StateStore(ws, cdir)
    assert fresh.load_world()["global_flags"]["test_flag"] is True


# --------------------------------------------------------------------------- #
#  LLM client (offline)
# --------------------------------------------------------------------------- #
def test_llm_client_mock_routes_and_records():
    client = LLMClient(ASSIGNMENTS)
    resp = client.complete("director", "system", "pick a beat",
                           {"role": "director", "seed_key": "x"})
    assert resp.text
    assert resp.provider == "mock"  # no API keys -> fallback
    assert client.stats


def test_llm_force_provider():
    client = LLMClient(ASSIGNMENTS, force_provider="mock")
    resp = client.complete("narrator", "sys", "describe",
                           {"role": "narrator", "location": "the square"})
    assert resp.provider == "mock"
    assert "square" in resp.text.lower() or resp.text


def test_world_event_json_parses():
    client = LLMClient(ASSIGNMENTS, force_provider="mock")
    resp = client.complete("world_event", "sys", "make event", {"role": "world_event"})
    import json
    data = json.loads(resp.text)
    assert "headline" in data


# --------------------------------------------------------------------------- #
#  Context builder
# --------------------------------------------------------------------------- #
def test_context_builder_npc(temp_world):
    store, *_ = temp_world
    cb = ContextBuilder(PROMPTS_DIR, RULES_DIR)
    bram = store.get_character("bram")
    system, user, ctx = cb.build_npc(bram, store.world, "A scene.", "Hello there.",
                                     topic="rumors")
    assert "character sheet" in system.lower()
    assert "Bram" in system
    assert ctx["role"] == "npc"


def test_context_builder_rules_loaded():
    cb = ContextBuilder(PROMPTS_DIR, RULES_DIR)
    assert "Mana" in cb.rule("magic_system")
    assert cb.prompt("narrator")


# --------------------------------------------------------------------------- #
#  Memory
# --------------------------------------------------------------------------- #
def test_memory_summarizes_when_full(temp_world):
    store, *_ = temp_world
    client = LLMClient(ASSIGNMENTS, force_provider="mock")
    cb = ContextBuilder(PROMPTS_DIR, RULES_DIR)
    mm = MemoryManager(store, client, cb, recent_threshold=4, keep_recent=2)
    bram = store.get_character("bram")
    for i in range(6):
        mm.remember(bram, f"event {i}")
    assert bram["memory"]["summary"]
    # after summarising to keep_recent (2), at most a few new events accrue
    assert len(bram["memory"]["recent"]) <= mm.recent_threshold


# --------------------------------------------------------------------------- #
#  Engine tick (offline, temp world)
# --------------------------------------------------------------------------- #
def test_engine_tick_advances_and_persists(tmp_path):
    ws = str(tmp_path / "world_state.json")
    cdir = str(tmp_path / "characters")
    engine = SimulationEngine(force_provider="mock", world_state_path=ws,
                              characters_dir=cdir, logs_dir=str(tmp_path / "logs"))
    engine.generate(seed="test")
    engine.load()
    start = engine.world["time"]["tick"]
    engine.simulate(8, verbose=False)
    assert engine.world["time"]["tick"] == start + 8
    # reload from disk proves persistence
    fresh = StateStore(ws, cdir)
    assert fresh.load_world()["time"]["tick"] == start + 8


def test_engine_npc_movement_follows_schedule(tmp_path):
    ws = str(tmp_path / "world_state.json")
    cdir = str(tmp_path / "characters")
    engine = SimulationEngine(force_provider="mock", world_state_path=ws,
                              characters_dir=cdir, logs_dir=str(tmp_path / "logs"))
    engine.generate(seed="test")
    engine.load()
    engine.simulate(24, verbose=False)
    locs = set(engine.world["locations"].keys())
    for npc in engine._active_npcs():
        assert npc["current_location"] in locs


def test_engine_talk_updates_relationship(tmp_path):
    ws = str(tmp_path / "world_state.json")
    cdir = str(tmp_path / "characters")
    engine = SimulationEngine(force_provider="mock", world_state_path=ws,
                              characters_dir=cdir, logs_dir=str(tmp_path / "logs"))
    engine.generate(seed="test")
    engine.load()
    bram = engine.store.get_character("bram")
    player = engine._player()
    player["current_location"] = bram["current_location"]
    before = bram.get("relationship_to_player", 0)
    engine.talk("Bram", "You keep a wonderful tavern, thank you friend!")
    assert bram["relationship_to_player"] >= before
