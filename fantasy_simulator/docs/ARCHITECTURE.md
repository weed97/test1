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
| `utils/state_report.py` | CLI status/summary formatting (presentation only) |
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

## World systems (faction, tension, main story)

End of each turn (`execute_turn` → `tick_world_systems`):

| Module | Config | State keys |
|--------|--------|------------|
| `utils/faction_engine.py` | `config/factions.json` | `flags.faction_reputation` (+ legacy `flags.reputation` sync) |
| `utils/world_tension.py` | tiers in code | `world.tension` (0–100) |
| `utils/main_story_engine.py` | `events/main_stories.json` | `flags.main_story` |

Event seeds may gate on `requires_faction_min/max`, `requires_tension_min/max`, and apply `faction_reputation` in outcomes. Legacy quest `reputation.ashpoint` etc. map to faction IDs via `legacy_reputation_keys`.

Long-term arcs: `seal_breaking` (default, linked to `smoke_on_the_mountain`), `crown_war`, `otherworld_invasion`.

**Six factions** (v2): 애쉬포인트 자치회, 실버우드 상인 연합, 검은송곳니 산적단, 잿빛 감시자, 칠흑의 서약, 은빛 십자 기사단 — see `config/factions.json` for relationship matrix (hostile / friendly / neutral / utilize) and reputation milestones (±40 triggers major events).

Player rep mirrors to `state.factions.player_reputation` for `world_state.json` readability.

## Keyword routing (default)

| Input keywords | Model |
|----------------|-------|
| fight, attack, cast, magic, combat | Codex (JSON) |
| talk, look, explore, investigate | Claude (text) |
| rest, unknown | rule engine |

Active combat always routes to Codex.

## Files to ignore

- `utils/llm/pipeline.py` — deprecated legacy pipeline

## Testing

Unit tests use `tests/fixtures.isolated_game_root()` to copy game data into a temp directory so turns do not mutate the repo's `state/` shards.

Hybrid / LLM paths use `tests/mock_llm_client.MockLLMClient` injected via `TurnContext.client` or `GameSession(..., client=mock)`.

Interactive mode supports **Tab completion** when `readline` is available (`utils/cli.completion_candidates`).

```bash
python3 -m unittest discover -s tests -v
```
