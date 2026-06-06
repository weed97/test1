"""Unified item catalog — import, generation, API."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tests.fixtures import isolated_game_root
from utils.game_session import GameSession
from utils.item_catalog import build_catalog_manifest, catalog_counts, get_item_def
from utils.progression import grant_item, init_heroes_from_party, use_item


class ItemCatalogTests(unittest.TestCase):
    def test_catalog_has_many_items(self) -> None:
        counts = catalog_counts(base_dir=ROOT)
        self.assertGreaterEqual(counts["total"], 150)
        self.assertGreaterEqual(counts["by_category"].get("weapon", 0), 30)
        self.assertGreaterEqual(counts["by_category"].get("potion", 0), 8)
        self.assertGreaterEqual(counts["by_category"].get("material", 0), 15)

    def test_imported_potion_parsed(self) -> None:
        pot = get_item_def("minor_heal_potion", base_dir=ROOT)
        self.assertIsNotNone(pot)
        assert pot is not None
        self.assertEqual(pot.get("hp_restore"), 30)
        self.assertTrue(pot.get("consumable"))

    def test_excalibur_renamed_to_avoid_sovereign_conflict(self) -> None:
        folk = get_item_def("folk_legend_blade", base_dir=ROOT)
        self.assertIsNotNone(folk)
        sov = get_item_def("excalibur_sovereign_blade", base_dir=ROOT)
        self.assertIsNotNone(sov)
        self.assertNotEqual(folk.get("grade"), "demigod")

    def test_manifest_filter_category(self) -> None:
        m = build_catalog_manifest(base_dir=ROOT, category="material", limit=50)
        self.assertGreater(m["filtered_count"], 10)
        for it in m["items"]:
            self.assertEqual(it["category"], "material")

    def test_grant_and_use_potion(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=1)
            session.state.setdefault("flags", {})["game_mode"] = "hybrid"
            init_heroes_from_party(session.state, base_dir=root)
            g = grant_item(session.state, "minor_heal_potion", 2, base_dir=root)
            self.assertTrue(g["ok"])
            hero = session.state["flags"]["ecology"]["progression"]["heroes"]["gareth_ironshield"]
            hero["hp"] = 10
            hero["max_hp"] = 100
            used = use_item(session.state, "gareth_ironshield", "minor_heal_potion", base_dir=root)
            self.assertTrue(used["ok"])
            self.assertGreaterEqual(hero["hp"], 40)


try:
    from fastapi.testclient import TestClient
    from api.server import app

    _HAS_API = True
except ImportError:
    _HAS_API = False


@unittest.skipIf(not _HAS_API, "fastapi not installed")
class ItemCatalogApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.client = TestClient(app)  # type: ignore[arg-type]

    def test_catalog_items_endpoint(self) -> None:
        r = self.client.get("/v1/catalog/items?category=weapon&limit=10")
        self.assertEqual(r.status_code, 200)
        body = r.json()
        self.assertGreaterEqual(body["counts"]["total"], 150)
        self.assertLessEqual(len(body["items"]), 10)

    def test_catalog_with_session_inventory(self) -> None:
        created = self.client.post("/v1/session/new", json={"game_mode": "hybrid"})
        sid = created.json()["session_id"]
        self.client.post(
            "/v1/progression/grant_item",
            json={"session_id": sid, "item_id": "minor_heal_potion", "count": 1},
        )
        r = self.client.get(f"/v1/catalog/items?session_id={sid}&category=potion")
        self.assertEqual(r.status_code, 200)
        inv = r.json().get("inventory", {})
        self.assertGreaterEqual(inv.get("consumables", {}).get("minor_heal_potion", 0), 1)


if __name__ == "__main__":
    unittest.main()
