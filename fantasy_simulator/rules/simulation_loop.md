# Simulation Loop

The world advances in **ticks** (one tick = one in-world hour). `simulation_engine.py`
is the orchestrator; the **director** role chooses each beat. The world keeps living
whether or not the player acts.

## Each tick, in order
1. **Advance time.** Update the clock (hour → time-of-day → day → season).
2. **Move characters.** Each NPC goes to the location their daily `schedule` dictates
   for the current time-of-day.
3. **Drift moods & regenerate.** Moods ease toward temperament; resources recover.
4. **Director beat.** Pick ONE of:
   - `advance_time` — a quiet hour passes;
   - `npc_activity` — co-located NPCs interact (gossip, banter, small deeds);
   - `world_event` — generate a headline that shocks the market / shifts moods;
   - `rumor_spread` — a rumour propagates from one NPC to others nearby.
5. **Spread rumours.** Co-located NPCs may exchange known rumours.
6. **Resolve skirmishes.** In dangerous places, hostiles may clash with others
   (dice-resolved, off-screen unless the player is present).
7. **Memory upkeep.** Append notable events; summarise when a character's recent log
   grows too long.
8. **Persist.** Write `world_state.json` and changed character files (atomic).

## World events
Use the `world_event` role to emit strict JSON:
`{"headline": ..., "rumor": ..., "mood_shift": -8..8, "market": {tag: multiplier}}`.
Keep events plausible for the season and current flags (e.g. dragon omens build toward
`dragon_awake`).

## Pacing
Most ticks should be quiet (`advance_time` / `npc_activity`). World events are rarer
(roughly one per in-world day). Long simulations must stay cheap: prefer the small/fast
model for ambient beats and reserve the strong model for the player's direct scenes.
