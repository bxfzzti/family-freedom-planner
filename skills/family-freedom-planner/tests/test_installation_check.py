import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import check_installation


class InstallationCheckTests(unittest.TestCase):
    def test_current_bundle_and_calculation(self):
        result = check_installation.check(ROOT)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["calculation_smoke"], "PASS")
        self.assertEqual(result["host_auto_activation"], "NOT_TESTED")

    def test_empty_installation_cannot_pass(self):
        with tempfile.TemporaryDirectory() as directory:
            result = check_installation.check(directory)
        self.assertEqual(result["status"], "FAIL")
        self.assertEqual(result["calculation_smoke"], "NOT_RUN")
        self.assertIn("missing file: SKILL.md", result["issues"])


if __name__ == "__main__":
    unittest.main()
