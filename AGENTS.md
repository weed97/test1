# AGENTS.md

Guidance for AI agents working in this repository.

## Repository layout

| Branch | Contents |
|--------|----------|
| `main` | Placeholder (`README.md` only) |
| `cursor/sungjwa-hunter-simulator-ace2` | **성좌 헌터 시뮬레이션** — Python CLI in `sungjwa_hunter_sim/` |

If `sungjwa_hunter_sim/` is missing, check out the simulator branch:

```bash
git fetch origin cursor/sungjwa-hunter-simulator-ace2
git checkout cursor/sungjwa-hunter-simulator-ace2
```

## Cursor Cloud specific instructions

### Stack

- **Python 3.10+** (VM has 3.12). **No pip dependencies** — stdlib + `unittest` only.
- No Docker, databases, or long-running servers.

### Working directory

All commands assume `cd sungjwa_hunter_sim` (relative to repo root).

### Tests

```bash
cd sungjwa_hunter_sim
python3 -m unittest discover -s tests -v
```

### Run the simulator (dev)

```bash
cd sungjwa_hunter_sim
python3 main.py --hunter kim_dokja --seed 42 --turns 4
python3 main.py --list-hunters
python3 main.py --list-monsters
python3 main.py --query '[외부 업데이트] 질의: randomness_intensity=2.6'
```

Use `--interactive` only when a TTY is available; prefer `--turns`, `--seed`, and `--query` in cloud/CI.

### Lint / format

No project-level Ruff, flake8, or mypy config. Optional sanity check:

```bash
python3 -m compileall -q sungjwa_hunter_sim/src sungjwa_hunter_sim/tests
```

### Config side effects

`main.py` persists external-update changes to `config/variables.json` unless `--no-persist` is set. Tests use temp copies of config and do not require resetting the repo file after `unittest`.

### Branch checkout note

Cloud VMs may start on `main` (empty tree). The application under test is not on `main`; switch to `cursor/sungjwa-hunter-simulator-ace2` before running tests or the CLI.
