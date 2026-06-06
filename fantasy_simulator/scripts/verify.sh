#!/usr/bin/env bash
# Full verification — run before opening Godot or merging PR.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Python unit tests (265+)"
pip install -q -r requirements-api.txt
python3 -m unittest discover -s tests -q

echo "==> API smoke (Arthur 5 skills + progression)"
python3 <<'PY'
from fastapi.testclient import TestClient
from api.server import app

c = TestClient(app)
r = c.post("/v1/session/new", json={"game_mode": "hybrid", "seed": 1})
assert r.status_code == 200, r.text
sid = r.json()["session_id"]
st = c.get(f"/v1/progression/status?session_id={sid}")
assert st.status_code == 200
heroes = st.json().get("heroes", {})
assert heroes, "heroes empty — init_heroes_from_party failed"
cid = next(iter(heroes))
tr = c.get(f"/v1/progression/skill_tree?session_id={sid}&character_id={cid}")
assert tr.status_code == 200
assert tr.json()["skill_tree"]["counts"]["job_total"] == 300
for sk in (
    "sovereign_blade_combo",
    "kings_aegis",
    "excalibur_sovereign_judgment",
    "sovereign_wish_rite",
):
    ar = c.post("/v1/combat/arthur_skill", json={"skill_id": sk})
    assert ar.status_code == 200, ar.text
print("API smoke OK")
PY

echo "==> All checks passed"
