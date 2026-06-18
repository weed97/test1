#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "==> Eldoria (fantasy_simulator)"
bash "$ROOT/fantasy_simulator/scripts/verify.sh"
echo "==> CPoW engine"
python3 -m unittest discover -s cpow_engine/tests -q
echo "==> Monorepo Python sims"
python3 -m unittest \
  tests.test_mmorpg_sim_engine \
  tests.test_dialogue \
  fantasy_mmorpg.tests.test_engine \
  sungjwa_hunter_sim.tests.test_simulator \
  sungjwa_hunter_sim.tests.test_units \
  -q
echo "==> JS medieval sim"
(cd "$ROOT/js_medieval_sim" && npm test)
echo "==> All monorepo checks passed"
