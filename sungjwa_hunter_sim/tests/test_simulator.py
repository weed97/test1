"""성좌 헌터 시뮬레이터 핵심 로직 단위 테스트.

표준 라이브러리 unittest 만 사용한다.
    python -m unittest discover -s tests -v
또는
    python tests/test_simulator.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.external_update import ExternalUpdateHandler  # noqa: E402
from src.rng import ChaosRNG  # noqa: E402
from src.simulator import Simulator  # noqa: E402
from src.variables import UNPREDICTABLE_KEYS, VariableManager  # noqa: E402

CONFIG = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "variables.json")


def fresh_config() -> str:
    """원본을 건드리지 않도록 임시 복사본 경로를 만든다."""
    with open(CONFIG, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
    json.dump(data, tmp, ensure_ascii=False, indent=2)
    tmp.close()
    return tmp.name


class TestVariables(unittest.TestCase):
    def setUp(self):
        self.path = fresh_config()
        self.vars = VariableManager(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_eight_unpredictable_vars(self):
        self.assertEqual(len(UNPREDICTABLE_KEYS), 8)
        uv = self.vars.uvars()
        self.assertEqual(len(uv), 8)
        self.assertAlmostEqual(uv["randomness_intensity"], 1.8)

    def test_set_uvar_clamped(self):
        self.assertEqual(self.vars.set_uvar("randomness_intensity", 999), 5.0)  # max
        self.assertEqual(self.vars.set_uvar("randomness_intensity", -5), 0.0)   # min

    def test_set_path_shortname_routes_to_uvar(self):
        self.vars.set_path("luck_factor", "2.5")
        self.assertAlmostEqual(self.vars.uvar("luck_factor"), 2.5)

    def test_set_path_nested_type_preserved(self):
        self.vars.set_path("hunter.hp", "55")
        self.assertEqual(self.vars.get_path("hunter.hp"), 55)
        self.assertIsInstance(self.vars.get_path("hunter.hp"), int)


class TestExternalUpdate(unittest.TestCase):
    def setUp(self):
        self.path = fresh_config()
        self.vars = VariableManager(self.path)
        self.handler = ExternalUpdateHandler(self.vars, persist=True)

    def tearDown(self):
        os.unlink(self.path)

    def test_is_query(self):
        self.assertTrue(self.handler.is_query("[외부 업데이트] 질의: luck_factor=2.0"))
        self.assertFalse(self.handler.is_query("그냥 텍스트"))

    def test_single_assignment(self):
        resp = self.handler.handle("[외부 업데이트] 질의: randomness_intensity=2.4")
        self.assertIn("응답", resp)
        self.assertAlmostEqual(self.vars.uvar("randomness_intensity"), 2.4)

    def test_multi_assignment_persists(self):
        self.handler.handle("[외부 업데이트] 질의: luck_factor=1.7, chaos_resonance=1.2")
        # 파일에 저장되었는지 재로드로 확인
        reloaded = VariableManager(self.path)
        self.assertAlmostEqual(reloaded.uvar("luck_factor"), 1.7)
        self.assertAlmostEqual(reloaded.uvar("chaos_resonance"), 1.2)

    def test_status_query(self):
        resp = self.handler.handle("[외부 업데이트] 질의: 상태")
        for key in UNPREDICTABLE_KEYS:
            self.assertIn(key, resp)

    def test_invalid_key_reports_error(self):
        resp = self.handler.handle("[외부 업데이트] 질의: 없는키=3")
        self.assertIn("오류", resp)


class TestSimulation(unittest.TestCase):
    def setUp(self):
        self.path = fresh_config()
        self.vars = VariableManager(self.path)

    def tearDown(self):
        os.unlink(self.path)

    def test_run_completes_and_is_deterministic(self):
        captured = []
        sim = Simulator(self.vars, seed=123, output=captured.append)
        state = sim.run(max_turns=6)
        self.assertTrue(state.finished)
        self.assertGreaterEqual(state.turn, 1)
        self.assertTrue(len(state.log) >= 1)

        # 동일 시드 → 동일 결과 (재현성)
        vars2 = VariableManager(fresh_config_path := fresh_config())
        try:
            sim2 = Simulator(vars2, seed=123, output=lambda s: None)
            state2 = sim2.run(max_turns=6)
            self.assertEqual(state.turn, state2.turn)
            self.assertEqual(len(state.log), len(state2.log))
            self.assertEqual(state.outcome, state2.outcome)
        finally:
            os.unlink(fresh_config_path)

    def test_high_randomness_changes_outcome_distribution(self):
        # 변수가 결과에 실제 영향을 주는지 (값 변경 시 로그가 달라짐) 확인
        sim_a = Simulator(self.vars, seed=7, output=lambda s: None)
        state_a = sim_a.run(max_turns=8)

        path_b = fresh_config()
        try:
            vars_b = VariableManager(path_b)
            vars_b.set_uvar("randomness_intensity", 4.5)
            vars_b.set_uvar("crisis_escalation", 2.8)
            sim_b = Simulator(vars_b, seed=7, output=lambda s: None)
            state_b = sim_b.run(max_turns=8)
            descriptions_a = [e.description for e in state_a.log]
            descriptions_b = [e.description for e in state_b.log]
            self.assertNotEqual(descriptions_a, descriptions_b)
        finally:
            os.unlink(path_b)

    def test_rng_roll_bounds(self):
        rng = ChaosRNG(self.vars, seed=1)
        for _ in range(50):
            self.assertIn(rng.roll(0.5), (True, False))
            self.assertIn(rng.mutates(), (True, False))
            self.assertIn(rng.chains(), (True, False))


if __name__ == "__main__":
    unittest.main(verbosity=2)
