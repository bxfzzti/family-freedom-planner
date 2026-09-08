#!/usr/bin/env python3
"""Migrate a legacy 0.9 context capsule to the explicit v1.4 envelope."""
import argparse
import json
from pathlib import Path

from validate_family_state import validate_state


def tag(as_of, source_type="USER_ESTIMATE", confidence="MEDIUM"):
    return {"source_type": source_type, "as_of": as_of, "confidence": confidence}


def migrate(old):
    if not isinstance(old, dict) or old.get("schema_version") != "0.9":
        raise ValueError("expected a legacy schema_version 0.9 context")
    as_of = old.get("as_of")
    income = old.get("income", {})
    expenses = old.get("expenses", {})
    assets = old.get("assets", {})
    housing = old.get("housing", {})
    reported_income = income.get("stable_household_income_annual")
    reported_financial = assets.get("cash_and_financial_assets")
    home_value = housing.get("primary_home_value")
    home_debt = housing.get("primary_home_debt")
    state = {
        "schema_version": "1.4.0", "as_of": as_of,
        "currency": "CNY", "amount_unit": "yuan",
        "income": {
            "period": "annual", "tax_basis": "UNKNOWN",
            "stable_annual": {"household_reported": reported_income},
            "high_risk_annual": income.get("high_risk_income_annual")},
        "expenses": {
            "period": "annual",
            "annual_total": expenses.get("annual_household_spend"),
            "annual_mandatory": None,
            "annual_total_includes_debt_payments": None},
        "assets": {
            "cash": None, "low_risk_investments": None, "investments": None,
            "other_liquid": None,
            "unallocated_financial_assets": reported_financial,
            "real_estate": ([{
                "id": "primary_home", "market_value": home_value,
                "linked_debt_id": "primary_home_debt" if home_debt is not None else None,
                "linked_debt_balance": home_debt,
                "sellable_for_plan": None}] if home_value is not None else []),
            "other_non_liquid": None},
        "debts": {"items": ([{
            "id": "primary_home_debt", "balance": home_debt,
            "balance_basis": "CURRENT_BALANCE"}] if home_debt is not None else [])},
        "household": old.get("household", {}),
        "career": old.get("career", {}),
        "education": old.get("education", {}),
        "housing": {key: value for key, value in housing.items()
                    if key not in ("primary_home_value", "primary_home_debt")},
        "preferences": old.get("preferences", {}),
        "deadlines": old.get("deadlines", []),
        "primary_decision": old.get("primary_decision"),
        "source_tags": {}
    }
    paths = {
        "income.stable_annual.household_reported": reported_income,
        "income.high_risk_annual": income.get("high_risk_income_annual"),
        "expenses.annual_total": expenses.get("annual_household_spend"),
        "assets.unallocated_financial_assets": reported_financial,
        "assets.real_estate.0.market_value": home_value,
        "assets.real_estate.0.linked_debt_balance": home_debt,
        "debts.items.0.balance": home_debt,
    }
    state["source_tags"] = {path: tag(as_of) for path, value in paths.items()
                            if value is not None}
    result = {
        "schema_version": "1.4.0", "as_of": as_of, "family_state": state,
        "goals": old.get("goals", []),
        "assumptions": list(old.get("assumptions", [])),
        "open_questions": list(old.get("open_questions", [])),
        "decision_journal": old.get("decision_journal", [])
    }
    result["open_questions"].extend([
        "确认家庭收入是税前还是税后，并拆分稳定收入来源",
        "把合并金融资产拆分为现金、低风险资产、波动资产和其他流动资产",
        "确认年支出是否包含全部债务还款，并填写必要支出"])
    check = validate_state(state, calculation_ready=False)
    if check["status"] != "PASS":
        raise ValueError("migration produced invalid state: " + "; ".join(check["errors"]))
    result["migration"] = {
        "from": "0.9", "to": "1.4.0", "calculation_ready": False,
        "reason": "legacy tax, spending and financial-asset composition are not explicit"}
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("legacy_context")
    args = parser.parse_args()
    try:
        result = migrate(json.loads(Path(args.legacy_context).read_text(encoding="utf-8")))
    except (ValueError, TypeError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
