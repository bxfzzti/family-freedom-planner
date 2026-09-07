import importlib.util
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
P=ROOT/"scripts"/"integrity_engine.py"
spec=importlib.util.spec_from_file_location("ie",P)
ie=importlib.util.module_from_spec(spec); spec.loader.exec_module(ie)

class IntegrityEngineTests(unittest.TestCase):
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

if __name__=="__main__":
    unittest.main()
