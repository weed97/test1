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

Long-term arc: **잿빛 봉인의 균열** — Phase 1 **균열의 전조** (`main_story_phase1.json`). Phase 2 **세력의 대립** (`main_story_phase2.json`). Phase 3 **최후의 선택** (reinforce/break/chaos final choice, path-based climax, ending resolution; `main_story_phase3.json`, `phase3_flow` in `events/main_stories.json`). Progress 100 resolves ending only after `phase3_climax_done`.

**World product framing:** Eldoria is designed as a **full-dive isekai VR** setting (Link OS meta layer, transfer contract, faction “guild flags”). See [design/README.md](design/README.md). Optional state: `flags.vr_meta` — schema in `config/vr_meta.schema.json`.

**Event zones:** `seed_type: main_story` (or `main_plot_link`) seeds without `location_zones` may trigger in `ashpoint`, `forest`, or `tower`. NPC-targeted `talk` no longer blocks main-story seeds that also allow `explore`.

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
