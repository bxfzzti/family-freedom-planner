import copy
import importlib.util
import unittest
from pathlib import Path

PATH = Path(__file__).resolve().parents[1] / "scripts" / "evaluate_dialogues.py"
SPEC = importlib.util.spec_from_file_location("dialogue_eval", PATH)
E = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(E)


class DialogueEvaluationTests(unittest.TestCase):
    def setUp(self):
        self.suite = {"cases": [{"id": "one", "user_turns": ["年收入50万"],
                                "criteria": {"meaning": "不自动推断税后"}}]}
        self.runs = {"run": {"model": "unit-test-fixture", "skill_revision": "test",
                             "recorded_at": "2026-09-08", "origin": "self_review"},
                     "cases": [{"id": "one", "turns": [
                         {"user": "年收入50万", "assistant": "50万是税前还是税后？"}]}]}
        self.review = {"cases": [{"id": "one", "reviewer": "test-fixture",
                                 "transcript_sha256": E.digest(self.runs["cases"][0]["turns"]),
                                 "case_sha256": E.digest(self.suite["cases"][0]),
                                 "checks": {"meaning": {
                                     "verdict": "PASS", "turn": 0,
                                     "evidence": "税前还是税后",
                                     "reason": "明确要求确认税收口径"}}}]}

    def status(self):
        return E.evaluate(self.suite, self.runs, self.review)["status"]

    def test_complete_review(self):
        self.assertEqual(self.status(), "PASS")

    def test_empty_recording_is_not_pass(self):
        self.runs["cases"] = []
        self.assertEqual(self.status(), "INCOMPLETE")

    def test_unreviewed_is_not_pass(self):
        self.review["cases"] = []
        self.assertEqual(self.status(), "INCOMPLETE")

    def test_changed_answer_invalidates_review(self):
        self.runs["cases"][0]["turns"][0]["assistant"] += "可以直接买房。"
        self.assertEqual(self.status(), "INCOMPLETE")

    def test_changed_criterion_invalidates_review(self):
        self.suite["cases"][0]["criteria"]["meaning"] = "也要区分收入主体"
        self.assertEqual(self.status(), "INCOMPLETE")

    def test_fabricated_quote_is_not_evidence(self):
        self.review["cases"][0]["checks"]["meaning"]["evidence"] = "不存在的句子"
        self.assertEqual(self.status(), "INCOMPLETE")

    def test_fail_is_reported(self):
        self.review["cases"][0]["checks"]["meaning"]["verdict"] = "FAIL"
        self.assertEqual(self.status(), "FAIL")

    def test_duplicate_ids_rejected(self):
        self.runs["cases"].append(copy.deepcopy(self.runs["cases"][0]))
        with self.assertRaises(ValueError):
            self.status()

    def test_unknown_criterion_rejected(self):
        self.review["cases"][0]["checks"]["invented"] = {}
        with self.assertRaises(ValueError):
            self.status()

    def test_wrong_user_turn_is_incomplete(self):
        self.runs["cases"][0]["turns"][0]["user"] = "不同的测试"
        self.assertEqual(self.status(), "INCOMPLETE")

    def test_empty_suite_rejected(self):
        with self.assertRaises(ValueError):
            E.evaluate({"cases": []}, {"cases": []}, {"cases": []})

    def test_missing_provenance_is_incomplete(self):
        self.runs["run"].pop("skill_revision")
        self.assertEqual(self.status(), "INCOMPLETE")

    def test_unknown_origin_is_incomplete(self):
        self.runs["run"]["origin"] = "fabricated"
        self.assertEqual(self.status(), "INCOMPLETE")


if __name__ == "__main__":
    unittest.main()
