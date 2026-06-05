"""Simulation API — Godot client contract."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from fastapi.testclient import TestClient
except ImportError:
    TestClient = None  # type: ignore[misc, assignment]

from api.server import app  # noqa: E402


@unittest.skipIf(TestClient is None, "fastapi not installed")
class ApiServerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)

    def test_health(self) -> None:
        r = self.client.get("/v1/health")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["api_version"], 1)

    def test_new_session_and_explore_turn(self) -> None:
        r = self.client.post(
            "/v1/session/new",
            json={"seed": 42, "mode": "rule", "temporal_mode": "classic"},
        )
        self.assertEqual(r.status_code, 200)
        session_id = r.json()["session_id"]

        r2 = self.client.post(
            "/v1/turn",
            json={"session_id": session_id, "action": "explore"},
        )
        self.assertEqual(r2.status_code, 200)
        data = r2.json()
        self.assertEqual(data["session_id"], session_id)
        self.assertIn("lines", data)
        self.assertIn("world", data)
        self.assertIsNotNone(data["world"].get("tension"))

    def test_precision_turn_includes_clock_fields(self) -> None:
        r = self.client.post(
            "/v1/session/new",
            json={"temporal_mode": "precision"},
        )
        session_id = r.json()["session_id"]
        r2 = self.client.post(
            "/v1/turn",
            json={
                "session_id": session_id,
                "action": "explore",
                "temporal_mode": "precision",
            },
        )
        data = r2.json()
        self.assertIn("minutes_advanced", data)
        self.assertIn("world", data)


if __name__ == "__main__":
    unittest.main()
