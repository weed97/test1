"""Simulation API — Godot client contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from fastapi.testclient import TestClient
    from api.server import app

    _HAS_API = True
except ImportError:
    _HAS_API = False
    TestClient = None  # type: ignore[misc, assignment]
    app = None  # type: ignore[assignment]


@unittest.skipIf(not _HAS_API, "fastapi not installed")
class ApiServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)  # type: ignore[arg-type]

    def test_health(self) -> None:
        r = self.client.get("/v1/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["api_version"], 1)

    def test_arthur_skill_endpoint(self) -> None:
        r = self.client.post(
            "/v1/combat/arthur_skill",
            json={
                "skill_id": "sovereign_blade_combo",
                "target_presets": ["world_rank_02"],
            },
        )
        self.assertEqual(r.status_code, 200)
        body = r.json().get("arthur_skill", {})
        self.assertEqual(body.get("skill_id"), "sovereign_blade_combo")
        self.assertIn("pipeline", body)

    def test_combat_combatant_arthur(self) -> None:
        r = self.client.get("/v1/combat/combatant/npc_arthur_pendragon")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["snapshot"]["tier"], "demigod")
        self.assertGreater(body["combat_power"], 0)

    def test_sovereign_status(self) -> None:
        r = self.client.get("/v1/sovereign/status")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertIn("hp_milli", body)
        self.assertIn("wish", body)

    def test_hybrid_session_skill_tree(self) -> None:
        created = self.client.post(
            "/v1/session/new",
            json={"game_mode": "hybrid", "temporal_mode": "precision"},
        )
        self.assertEqual(created.status_code, 200)
        sid = created.json()["session_id"]
        status = self.client.get(f"/v1/progression/status?session_id={sid}")
        self.assertEqual(status.status_code, 200)
        heroes = status.json().get("heroes", {})
        cid = next(iter(heroes), "gareth_ironshield")
        tree = self.client.get(
            f"/v1/progression/skill_tree?session_id={sid}&character_id={cid}"
        )
        self.assertEqual(tree.status_code, 200)
        payload = tree.json().get("skill_tree", {})
        self.assertEqual(payload.get("counts", {}).get("job_total"), 300)

    def test_sovereign_wish_empower_kingdom(self) -> None:
        created = self.client.post(
            "/v1/session/new",
            json={"game_mode": "hybrid"},
        )
        sid = created.json()["session_id"]
        r = self.client.post(
            "/v1/sovereign/wish",
            json={
                "session_id": sid,
                "edict_type": "empower_kingdom",
                "civilization_id": "ashpoint_commons",
                "prosperity_gain": 10,
            },
        )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json().get("ok"))

    def test_hybrid_turn_and_position(self) -> None:
        created = self.client.post(
            "/v1/session/new",
            json={"game_mode": "hybrid", "seed": 99, "temporal_mode": "precision"},
        )
        self.assertEqual(created.status_code, 200)
        sid = created.json()["session_id"]
        turn = self.client.post(
            "/v1/turn",
            json={"session_id": sid, "action": "explore", "temporal_mode": "precision"},
        )
        self.assertEqual(turn.status_code, 200)
        self.assertIn("lines", turn.json())
        pos = self.client.post(
            "/v1/world/position",
            json={
                "session_id": sid,
                "position": {
                    "map_id": "ashpoint_01",
                    "x": 41,
                    "y": 48,
                    "facing": "south",
                },
            },
        )
        self.assertEqual(pos.status_code, 200)
        self.assertTrue(pos.json().get("ok", True))
        agents = self.client.get(f"/v1/world/agents?session_id={sid}&map_id=ashpoint_01")
        self.assertEqual(agents.status_code, 200)
        self.assertIn("agents", agents.json())
