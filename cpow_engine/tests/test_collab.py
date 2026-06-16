"""Collaborative open world tests."""

import unittest

from cpow_engine.collab import CollaborativeWorld, load_collab_policy
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object


class TestCollabPolicy(unittest.TestCase):
    def test_load_policy(self) -> None:
        p = load_collab_policy()
        self.assertLessEqual(p.max_relative_change, 0.5)
        self.assertGreater(p.damp_factor, 0.0)

    def test_effective_damp_increases_with_magnitude(self) -> None:
        p = CollabPolicy(damp_factor=0.4, noise_threshold=0.6)
        low = p.effective_damp(0.3)
        high = p.effective_damp(0.9)
        self.assertGreater(low, high)


class TestNoiseGate(unittest.TestCase):
    def test_extreme_heat_damped_not_raw(self) -> None:
        world = CollaborativeWorld("test")
        extreme = create_heat_object("u1", "폭발", heat_intensity=500.0)
        result = world.submit_creation("u1", extreme)
        world.advance_tick()
        self.assertTrue(result.ok, result.reason)
        obj = world.state.objects[result.object_id]
        heat = obj.get_property("heat_intensity")
        assert heat is not None
        self.assertLess(heat.value, 500.0)
        self.assertIn("damped", result.reason)

    def test_small_change_mostly_accepted(self) -> None:
        world = CollaborativeWorld("test")
        mild = create_heat_object("u1", "작은 불", heat_intensity=55.0)
        r1 = world.submit_creation("u1", mild)
        self.assertTrue(r1.ok)
        mild2 = create_heat_object("u1", "작은 불", heat_intensity=60.0)
        mild2.id = r1.object_id
        r2 = world.submit_creation("u1", mild2)
        world.advance_tick()
        self.assertTrue(r2.ok)
        if r2.verdict:
            self.assertLess(r2.verdict.magnitude, 1.5)


class TestCollaborativeWorld(unittest.TestCase):
    def test_multi_creator_open_world(self) -> None:
        world = CollaborativeWorld("open_alpha")
        for i, cid in enumerate(["alice", "bob", "carol"]):
            obj = create_heat_object(cid, f"열원{i}", 70.0 + i * 5)
            r = world.submit_creation(cid, obj)
            self.assertTrue(r.ok, r.reason)
        world.advance_tick()

        self.assertEqual(len(world.state.objects), 3)
        pub = world.to_public_dict()
        self.assertEqual(pub["object_count"], 3)
        self.assertIn("alice", pub["contributors"])

    def test_tick_creation_cap(self) -> None:
        policy = CollabPolicy(max_creations_per_tick=2)
        world = CollaborativeWorld("cap_test", policy=policy)
        for i in range(3):
            obj = create_heat_object("u1", f"o{i}", 50.0 + i)
            r = world.submit_creation("u1", obj)
        self.assertFalse(r.ok)
        self.assertEqual(len(world.state.objects), 2)

    def test_noise_level_tracks_activity(self) -> None:
        world = CollaborativeWorld("noise")
        world.submit_creation("u1", create_heat_object("u1", "big", 400.0))
        self.assertGreater(world.world_noise_level(), 0.0)


if __name__ == "__main__":
    unittest.main()
