"""CPoW areas + auth — Godot client contract & security smoke tests."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    from fastapi.testclient import TestClient
    from cpow_api.server import app

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
class TestCpowWorldApiFlow(unittest.TestCase):
    """오픈월드 — 바이옴·채굴·건축 API 스모크."""

    def setUp(self) -> None:
        self.client = TestClient(app)  # type: ignore[arg-type]

    def test_world_catalog_and_cell(self) -> None:
        catalog = self.client.get("/v1/world/catalog")
        self.assertEqual(catalog.status_code, 200)
        body = catalog.json()
        self.assertTrue(body.get("ok"))
        self.assertIn("biomes", body)
        self.assertIn("ores", body)

        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "world_u", "label": "월드 테스트"},
        )
        area_id = found.json()["area"]["area_id"]

        cell = self.client.post(
            "/v1/world/cell",
            json={"area_id": area_id, "x": 64.0, "z": -32.0, "advance_tick": True},
        )
        self.assertEqual(cell.status_code, 200, cell.json())
        self.assertTrue(cell.json().get("ok"), cell.json())
        self.assertIn("hazard", cell.json())

    def test_world_mine_and_adventure_mine(self) -> None:
        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "miner_u", "label": "채굴 테스트"},
        )
        area_id = found.json()["area"]["area_id"]

        mined = self.client.post(
            "/v1/world/mine",
            json={
                "area_id": area_id,
                "actor_id": "miner_u",
                "x": 10.0,
                "z": 10.0,
                "depth_y": 40,
                "tool_type": "pickaxe",
                "tool_tier": 2,
                "ore_id": "coal",
            },
        )
        self.assertEqual(mined.status_code, 200, mined.json())
        mined_body = mined.json()
        self.assertTrue(mined_body.get("ok"), mined_body)
        self.assertIn("inventory", mined_body)
        self.assertIn("inventory_delta", mined_body)
        self.assertIn("world_drop", mined_body)
        self.assertNotIn("creation", mined_body)

        inv = self.client.get(
            f"/v1/world/inventory?area_id={area_id}&actor_id=miner_u",
        )
        self.assertTrue(inv.json().get("ok"))
        self.assertGreater(inv.json()["inventory"]["stacks"].get("coal", 0), 0)

        adventure = self.client.post(
            "/v1/areas/adventure",
            json={
                "area_id": area_id,
                "actor_id": "miner_u",
                "action": "mine",
                "x": 10.0,
                "z": 10.0,
                "depth_y": 40,
                "tool_type": "pickaxe",
                "tool_tier": 2,
                "ore_id": "coal",
            },
        )
        self.assertEqual(adventure.status_code, 200, adventure.json())
        self.assertTrue(adventure.json().get("ok"), adventure.json())
        self.assertEqual(adventure.json().get("action"), "mine")
        self.assertIn("inventory", adventure.json())

    def test_world_mine_area_object_mode(self) -> None:
        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "obj_u", "label": "오브젝트 채굴"},
        )
        area_id = found.json()["area"]["area_id"]
        mined = self.client.post(
            "/v1/world/mine",
            json={
                "area_id": area_id,
                "actor_id": "obj_u",
                "x": 10.0,
                "z": 10.0,
                "depth_y": 40,
                "tool_type": "pickaxe",
                "tool_tier": 2,
                "ore_id": "coal",
                "deposit_mode": "both",
                "submit_to_area": True,
            },
        )
        body = mined.json()
        self.assertTrue(body.get("ok"), body)
        self.assertIn("inventory", body)
        self.assertIn("creation", body)
        self.assertTrue(body["creation"].get("ok"), body.get("creation"))

    def test_world_mine_skip_area_submit(self) -> None:
        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "skip_u", "label": "미등록 채굴"},
        )
        area_id = found.json()["area"]["area_id"]
        mined = self.client.post(
            "/v1/world/mine",
            json={
                "area_id": area_id,
                "actor_id": "skip_u",
                "x": 5.0,
                "z": 5.0,
                "depth_y": 40,
                "tool_type": "pickaxe",
                "tool_tier": 2,
                "ore_id": "coal",
                "submit_to_area": False,
            },
        )
        body = mined.json()
        self.assertTrue(body.get("ok"), body)
        self.assertNotIn("creation", body)
        self.assertIn("inventory", body)

    def test_world_build_validate_and_boss_loot(self) -> None:
        build = self.client.post(
            "/v1/world/build/validate",
            json={
                "biome_id": "desert",
                "blueprint_id": "camp_kit",
                "placed_modules": {
                    "foundation_1x1": 1,
                    "wall_t1": 4,
                    "heater_core": 1,
                },
                "placed_materials": {"wood_plank": 8, "stone_brick": 4},
            },
        )
        self.assertEqual(build.status_code, 200, build.json())
        self.assertTrue(build.json().get("ok"), build.json())

        found = self.client.post(
            "/v1/areas/found",
            json={"founder_id": "boss_u", "label": "보스 루트"},
        )
        area_id = found.json()["area"]["area_id"]
        loot = self.client.post(
            "/v1/world/boss_loot",
            json={"area_id": area_id, "actor_id": "boss_u", "amount": 1.0},
        )
        self.assertEqual(loot.status_code, 200, loot.json())
        self.assertTrue(loot.json().get("ok"), loot.json())


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
