"""Ecology RNG — session seed persistence and deterministic ticks."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from api.session_store import SessionStore  # noqa: E402
from tests.fixtures import isolated_game_root  # noqa: E402
from utils.field_agents import ecology_rng, persist_ecology_rng, tick_field_ecology  # noqa: E402
from utils.game_session import GameSession  # noqa: E402


class EcologyRngTests(unittest.TestCase):
    def test_ecology_rng_restores_state(self) -> None:
        state: dict = {"flags": {"ecology": {}}, "meta": {"rng_seed": 42}}
        r1 = ecology_rng(state, None)
        _ = [r1.random() for _ in range(5)]
        persist_ecology_rng(state, r1)
        r2 = ecology_rng(state, None)
        self.assertEqual(r1.random(), r2.random())

    def test_session_store_restores_seed(self) -> None:
        store = SessionStore()
        sid, session = store.create(seed=77, mode="rule", temporal_mode="precision")
        self.assertEqual(session.state["meta"]["rng_seed"], 77)
        store._sessions.pop(sid)
        reloaded = store.get(sid)
        assert reloaded is not None
        self.assertEqual(reloaded.rng.randint(0, 10), session.rng.randint(0, 10))

    def test_tick_field_ecology_persists_rng_state(self) -> None:
        with isolated_game_root() as root:
            session = GameSession.from_root(root, mode="rule", seed=11)
            session.state.setdefault("flags", {})["game_mode"] = "ecology"
            session.state["world"]["map_id"] = "forest_01"
            session.state.setdefault("meta", {})["rng_seed"] = 11
            from utils.field_agents import ensure_ecology_seeds

            ensure_ecology_seeds(session.state, base_dir=root)
            tick_field_ecology(session.state, base_dir=root)
            self.assertIn("rng_state", session.state["flags"]["ecology"])


if __name__ == "__main__":
    unittest.main()
