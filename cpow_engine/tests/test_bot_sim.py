"""Bot simulation vulnerability tests."""

import unittest

from cpow_engine.bot_sim import run_bot_simulation


class TestBotSimulation(unittest.TestCase):
    def test_runs_all_scenarios(self) -> None:
        report = run_bot_simulation(steps=15)
        self.assertEqual(len(report.scenarios), 3)
        names = {s.name for s in report.scenarios}
        self.assertIn("macro_clicker", names)
        self.assertIn("fingerprint_spam", names)
        self.assertIn("diversity_farmer", names)

    def test_macro_clicker_high_bot_risk(self) -> None:
        report = run_bot_simulation(steps=20)
        macro = next(s for s in report.scenarios if s.name == "macro_clicker")
        self.assertGreater(macro.avg_bot_risk, 0.5)
        self.assertGreater(macro.flagged_bot_ratio, 0.5)

    def test_fingerprint_spam_low_creativity(self) -> None:
        report = run_bot_simulation(steps=20)
        spam = next(s for s in report.scenarios if s.name == "fingerprint_spam")
        self.assertLess(spam.avg_creativity, 1.0)

    def test_report_has_recommendations(self) -> None:
        report = run_bot_simulation(steps=20)
        self.assertGreater(len(report.recommendations), 0)
        data = report.to_dict()
        self.assertIn("scenarios", data)


if __name__ == "__main__":
    unittest.main()
