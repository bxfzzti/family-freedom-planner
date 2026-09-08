import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import migrate_context
import validate_family_state


class MigrationTests(unittest.TestCase):
    def setUp(self):
        self.old = json.loads((ROOT / "examples" / "family-context-old.json").read_text())

    def test_migration_preserves_amounts_without_inventing_liquidity(self):
        result = migrate_context.migrate(self.old)
        state = result["family_state"]
        self.assertEqual(state["assets"]["unallocated_financial_assets"], 1000000)
        self.assertIsNone(state["assets"]["cash"])
        self.assertEqual(state["income"]["tax_basis"], "UNKNOWN")
        self.assertFalse(result["migration"]["calculation_ready"])

    def test_migrated_state_is_valid_but_not_calculation_ready(self):
        state = migrate_context.migrate(self.old)["family_state"]
        self.assertEqual(validate_family_state.validate_state(state)["status"], "PASS")
        self.assertEqual(validate_family_state.validate_state(state, True)["status"], "FAIL")

    def test_wrong_version_rejected(self):
        self.old["schema_version"] = "1.4.0"
        with self.assertRaises(ValueError):
            migrate_context.migrate(self.old)

    def test_goals_and_journal_preserved(self):
        result = migrate_context.migrate(self.old)
        self.assertEqual(result["goals"], self.old["goals"])
        self.assertEqual(result["decision_journal"], self.old["decision_journal"])


if __name__ == "__main__":
    unittest.main()
