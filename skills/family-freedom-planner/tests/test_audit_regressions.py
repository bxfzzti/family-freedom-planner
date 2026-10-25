"""Regression reproductions for all ten confirmed audit findings."""
import copy
import json
import os
import stat
import sys
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import workflow_orchestrator as w
import family_freedom_engine as e
import decision_cashflow as cashflow
import plan_engine
import validate_family_state as state_validator
import migrate_context
import fact_evidence
import private_storage
import evaluate_dialogues


def source():
    return json.loads((ROOT / "examples/sample_household.json").read_text())


def full_run(mutate=None):
    state = source()
    outputs = plan_engine.step_outputs(state)
    if mutate:
        mutate(outputs)
    topics = ["HOUSING_EXISTING", "FINANCING", "CAREER"]
    run = w.init_run({"user_text": "Synthetic audit regression", "selected_topics": topics})
    w.complete_step(run, "INTAKE_ROUTE", {
        "selected_topics": topics, "known_facts": {}, "missing_fields": []})
    for step in ("STATE_BUILD", "INPUT_VALIDATE", "DEADLINE_IDENTIFY", "BASELINE_CALCULATE",
                 "HOUSING_ANALYSIS", "FINANCING_ANALYSIS", "CAREER_ANALYSIS",
                 "STRESS_TEST", "OPTIONS_BUILD", "OPTIONS_VALIDATE"):
        w.complete_step(run, step, outputs[step])
    w.evaluate_integrity_gate(run)
    w.evaluate_gate(run)
    return run


class FinancialRegressionTests(unittest.TestCase):
    def test_F01_excluded_debt_is_added_to_spending(self):
        state = source()
        state["expenses"]["annual_total_includes_debt_payments"] = False
        result = e.baseline(state)
        self.assertEqual(result["annual_spend"], 240000)
        self.assertEqual(result["annual_surplus"], 420000)
        self.assertEqual(result["mandatory_cashflow_annual"], 210000)

    def test_F01_missing_payment_schedule_blocks_calculation(self):
        state = source()
        state["expenses"]["annual_total_includes_debt_payments"] = False
        del state["debts"]["items"][0]["annual_payment"]
        with self.assertRaises(ValueError):
            e.baseline(state)

    def test_F02_invented_cash_still_fails_if_result_recomputed(self):
        def change(outputs):
            entry = outputs["STRESS_TEST"]["option_runs"][0]
            entry["input"]["initial_low_risk_assets"] = 50000000
            entry["result"] = cashflow.simulate(entry["input"])
        run = full_run(change)
        self.assertEqual(run["gate"]["status"], "BLOCKED")
        self.assertEqual(run["steps"]["STRESS_TEST"]["status"], "QUARANTINED")

    def test_F02_invented_spending_is_not_a_valid_stress_source(self):
        def change(outputs):
            entry = outputs["STRESS_TEST"]["option_runs"][0]
            entry["input"]["scenarios"]["SEVERE"]["spending_annual"] = 0
            entry["result"] = cashflow.simulate(entry["input"])
        self.assertEqual(full_run(change)["gate"]["status"], "BLOCKED")

    def test_F03_purchase_must_be_funded(self):
        state = source()
        state["decision_plan"]["options"][0]["down_payment"] = 1
        with self.assertRaises(ValueError):
            plan_engine.derive(state)

    def test_F03_fake_output_cannot_hide_source_costs(self):
        def change(outputs):
            option = outputs["HOUSING_ANALYSIS"]["results"]["options"][0]
            option["cash_outlay"] = 1
            option["post_purchase_liquid_assets"] = option["pre_purchase_liquid_assets"] + option["sale_net_inflow"] - 1
        self.assertEqual(full_run(change)["gate"]["status"], "BLOCKED")

    def test_F03_source_down_payment_must_fit_available_funds(self):
        state = source()
        option = state["decision_plan"]["options"][0]
        option["loans"] = []
        option["down_payment"] = option["target_home_price"]
        with self.assertRaises(ValueError):
            plan_engine.derive(state)

    def test_F05_missing_mortgage_option_blocks(self):
        def change(outputs):
            outputs["FINANCING_ANALYSIS"]["results"]["loans"] = [
                x for x in outputs["FINANCING_ANALYSIS"]["results"]["loans"] if x["option_id"] == "A"]
        self.assertEqual(full_run(change)["gate"]["status"], "BLOCKED")

    def test_F05_combination_loan_has_separate_tranches(self):
        state = source()
        option = state["decision_plan"]["options"][0]
        option["loans"] = [
            {"loan_id": "fund", "principal": 1000000, "annual_rate": .026, "years": 30},
            {"loan_id": "bank", "principal": 2000000, "annual_rate": .03, "years": 30}]
        result = plan_engine.derive(state)["options"][0]
        self.assertEqual(sum(x["principal"] for x in result["loans"]), 3000000)
        self.assertEqual({x["option_id"] for x in result["loans"]}, {"A"})

    def test_F06_missing_option_runs_blocks(self):
        def change(outputs):
            del outputs["STRESS_TEST"]["option_runs"]
        self.assertEqual(full_run(change)["gate"]["status"], "BLOCKED")

    def test_F06_missing_source_plan_blocks(self):
        state = source()
        del state["decision_plan"]
        with self.assertRaises(ValueError):
            plan_engine.derive(state)

    def test_source_bound_workflow_can_finalize(self):
        run = full_run()
        self.assertEqual(run["gate"]["status"], "CONDITIONAL_PASS")  # actual contracts not inspected
        w.finalize(run, {"final_output_mode": "CONDITIONAL",
                         "conditional_constraints_acknowledged": True,
                         "decision_summary": "Synthetic conditional plan"})
        self.assertEqual(run["steps"]["FINALIZE"]["status"], "COMPLETE")


