import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROUTER = ROOT / "scripts" / "intake_router.py"

spec = importlib.util.spec_from_file_location("router", ROUTER)
router = importlib.util.module_from_spec(spec)
spec.loader.exec_module(router)


class IntakeRouterTests(unittest.TestCase):
    def test_housing_career(self):
        result = router.route("我38岁，两个孩子，想换房，但是担心40岁以后工作不稳")
        self.assertIn("HOUSING_EXISTING", result["selected_topics"])
        self.assertIn("CAREER", result["selected_topics"])

    def test_first_buy(self):
        result = router.route("我们还没买房，手里120万，想看看首套可以买多贵")
        self.assertIn("HOUSING_FIRST_BUY", result["selected_topics"])
        self.assertNotIn("HOUSING_EXISTING", result["selected_topics"])

    def test_spouse_break(self):
        result = router.route("老婆明年可能不上班在家带孩子，我们家会不会压力大")
        self.assertIn("SPOUSE_BREAK", result["selected_topics"])

    def test_max_three(self):
        result = router.route("想换学区房，老婆可能脱产，我也想40岁离职，还担心抵押贷续贷", max_topics=3)
        self.assertLessEqual(len(result["selected_topics"]), 3)

    def test_general(self):
        result = router.route("帮我看看我们家未来几年整体安全吗")
        self.assertEqual(result["selected_topics"], ["GENERAL"])

    def test_age_alone_is_not_career_risk(self):
        result = router.route("我35岁，想安排父母养老")
        self.assertNotIn("CAREER", result["selected_topics"])

    def test_first_home_school_district(self):
        result = router.route("我们没有房，准备买首套学区房")
        self.assertIn("HOUSING_FIRST_BUY", result["selected_topics"])
        self.assertIn("EDUCATION", result["selected_topics"])
        self.assertNotIn("HOUSING_EXISTING", result["selected_topics"])

    def test_previous_no_home_does_not_override_current_home(self):
        result = router.route("以前没有房，现在已有房，想换学区房")
        self.assertIn("HOUSING_EXISTING", result["selected_topics"])

    def test_invalid_budget(self):
        for limit in (0, -1, 4, 1.5, True):
            with self.subTest(limit=limit), self.assertRaises(ValueError):
                router.route("想换房", limit)


if __name__ == "__main__":
    unittest.main()
