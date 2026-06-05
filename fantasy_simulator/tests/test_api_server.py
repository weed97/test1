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

    def test_combat_combatant_arthur(self) -> None:
        r = self.client.get("/v1/combat/combatant/npc_arthur_pendragon")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertEqual(body["snapshot"]["tier"], "demigod")
        self.assertGreater(body["combat_power"], 0)

    def test_sovereign_status(self) -> None:
        r = self.client.get("/v1/sovereign/status")
        self.assertEqual(r.status_code, 200)
        self.assertIn("hp_milli", r.json())
