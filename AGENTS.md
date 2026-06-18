# AGENTS.md — CPoW World

**Not a game.** Data-creation autonomous simulation (CPoW). See `docs/CPOW_ARCHITECTURE.md`.

## Layout

| Path | Role |
|------|------|
| `cpow_engine/` | Physics, CPoW scoring, areas, governance |
| `cpow_api/` | FastAPI — `/v1/areas/*`, auth, collab, XR |
| `cpow_client/godot/` | Godot 4 3D client |

## Commands

```bash
pip install -r requirements-api.txt
python3 -m cpow_engine.demo --areas
uvicorn cpow_api.server:app --host 127.0.0.1 --port 8765
bash scripts/verify.sh
```

Godot: open `cpow_client/godot/project.godot` (API server required).
