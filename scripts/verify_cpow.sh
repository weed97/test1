#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> CPoW engine unit tests"
python3 -m unittest discover -s cpow_engine/tests -q

echo "==> CPoW API smoke tests"
if python3 -c "import fastapi" 2>/dev/null; then
  python3 -m unittest tests.test_cpow_api_flow -q
else
  echo "    (skip: pip install -r requirements-cpow-api.txt)"
fi

echo "==> CPoW compile check"
python3 -m compileall -q cpow_engine cpow_api

echo "==> CPoW checks passed"
