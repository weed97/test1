# Module layout (feature packages)

Python simulation code is moving from a flat `utils/` tree into **feature packages** with **shims** at the old import paths. Existing `from utils.agent_mind import …` calls keep working.

## Principles

1. **One feature, one folder** — ecology, kingdom, combat, progression, turn, narrative, …
2. **Shims first** — move implementation, leave `utils/<old_name>.py` as re-export until callers are updated
3. **No big-bang** — migrate leaf modules before hubs (`field_agents`, `turn_processor`, `game_session`)
4. **Ask before breaking changes** — public API paths and on-disk state shape need explicit approval

## Current packages

| Package | Contents | Shim paths |
|---------|----------|------------|
| `utils/ecology/` | agent planning, beat orchestration, action keys, ecology state bucket | `agent_mind`, `ecology_beat`, `ecology_state`, `action_keys` |
| `utils/llm/` | LLM router, providers, pipeline | (already packaged) |

## Planned packages (order)

| Phase | Package | Modules |
|-------|---------|---------|
| next | `utils/kingdom/` | `settlement_build`, `kingdom_system`, `kingdom_war`, `civilization_coupling`, `world_conflicts` |
| then | `utils/combat/` | `combat_precision`, `combat_stats`, `combat_skill_ai`, `skill_effects` |
| then | `utils/progression/` | `progression`, `skill_catalog`, `level_unlocks`, `item_catalog`, … |
| then | `utils/narrative/` | `event_engine`, `faction_engine`, `main_story_engine`, `world_tension` |
| last | `utils/turn/` | `rule_engine`, `world_systems`, `temporal`, `world_clock` |

## Stay at `utils/` root (stable API)

- `game_session`, `turn_processor`, `turn_context`
- `state_manager`, `state_loader`, `state_store`
- `llm_client`, `llm_router`, `cli`
- `io_helpers`, `config_loader`

## Agent AI (merged)

Sequential ticks (`tick_agent_mind`) and parallel beats (`plan_agent_beat`) both call **`plan_agent_action`** in `utils/ecology/agent_mind.py`. Parallel mode still resolves combat in batch via `parallel_beat.resolve_and_commit_field_beat`.
