import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"scripts"/"integrity_engine.py"
spec=importlib.util.spec_from_file_location("ie",P)
ie=importlib.util.module_from_spec(spec); spec.loader.exec_module(ie)

class IntegrityEngineTests(unittest.TestCase):
    def test_amortizing_mortgage_uses_payment_check(self):
        result = ie.validate("financing", {
            "loan_structure": "FULLY_AMORTIZING_FIXED_TERM", "refinance_required": False,
            "principal": 120000, "annual_rate": 0, "years": 10,
            "monthly_payment": 1000, "balloon_payment": 0})
        self.assertEqual(result["integrity"]["status"], "PASS")

    def test_amortizing_wrong_payment_fails(self):
        result = ie.validate("financing", {
            "loan_structure": "FULLY_AMORTIZING_FIXED_TERM", "refinance_required": False,
            "principal": 120000, "annual_rate": 0, "years": 10,
            "monthly_payment": 100, "balloon_payment": 0})
        self.assertEqual(result["integrity"]["status"], "FAIL")

    def test_amortizing_balloon_is_not_exempt(self):
        result = ie.validate("financing", {
            "loan_structure": "FULLY_AMORTIZING_FIXED_TERM", "refinance_required": False,
            "principal": 120000, "annual_rate": 0, "years": 10,
            "monthly_payment": 1000, "balloon_payment": 100000})
        self.assertEqual(result["integrity"]["status"], "FAIL")

    def test_good_housing_passes(self):
        data={
            "pre_purchase_liquid_assets":400,
            "cash_outlay":240,
            "sale_net_inflow":0,
            "post_purchase_liquid_assets":160,
            "old_home_price":350,
            "target_home_price":500,
            "replacement_spread":150,
            "final_home_non_sellable":True,
            "final_home_equity_counted_as_portable":False
        }
        r=ie.validate("housing",data)
        self.assertEqual(r["integrity"]["status"],"PASS")

    def test_bad_spread_fails(self):
        data={
            "pre_purchase_liquid_assets":400,
            "cash_outlay":240,
            "post_purchase_liquid_assets":160,
            "old_home_price":350,
            "target_home_price":500,
            "replacement_spread":180
        }
        r=ie.validate("housing",data)
        self.assertEqual(r["integrity"]["status"],"FAIL")

    def test_nonsellable_home_not_portable(self):
        data={
            "final_home_non_sellable":True,
            "final_home_equity_counted_as_portable":True
        }
        r=ie.validate("housing",data)
        self.assertEqual(r["integrity"]["status"],"FAIL")

    def test_refi_identity(self):
        data={
            "principal_due_or_current_balance":300,
            "confirmed_refinance_amount":180,
            "safely_available_for_debt":80,
            "refinance_gap":40,
            "compliance_status":"VERIFIED"
        }
        r=ie.validate("financing",data)
        self.assertEqual(r["integrity"]["status"],"PASS")

    def test_no_refi_scenario_requires_zero_refi(self):
        data={
            "principal_due_or_current_balance":300,
            "confirmed_refinance_amount":180,
            "safely_available_for_debt":80,
            "refinance_gap":40,
            "scenario":"NO_REFINANCE",
            "compliance_status":"VERIFIED"
        }
        r=ie.validate("financing",data)
        self.assertEqual(r["integrity"]["status"],"FAIL")

    def test_education_monotonic(self):
        r=ie.validate("education",{"BASE":10,"MID":20,"HIGH":15})
        self.assertEqual(r["integrity"]["status"],"FAIL")

    def test_state_anomaly_detection(self):
        old={"assets":{"financial_assets":100}}
        new={"assets":{"financial_assets":10}}
        a=ie.detect_state_anomalies(old,new)
        self.assertTrue(a)

    def test_dependency_invalidation(self):
        g={"a":["b"],"b":["c"],"c":["d"]}
        r=ie.invalidate_downstream(["a"],g)
        self.assertEqual(r,["b","c","d"])

    def test_empty_financing_is_not_pass(self):
        self.assertNotEqual(ie.validate("financing", {})["integrity"]["status"], "PASS")

    def test_null_financing_is_not_zero(self):
        data = {"principal_due_or_current_balance": None,
                "confirmed_refinance_amount": 0,
                "safely_available_for_debt": 0, "refinance_gap": 0}
        self.assertEqual(ie.validate("financing", data)["integrity"]["status"], "FAIL")

    def test_nonfinite_numbers_fail_without_crash(self):
        for value in (float("nan"), float("inf"), True, "100"):
            with self.subTest(value=value):
                result = ie.validate("baseline", {
                    "total_assets": value, "total_debt": 0, "net_worth": 100})
                self.assertEqual(result["integrity"]["status"], "FAIL")

    def test_negative_financing_fails(self):
        data = {"principal_due_or_current_balance": -1,
                "confirmed_refinance_amount": 0,
                "safely_available_for_debt": 0, "refinance_gap": 0}
        self.assertEqual(ie.validate("financing", data)["integrity"]["status"], "FAIL")

    def test_negative_net_worth_is_valid(self):
        result = ie.validate("baseline", {
            "total_assets": 100, "total_debt": 200, "net_worth": -100})
        self.assertEqual(result["integrity"]["status"], "PASS")

if __name__=="__main__":
    unittest.main()
