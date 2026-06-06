from mmorpg_sim.engine import SimulatorEngine


def test_dialogue_replies_and_updates_memory() -> None:
    engine = SimulatorEngine(player_name="Speaker", seed=100)
    engine.player.region_key = "moonmere"
    response = engine.talk("seer_liora", "I need a quest and rumor")
    assert "Seer Liora" in response
    npc = engine.world.npcs["seer_liora"]
    assert npc.memory


def test_positive_and_negative_tokens_shift_disposition() -> None:
    engine = SimulatorEngine(player_name="Speaker", seed=100)
    engine.player.region_key = "goldmeadow"
    npc = engine.world.npcs["guildmaster_tovin"]
    start = npc.disposition
    engine.talk("guildmaster_tovin", "I bring trade and thanks")
    mid = npc.disposition
    engine.talk("guildmaster_tovin", "I will betray and steal")
    end = npc.disposition
    assert mid >= start
    assert end <= mid
