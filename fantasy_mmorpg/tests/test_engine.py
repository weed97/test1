from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from fantasy_mmorpg.engine import GameEngine


class GameEngineTest(unittest.TestCase):
    def test_look_and_dialogue_expose_world_content(self) -> None:
        engine = GameEngine(GameEngine.create_player("Lyra", "mage"), seed=1)

        look = engine.handle("look")
        self.assertIn("Eldermist Village", look)
        self.assertIn("Mira", look)

        talk = engine.handle("talk mira")
        self.assertIn("Available quests", talk)
        self.assertIn("Rats in the Cellar", talk)

        ask = engine.handle("ask mira about rumors")
        self.assertIn("Barrow Road", ask)

    def test_gather_and_complete_healer_quest(self) -> None:
        engine = GameEngine(GameEngine.create_player("Rowan", "ranger"), seed=2)

        self.assertIn("Quest accepted", engine.handle("accept herbs"))
        engine.handle("go north")
        engine.handle("gather moonleaf")
        engine.handle("gather moonleaf")
        engine.handle("gather moonleaf")
        engine.handle("go north")
        engine.handle("gather marshroot")
        engine.handle("go south")
        engine.handle("go south")

        result = engine.handle("complete herbs")
        self.assertIn("Quest complete", result)
        self.assertIn("Silver Chapel reputation", result)
        self.assertIn("herbs_for_the_healer", engine.player.completed_quests)

    def test_cellar_rat_combat_updates_quest_progress(self) -> None:
        engine = GameEngine(GameEngine.create_player("Bran", "knight"), seed=3)

        engine.handle("accept rats")
        for _ in range(3):
            start = engine.handle("fight")
            self.assertIn("Cellar Rat", start)
            guard = 0
            while engine.active_enemy is not None:
                engine.handle("attack")
                guard += 1
                self.assertLess(guard, 10)

        quest_text = engine.handle("quests")
        self.assertIn("Rats in the Cellar [ready]", quest_text)
        complete = engine.handle("complete rats")
        self.assertIn("Quest complete", complete)
        self.assertGreaterEqual(engine.player.reputation["Hearthfolk"], 2)

    def test_search_save_and_load_round_trip(self) -> None:
        engine = GameEngine(GameEngine.create_player("Mara", "rogue"), seed=4)
        search = engine.handle("search")
        self.assertIn("village well", search.lower())
        self.assertIn("village_well_cache", engine.player.discoveries)

        with tempfile.TemporaryDirectory() as tmp:
            save_path = Path(tmp) / "save.json"
            self.assertIn("Saved game", engine.save(save_path))
            loaded = GameEngine.load(save_path)

        self.assertEqual(loaded.player.name, "Mara")
        self.assertIn("village_well_cache", loaded.player.discoveries)
        self.assertEqual(loaded.player.inventory, engine.player.inventory)

    def test_shop_and_crafting(self) -> None:
        engine = GameEngine(GameEngine.create_player("Sera", "cleric"), seed=5)
        engine.player.gold = 100

        shop = engine.handle("shop")
        self.assertIn("Healing Draught", shop)
        bought = engine.handle("buy healing")
        self.assertIn("Bought Healing Draught", bought)

        engine.player.add_item("moonleaf", 2)
        engine.player.add_item("travel_ration", 1)
        crafted = engine.handle("craft healing")
        self.assertIn("Crafted Healing Draught", crafted)


if __name__ == "__main__":
    unittest.main()
