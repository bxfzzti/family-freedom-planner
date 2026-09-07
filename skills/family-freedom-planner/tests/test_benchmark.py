import importlib.util
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "validate_benchmark.py"
BENCHMARK = ROOT / "evals" / "benchmark_cases.json"

spec = importlib.util.spec_from_file_location("validator", SCRIPT)
validator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(validator)

class BenchmarkTests(unittest.TestCase):
    def test_release_gate(self):
        result = validator.validate(BENCHMARK)
        self.assertEqual(result["status"], "PASS", result["errors"])
        self.assertGreaterEqual(result["case_count"], 25)
        self.assertGreaterEqual(result["unique_risk_tags"], 10)
        self.assertGreaterEqual(result["counterfactual_cases"], 5)
        self.assertGreaterEqual(result["invariance_cases"], 3)

if __name__ == "__main__":
    unittest.main()
