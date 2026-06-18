#!/usr/bin/env bash
# test1/main → cpow_world 전용 디렉터리 export (fantasy_simulator 등 제외)
set -euo pipefail

DEST="${1:?usage: export_cpow_world.sh DEST_DIR}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"

CPOW_DOCS=(
  AREA_DIPLOMACY.md
  AREA_EXTENT_NPC.md
  AREA_MODES.md
  AREA_SIEGE.md
  COLLABORATIVE_WORLD.md
  CPOW_ARCHITECTURE.md
  CPOW_PHASE2.md
  CPOW_ROADMAP.md
  CREATION_DESTRUCTION_POWERS.md
  HOST_SECURITY.md
  L1_PROTOCOL_ARCHITECTURE.md
  MOBILE_PUSH_CPOW.md
  P0_SECURITY.md
  PHYSICS_BALANCE.md
  PHYSICS_EXTENDED.md
  PUSH_CPOW_DEPLOY_KEY.md
  SPLIT_REPO.md
  SYNC_CPOW_WORLD.md
  SYSTEM_GOVERNANCE.md
  TODO_REMAINING.md
  XR_INTEGRATION.md
)

rm -rf "$DEST"
mkdir -p "$DEST/docs" "$DEST/scripts" "$DEST/.github/workflows"

echo "==> Copy cpow_engine, cpow_api, cpow_client, tests"
cp -a "$ROOT/cpow_engine" "$ROOT/cpow_api" "$ROOT/cpow_client" "$ROOT/tests" "$DEST/"

echo "==> Copy docs"
for f in "${CPOW_DOCS[@]}"; do
  if [[ -f "$ROOT/docs/$f" ]]; then
    cp "$ROOT/docs/$f" "$DEST/docs/"
  fi
done

echo "==> Copy scripts & requirements"
cp "$ROOT/scripts/verify_cpow.sh" "$DEST/scripts/verify.sh"
cp "$ROOT/requirements-cpow-api.txt" "$DEST/requirements-api.txt"

if [[ -f "$ROOT/scripts/clone_cpow_world.sh" ]]; then
  cp "$ROOT/scripts/clone_cpow_world.sh" "$DEST/scripts/"
fi

echo "==> README.md"
if [[ -f "$ROOT/README_CPOW.md" ]]; then
  sed 's/requirements-cpow-api\.txt/requirements-api.txt/g' "$ROOT/README_CPOW.md" > "$DEST/README.md"
else
  cp "$ROOT/README.md" "$DEST/README.md"
fi

echo "==> AGENTS.md"
cat > "$DEST/AGENTS.md" <<'EOF'
# AGENTS.md — CPoW World

**Not a game.** Data-creation autonomous simulation (CPoW). See `docs/CPOW_ARCHITECTURE.md`.

**Canonical repo:** https://github.com/weed97/cpow_world

## Layout

| Path | Role |
|------|------|
| `cpow_engine/` | Physics, CPoW, areas, governance, `world/` (biomes, mining) |
| `cpow_api/` | FastAPI — `/v1/areas/*`, `/v1/world/*`, auth |
| `cpow_client/unity/` | **Unity 2022.3+** 3D client — chunk streaming |
| `cpow_client/godot/` | Legacy Godot prototype |

## Commands

```bash
pip install -r requirements-api.txt
python3 -m cpow_engine.demo --areas
uvicorn cpow_api.server:app --host 127.0.0.1 --port 8765
bash scripts/verify.sh
```

Unity: open `cpow_client/unity/CPoWWorld` (API server required).
EOF

echo "==> .gitignore"
cat > "$DEST/.gitignore" <<'EOF'
__pycache__/
*.py[cod]
*.egg-info/
.venv/
venv/
.pytest_cache/
.mypy_cache/
*.log

# Godot
.godot/
.import/
export.cfg
export_presets.cfg

# Unity
[Ll]ibrary/
[Tt]emp/
[Oo]bj/
[Bb]uild/
[Bb]uilds/
[Ll]ogs/
[Uu]ser[Ss]ettings/
*.csproj
*.sln
EOF

echo "==> CI workflow"
cat > "$DEST/.github/workflows/test.yml" <<'EOF'
name: Tests

on:
  push:
    branches: ["**"]
  pull_request:

jobs:
  cpow-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - name: Install API dependencies
        run: pip install -r requirements-api.txt
      - name: Run verify
        run: bash scripts/verify.sh
EOF

echo "==> Clean caches"
find "$DEST" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
find "$DEST" -type d -name '.pytest_cache' -prune -exec rm -rf {} + 2>/dev/null || true

echo "==> Export ready: $DEST"
find "$DEST" -maxdepth 2 -type d | sort
