# AGENTS.md

Guidance for AI agents working in this repository.

## Project identity

**This is NOT a game.** It is a **data-creation-based autonomous simulation engine** (CPoW — Creativity-Proof of Work). See [`.cursorrules`](.cursorrules) and [`docs/CPOW_ARCHITECTURE.md`](docs/CPOW_ARCHITECTURE.md).

## Repository layout

| Path | Role |
|------|------|
| `cpow_engine/` | **Core engine** — physics, CPoW scoring, shared state |
| `fantasy_simulator/` | Eldoria legacy — transitioning to CPoW adapters |
| `cpow_client/godot/` | **CPoW World Client** — areas API, VRoid/glb (not Eldoria 2D) |
| `sungjwa_hunter_sim/` | 성좌 헌터 sim — CPoW adapter planned |
| `mmorpg_sim/`, `fantasy_mmorpg/` | Legacy text sims |
| `item_catalog/` | Item catalog web UI |

## Stack

- **Python 3.10+** (VM has 3.12). CPoW engine: **stdlib + unittest only**.
- `fantasy_simulator` API may require `pip install -r requirements-api.txt`.

## CPoW engine (primary)

```bash
# Demo: create Heat object → energy generation
python3 -m cpow_engine.demo --seed 42 --ticks 3

# L1 protocol demo: off-chain → on-chain submission
python3 -m cpow_engine.demo --chain --seed 42 --ticks 5

# Tests
python3 -m unittest discover -s cpow_engine/tests -v

# Phase 2: bot vulnerability simulation
python3 -m cpow_engine.bot_sim

# Compile check
python3 -m compileall -q cpow_engine
```

## Sungjwa hunter sim (legacy)

```bash
cd sungjwa_hunter_sim
python3 -m unittest discover -s tests -v
python3 main.py --hunter kim_dokja --seed 42 --turns 4 --no-persist
```

## Implementation rules

1. **No hardcoded physics** — use property definitions (`heat_intensity`, `material_type`, etc.)
2. **Data is law** — define schemas before writing interaction code
3. **Anti-bot heuristics** — entropy-based rewards, repetition penalties
4. **Small MVPs** — e.g. "create heat → generate energy" before "build a world"
5. **Fantasy → property substitution** — replace `fireball` skill with `heat_intensity` object

## Config side effects

`sungjwa_hunter_sim/main.py` persists external-update changes to `config/variables.json` unless `--no-persist` is set.
