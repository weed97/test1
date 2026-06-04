# Architecture

## Turn flow (single path)

```
Cursor terminal / CLI
        │
        ▼
simulation_engine.py          (thin CLI entry)
        │
        ▼
utils/game_session.py
  GameSession.run_turn()      ← turn controller (state + engines)
        │
        ▼
utils/turn_processor.py
  execute_turn()              ← time advance, combat start
    process_player_action()   ← action resolution only
        │
        ├── utils/llm_router.decide_model_and_prompt()
        │
        ├── rule engine (utils/rule_engine.py)
        │
        └── utils/llm_client.py (live API or mock)
                │
                ▼
        utils/state_manager.py
          save state/ + mirror world_state.json
```

`SimulationEngine` is a backward-compatible alias for `GameSession`.

There is **no** `handle_player_action` or nested `process_turn` chain.

## Responsibilities

| Module | Role |
|--------|------|
| `simulation_engine.py` | argparse, REPL dispatch, debug flags |
| `utils/game_session.py` | Turn controller — holds state, wires engines |
| `utils/turn_processor.py` | Action resolution + full turn orchestration |
| `utils/turn_context.py` | `TurnContext` / `TurnResult` dataclasses |
| `utils/state_manager.py` | Persist shards, apply LLM results, status report |
| `utils/cli.py` | Input parsing, interactive loop, friendly errors |

## LLM providers

| Check | Command |
|-------|---------|
| Live vs mock | `python3 simulation_engine.py --show-providers` |
| Routing rules | `python3 simulation_engine.py --show-routing` |

Behavior:
1. No API key → mock provider (offline)
2. API key set → live Anthropic/OpenAI call
3. Live call fails → network retry → optional degrade to mock (`config/llm_routing.json` → `network`)
4. LLM still fails → rule engine fallback (`turn_processor`)

Result fields: `is_mock`, `degraded`, `fallback_reason`

## State storage

| Layer | Path | Role |
|-------|------|------|
| Canonical | `state/*.json` | Engine read/write (minimal) |
| Mirror | `world_state.json` | Cursor `@world_state.json` hub |
| Lore | `lore/`, `events/` | Rich text — loaded on demand for LLM only |

See [LORE_AND_EVENTS.md](LORE_AND_EVENTS.md).

## Keyword routing (default)

| Input keywords | Model |
|----------------|-------|
| fight, attack, cast, magic, combat | Codex (JSON) |
| talk, look, explore, investigate | Claude (text) |
| rest, unknown | rule engine |

Active combat always routes to Codex.

## Files to ignore

- `utils/llm/pipeline.py` — deprecated legacy pipeline
