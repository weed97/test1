"""CPoW areas + auth — Godot client contract & security smoke tests."""

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


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@unittest.skipIf(not _HAS_API, "fastapi not installed")
class TestCpowGodotClientFlow(unittest.TestCase):
    """areas_client.gd 와 동일한 HTTP 시퀀스."""

    def setUp(self) -> None:
        self.client = TestClient(app)  # type: ignore[arg-type]
        self.user = "godot_flow_player"

    def test_health_list_found_join_create_state(self) -> None:
        health = self.client.get("/v1/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json().get("status"), "ok")

        listing = self.client.get("/v1/areas/list")
        self.assertEqual(listing.status_code, 200)
        self.assertTrue(listing.json().get("ok"))

        found = self.client.post(
            "/v1/areas/found",
            json={
                "founder_id": self.user,
                "label": "Godot 테스트 월드",
                "mode": "creation_adventure",
            },
        )
        self.assertEqual(found.status_code, 200)
        body = found.json()
        self.assertTrue(body.get("ok"), body)
        area_id = body["area"]["area_id"]

        joined = self.client.post(
            "/v1/areas/join",
            json={"area_id": area_id, "creator_id": "ally_bot"},
        )
        self.assertTrue(joined.json().get("ok"), joined.json())

        created = self.client.post(
            "/v1/areas/create",
            json={
                "area_id": area_id,
                "creator_id": self.user,
                "type": "heat",
                "label": "열원",
                "heat_intensity": 80.0,
            },
        )
        self.assertEqual(created.status_code, 200, created.json())
        self.assertTrue(created.json().get("ok"), created.json())

        state = self.client.get(f"/v1/areas/state?area_id={area_id}")
        self.assertEqual(state.status_code, 200)
        self.assertTrue(state.json().get("ok"))
        self.assertIn("state", state.json())

    def test_empty_object_field_ignored(self) -> None:
        """Pydantic 기본 object:{} — heat 분기로 폴백."""
        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "pyd_u", "label": "Pydantic"},
        )
        area_id = found.json()["area"]["area_id"]
        r = self.client.post(
            "/v1/areas/create",
            json={
                "area_id": area_id,
                "creator_id": "pyd_u",
                "type": "heat",
                "label": "열원",
                "object": {},
                "intent": {},
            },
        )
        self.assertEqual(r.status_code, 200, r.json())
        self.assertNotIn("detail", r.json())

    def test_visual_object_payload_like_godot(self) -> None:
        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "visual_u", "label": "비주얼"},
        )
        area_id = found.json()["area"]["area_id"]
        created = self.client.post(
            "/v1/areas/create",
            json={
                "area_id": area_id,
                "creator_id": "visual_u",
                "object": {
                    "creator_id": "visual_u",
                    "label": "prop",
                    "properties": [
                        {"name": "heat_intensity", "value": 40.0, "unit": "joules_per_tick"},
                    ],
                    "visual": {"glb_url": "res://x.glb", "slot": "world_prop"},
                },
            },
        )
        self.assertEqual(created.status_code, 200, created.json())
        self.assertNotIn("detail", created.json())


@unittest.skipIf(not _HAS_API, "fastapi not installed")
class TestCpowAuthFlow(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)  # type: ignore[arg-type]

    def test_register_login_me_identity(self) -> None:
        reg = self.client.post(
            "/v1/auth/register",
            json={"user_id": "sec_alice", "password": "password123"},
        )
        self.assertEqual(reg.status_code, 200)
        self.assertTrue(reg.json().get("ok"))
        token = reg.json()["token"]

        me = self.client.get("/v1/auth/me", headers=_auth_headers(token))
        self.assertEqual(me.status_code, 200)
        self.assertEqual(me.json()["user_id"], "sec_alice")

        ident = self.client.post(
            "/v1/identity/register",
            json={"person_key": "person_secret_alice_1234"},
            headers=_auth_headers(token),
        )
        self.assertTrue(ident.json().get("ok"), ident.json())

        status = self.client.get("/v1/identity/status?user_id=sec_alice")
        self.assertTrue(status.json().get("verified"))


@unittest.skipIf(not _HAS_API, "fastapi not installed")
class TestCpowApiSecurity(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)  # type: ignore[arg-type]

    def test_identity_register_requires_bearer(self) -> None:
        r = self.client.post(
            "/v1/identity/register",
            json={"person_key": "x" * 12},
        )
        self.assertEqual(r.status_code, 401)

    def test_bearer_binds_founder_id(self) -> None:
        reg = self.client.post(
            "/v1/auth/register",
            json={"user_id": "bound_user", "password": "password123"},
        )
        token = reg.json()["token"]
        r = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "imposter", "label": "스푸핑"},
            headers=_auth_headers(token),
        )
        self.assertEqual(r.status_code, 403)

    def test_session_overrides_anonymous_actor(self) -> None:
        reg = self.client.post(
            "/v1/auth/register",
            json={"user_id": "real_actor", "password": "password123"},
        )
        token = reg.json()["token"]
        found = self.client.post(
            "/v1/areas/found",
            json={"label": "세션 월드"},
            headers=_auth_headers(token),
        )
        self.assertTrue(found.json().get("ok"))
        self.assertEqual(found.json()["area"]["founder_id"], "real_actor")

    def test_invalid_token_rejected(self) -> None:
        r = self.client.get(
            "/v1/auth/me",
            headers={"Authorization": "Bearer not.a.valid.token"},
        )
        self.assertEqual(r.status_code, 401)

    def test_unauthenticated_mutate_still_allowed(self) -> None:
        """P0: optional auth — anonymous actor_id still accepted without Bearer."""
        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "anon_u", "label": "익명"},
        )
        self.assertTrue(found.json().get("ok"))
        self.assertEqual(found.json()["area"]["founder_id"], "anon_u")


if __name__ == "__main__":
    unittest.main()