class MigrationRegressionTests(unittest.TestCase):
    def test_F04_extra_debt_and_original_are_retained(self):
        old = json.loads((ROOT / "examples/family-context-old.json").read_text())
        old["debts"] = {"items": [{"id": "consumer", "balance": 600000}]}
        old["assets"].update(cash=200000, investments=800000)
        result = migrate_context.migrate(old)
        self.assertEqual(result["migration"]["original_context"], old)
        self.assertIn(600000, [x["balance"] for x in result["family_state"]["debts"]["items"]])
        self.assertEqual(result["family_state"]["assets"]["cash"], 200000)
        self.assertEqual(result["family_state"]["assets"]["investments"], 800000)
        self.assertEqual(result["family_state"]["assets"]["unallocated_financial_assets"], 0)
        self.assertFalse(result["migration"]["resolved"])
        self.assertTrue(result["migration"]["unresolved_fields"])


class ValidationRegressionTests(unittest.TestCase):
    def test_initial_confirmed_state_cannot_be_silently_replaced(self):
        state = source()
        run = w.init_run({"user_text": "Synthetic confirmed source",
                          "selected_topics": ["GENERAL"], "family_state": state})
        changed = copy.deepcopy(state)
        changed["assets"]["cash"] = 50000000
        valid, _ = w.validate_state_build(
            {"family_state": changed, "source_tags": changed["source_tags"]}, run)
        self.assertFalse(valid)
    def test_precision_does_not_allow_thousands_of_yuan_error(self):
        import integrity_engine
        result = integrity_engine.validate("housing", {
            "pre_purchase_liquid_assets": 800000, "cash_outlay": 200000,
            "sale_net_inflow": 0, "post_purchase_liquid_assets": 603000,
            "old_home_price": 3500000, "target_home_price": 5000000,
            "replacement_spread": 1505000})
        self.assertEqual(result["integrity"]["status"], "FAIL")
    def test_F08_unknown_field_is_rejected(self):
        state = source()
        state["income"]["invented"] = 1
        self.assertEqual(state_validator.validate_state(state, True)["status"], "FAIL")

    def test_F08_numeric_boolean_rejected(self):
        state = source()
        state["assets"]["real_estate"][0]["sellable_for_plan"] = 1
        self.assertEqual(state_validator.validate_state(state, True)["status"], "FAIL")

    def test_F08_array_id_returns_fail_not_exception(self):
        state = source()
        state["debts"]["items"][0]["id"] = []
        self.assertEqual(state_validator.validate_state(state, True)["status"], "FAIL")

    def test_F08_missing_required_nullable_field_rejected(self):
        state = source()
        del state["income"]["high_risk_annual"]
        self.assertEqual(state_validator.validate_state(state, True)["status"], "FAIL")


