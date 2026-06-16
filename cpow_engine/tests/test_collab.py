"""Collaborative open world tests."""

import unittest

from cpow_engine.collab import CollaborativeWorld, load_collab_policy
from cpow_engine.collab.policy import CollabPolicy
from cpow_engine.physics import create_heat_object


def _instant_policy(**kwargs: object) -> CollabPolicy:
    """펄스 없이 즉시 반영 — 기존 단위 테스트용."""
    return CollabPolicy(pulse_interval_sec=0.0, min_creator_cooldown_sec=0.0, **kwargs)


class TestCollabPolicy(unittest.TestCase):
    def test_load_policy(self) -> None:
        p = load_collab_policy()
        self.assertLessEqual(p.max_relative_change, 0.5)
        self.assertGreater(p.damp_factor, 0.0)
        self.assertGreater(p.pulse_interval_sec, 0.0)

    def test_effective_damp_increases_with_magnitude(self) -> None:
        p = CollabPolicy(damp_factor=0.4, noise_threshold=0.6)
        low = p.effective_damp(0.3)
        high = p.effective_damp(0.9)
        self.assertGreater(low, high)


class TestNoiseGate(unittest.TestCase):
    def test_extreme_heat_damped_not_raw(self) -> None:
        world = CollaborativeWorld("test", policy=_instant_policy())
        extreme = create_heat_object("u1", "폭발", heat_intensity=500.0)
        result = world.submit_creation("u1", extreme)
        self.assertTrue(result.ok, result.reason)
        obj = world.state.objects[result.object_id]
        heat = obj.get_property("heat_intensity")
        assert heat is not None
        self.assertLess(heat.value, 500.0)
        self.assertIn("damped", result.reason)

    def test_small_change_mostly_accepted(self) -> None:
        world = CollaborativeWorld("test", policy=_instant_policy())
        mild = create_heat_object("u1", "작은 불", heat_intensity=55.0)
        r1 = world.submit_creation("u1", mild)
        self.assertTrue(r1.ok)
        mild2 = create_heat_object("u1", "작은 불", heat_intensity=60.0)
        mild2.id = r1.object_id
        r2 = world.submit_creation("u1", mild2)
        self.assertTrue(r2.ok)
        if r2.verdict:
            self.assertLess(r2.verdict.magnitude, 1.5)


class TestCollaborativeWorld(unittest.TestCase):
    def test_multi_creator_open_world(self) -> None:
        world = CollaborativeWorld("open_alpha", policy=_instant_policy())
        for i, cid in enumerate(["alice", "bob", "carol"]):
            obj = create_heat_object(cid, f"열원{i}", 70.0 + i * 5)
            r = world.submit_creation(cid, obj)
            self.assertTrue(r.ok, r.reason)

        self.assertEqual(len(world.state.objects), 3)
        pub = world.to_public_dict()
        self.assertEqual(pub["object_count"], 3)
        self.assertIn("alice", pub["contributors"])

    def test_pulse_queue_cap(self) -> None:
        policy = CollabPolicy(
            pulse_interval_sec=8.0,
            min_creator_cooldown_sec=0.0,
            max_creations_per_creator_per_pulse=3,
            max_creations_per_tick=2,
        )
        world = CollaborativeWorld("cap_test", policy=policy, now=0.0)
        for i in range(3):
            obj = create_heat_object(f"u{i}", f"o{i}", 50.0 + i)
            r = world.submit_creation(f"u{i}", obj)
        self.assertFalse(r.ok)
        pulse = world.advance_pulse(force=True)
        self.assertEqual(pulse.applied_count, 2)
        self.assertEqual(len(world.state.objects), 2)

    def test_noise_level_tracks_activity(self) -> None:
        world = CollaborativeWorld("noise", policy=_instant_policy())
        world.submit_creation("u1", create_heat_object("u1", "big", 400.0))
        self.assertGreater(world.world_noise_level(), 0.0)


class TestBuildPulse(unittest.TestCase):
    def test_queue_then_commit_together(self) -> None:
        policy = CollabPolicy(
            pulse_interval_sec=8.0,
            min_creator_cooldown_sec=0.0,
            max_creations_per_creator_per_pulse=1,
        )
        world = CollaborativeWorld("pulse", policy=policy, now=0.0)

        r1 = world.submit_creation("alice", create_heat_object("alice", "불1", 60.0))
        r2 = world.submit_creation("bob", create_heat_object("bob", "불2", 70.0))

        self.assertTrue(r1.queued)
        self.assertTrue(r2.queued)
        self.assertEqual(len(world.state.objects), 0)
        self.assertEqual(world.to_public_dict()["pending_count"], 2)

        pulse = world.advance_pulse(force=True)
        self.assertTrue(pulse.advanced)
        self.assertEqual(pulse.applied_count, 2)
        self.assertEqual(len(world.state.objects), 2)

    def test_creator_cooldown_blocks_spam(self) -> None:
        policy = CollabPolicy(
            pulse_interval_sec=8.0,
            min_creator_cooldown_sec=5.0,
            max_creations_per_creator_per_pulse=2,
        )
        world = CollaborativeWorld("cooldown", policy=policy, now=0.0)

        r1 = world.submit_creation("alice", create_heat_object("alice", "a1", 50.0))
        self.assertTrue(r1.ok)

        world.set_time(2.0)
        r2 = world.submit_creation("alice", create_heat_object("alice", "a2", 55.0))
        self.assertFalse(r2.ok)
        self.assertEqual(r2.reason, "creator_cooldown")
        self.assertGreater(r2.cooldown_remaining, 0.0)

    def test_one_creation_per_creator_per_pulse(self) -> None:
        policy = CollabPolicy(
            pulse_interval_sec=8.0,
            min_creator_cooldown_sec=0.0,
            max_creations_per_creator_per_pulse=1,
        )
        world = CollaborativeWorld("one_each", policy=policy, now=0.0)

        world.submit_creation("alice", create_heat_object("alice", "a1", 50.0))
        r2 = world.submit_creation("alice", create_heat_object("alice", "a2", 55.0))
        self.assertFalse(r2.ok)
        self.assertEqual(r2.reason, "creator_pulse_limit_reached")

    def test_auto_pulse_when_interval_elapsed(self) -> None:
        policy = CollabPolicy(pulse_interval_sec=5.0, min_creator_cooldown_sec=0.0)
        world = CollaborativeWorld("auto", policy=policy, now=0.0)
        world.submit_creation("alice", create_heat_object("alice", "불", 60.0))

        not_yet = world.maybe_advance_pulse(now=3.0)
        self.assertFalse(not_yet.advanced)

        done = world.maybe_advance_pulse(now=5.0)
        self.assertTrue(done.advanced)
        self.assertEqual(len(world.state.objects), 1)


if __name__ == "__main__":
    unittest.main()