class EvidenceRegressionTests(unittest.TestCase):
    def evidence(self):
        today = datetime.now(timezone.utc).date()
        return {"facts": [{"id": "rate", "kind": "rate", "value": .03,
                          "region": "Synthetic only", "source_type": "OFFICIAL",
                          "source": "https://example.gov/rate", "verification_method": "test fixture",
                          "as_of": today.isoformat(), "valid_until": (today + timedelta(days=1)).isoformat()}],
                "verification_status": "VERIFIED", "conditionalized_if_unverified": False}

    def test_F07_empty_verified_rejected(self):
        good, _ = w.validate_external_facts({
            "facts": [], "verification_status": "VERIFIED",
            "conditionalized_if_unverified": False}, {})
        self.assertFalse(good)

    def test_F07_expired_or_missing_region_not_verified(self):
        evidence = self.evidence()
        evidence["facts"][0]["valid_until"] = "2000-01-01"
        self.assertNotEqual(fact_evidence.evaluate(evidence)["status"], "VERIFIED")
        evidence = self.evidence()
        del evidence["facts"][0]["region"]
        self.assertNotEqual(fact_evidence.evaluate(evidence)["status"], "VERIFIED")

    def test_F07_current_metadata_is_not_rejected(self):
        self.assertEqual(fact_evidence.evaluate(self.evidence())["status"], "VERIFIED")

    def test_F07_wrong_region_is_not_verified(self):
        self.assertNotEqual(fact_evidence.evaluate(
            self.evidence(), expected_region="Different jurisdiction")["status"], "VERIFIED")

    def test_F10_arbitrary_revision_is_stale(self):
        p = ROOT / "evals"
        suite = json.loads((p / "dialogue_cases.json").read_text())
        records = json.loads((p / "results/v1.3-dialogue-recordings.json").read_text())
        reviews = json.loads((p / "results/v1.3-dialogue-reviews.json").read_text())
        records["run"]["skill_revision"] = "arbitrary"
        result = evaluate_dialogues.evaluate(suite, records, reviews, expected_fingerprint="current")
        self.assertEqual(result["status"], "STALE")


class StorageRegressionTests(unittest.TestCase):
    def test_F09_private_permissions_and_stale_writer(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            mask = os.umask(0o022)
            try:
                private_storage.save(path, {"A": False, "B": False})
            finally:
                os.umask(mask)
            if os.name != "nt":
                self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            a, b = private_storage.load(path), private_storage.load(path)
            a["A"] = True
            private_storage.save(path, a)
            b["B"] = True
            with self.assertRaises(private_storage.StorageError):
                private_storage.save(path, b)
            self.assertTrue(private_storage.load(path)["A"])

    def test_F09_failed_atomic_write_preserves_old_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            private_storage.save(path, {"value": 1})
            value = private_storage.load(path)
            value["value"] = 2
            with patch("private_storage.os.replace", side_effect=OSError("simulated failure")):
                with self.assertRaises(OSError):
                    private_storage.save(path, value)
            self.assertEqual(private_storage.load(path)["value"], 1)

    def test_F09_restore_and_symbolic_link(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            private_storage.save(path, {"value": 1})
            doc = private_storage.load(path)
            doc["value"] = 2
            private_storage.save(path, doc)
            self.assertEqual(private_storage.restore(path)["value"], 1)
            alias = Path(directory) / "alias.json"
            alias.symlink_to(path)
            with self.assertRaises(private_storage.StorageError):
                private_storage.save(alias, {"bad": True})

    def test_F09_recovery_can_restore_a_missing_document(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "run.json"
            private_storage.save(path, {"value": 1})
            doc = private_storage.load(path)
            doc["value"] = 2
            private_storage.save(path, doc)
            path.unlink()
            self.assertEqual(private_storage.restore(path)["value"], 1)


if __name__ == "__main__":
    unittest.main()
