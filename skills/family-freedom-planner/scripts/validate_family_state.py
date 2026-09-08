#!/usr/bin/env python3
"""Validate the v1.4 normalized family state with the Python standard library."""
import argparse
import json
import math
import re
from pathlib import Path

VERSION = "1.4.0"
SOURCE_TYPES = {"USER_EXACT", "USER_ESTIMATE", "EXTERNAL_PRIMARY",
                "EXTERNAL_SECONDARY", "MODEL_ASSUMPTION", "DERIVED"}
CONFIDENCE = {"HIGH", "MEDIUM", "LOW"}
DATE = re.compile(r"^\d{4}-\d{2}(?:-\d{2})?$")


def number(value, path, errors, nullable=False):
    if value is None and nullable:
        return
    if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
        errors.append(f"{path} must be a finite non-negative number" +
                      (" or null" if nullable else ""))


def validate_source_tags(state, numeric_paths, errors):
    tags = state.get("source_tags")
    if not isinstance(tags, dict):
        errors.append("source_tags must be an object")
        return
    for path in numeric_paths:
        tag = tags.get(path)
        if not isinstance(tag, dict):
            errors.append(f"missing source tag: {path}")
            continue
        if tag.get("source_type") not in SOURCE_TYPES:
            errors.append(f"{path} has invalid source_type")
        if tag.get("confidence") not in CONFIDENCE:
            errors.append(f"{path} has invalid confidence")
        if not isinstance(tag.get("as_of"), str) or not DATE.match(tag["as_of"]):
            errors.append(f"{path} has invalid as_of")


def validate_state(state, calculation_ready=False):
    errors, warnings, numeric_paths = [], [], []
    if not isinstance(state, dict):
        return {"status": "FAIL", "calculation_ready": False,
                "errors": ["family state must be an object"], "warnings": []}
    if state.get("schema_version") != VERSION:
        errors.append(f"schema_version must be {VERSION}")
    if state.get("currency") != "CNY" or state.get("amount_unit") != "yuan":
        errors.append("currency/amount_unit must be CNY/yuan")
    if not isinstance(state.get("as_of"), str) or not DATE.match(state["as_of"]):
        errors.append("as_of must be YYYY-MM or YYYY-MM-DD")

    income = state.get("income")
    if not isinstance(income, dict):
        errors.append("income must be an object")
        income = {}
    if income.get("period") != "annual":
        errors.append("income.period must be annual")
    if income.get("tax_basis") not in {"AFTER_TAX", "BEFORE_TAX", "UNKNOWN"}:
        errors.append("income.tax_basis must be AFTER_TAX, BEFORE_TAX or UNKNOWN")
    stable = income.get("stable_annual")
    if not isinstance(stable, dict):
        errors.append("income.stable_annual must be an object")
        stable = {}
    for key, value in stable.items():
        path = f"income.stable_annual.{key}"
        number(value, path, errors, nullable=True)
        if value is not None:
            numeric_paths.append(path)
    if "high_risk_annual" in income:
        number(income["high_risk_annual"], "income.high_risk_annual", errors, nullable=True)
        if income["high_risk_annual"] is not None:
            numeric_paths.append("income.high_risk_annual")

    expenses = state.get("expenses")
    if not isinstance(expenses, dict):
        errors.append("expenses must be an object")
        expenses = {}
    if expenses.get("period") != "annual":
        errors.append("expenses.period must be annual")
    number(expenses.get("annual_total"), "expenses.annual_total", errors, nullable=True)
    if expenses.get("annual_total") is not None:
        numeric_paths.append("expenses.annual_total")
    number(expenses.get("annual_mandatory"), "expenses.annual_mandatory", errors, nullable=True)
    if expenses.get("annual_mandatory") is not None:
        numeric_paths.append("expenses.annual_mandatory")
    if expenses.get("annual_total_includes_debt_payments") not in (True, False, None):
        errors.append("annual_total_includes_debt_payments must be boolean or null")

    assets = state.get("assets")
    if not isinstance(assets, dict):
        errors.append("assets must be an object")
        assets = {}
    for key in ("cash", "low_risk_investments", "investments", "other_liquid",
                "unallocated_financial_assets", "other_non_liquid"):
        number(assets.get(key), f"assets.{key}", errors, nullable=True)
        if assets.get(key) is not None:
            numeric_paths.append(f"assets.{key}")
    homes = assets.get("real_estate")
    if not isinstance(homes, list) or not all(isinstance(x, dict) for x in homes):
        errors.append("assets.real_estate must be a list of objects")
        homes = []
    for index, home in enumerate(homes):
        path = f"assets.real_estate.{index}.market_value"
        number(home.get("market_value"), path, errors, nullable=True)
        if home.get("market_value") is not None:
            numeric_paths.append(path)
        debt_path = f"assets.real_estate.{index}.linked_debt_balance"
        number(home.get("linked_debt_balance"), debt_path, errors, nullable=True)
        if home.get("linked_debt_balance") is not None:
            numeric_paths.append(debt_path)
        if home.get("sellable_for_plan") not in (True, False, None):
            errors.append(f"assets.real_estate.{index}.sellable_for_plan must be boolean or null")

    debts = state.get("debts")
    if not isinstance(debts, dict):
        errors.append("debts must be an object")
        debts = {}
    items = debts.get("items")
    if not isinstance(items, list) or not all(isinstance(x, dict) for x in items):
        errors.append("debts.items must be a list of objects")
        items = []
    for index, item in enumerate(items):
        path = f"debts.items.{index}.balance"
        number(item.get("balance"), path, errors, nullable=True)
        if item.get("balance") is not None:
            numeric_paths.append(path)
        if item.get("balance_basis") not in {"CURRENT_BALANCE", "ORIGINAL_PRINCIPAL", "UNKNOWN"}:
            errors.append(f"debts.items.{index}.balance_basis is invalid")
    debt_ids = [item.get("id") for item in items]
    if any(not isinstance(value, str) or not value for value in debt_ids):
        errors.append("every debt item needs a nonempty id")
    if len(debt_ids) != len(set(debt_ids)):
        errors.append("debt item ids must be unique")
    debt_by_id = {item.get("id"): item for item in items if isinstance(item.get("id"), str)}
    home_ids = [home.get("id") for home in homes]
    if any(not isinstance(value, str) or not value for value in home_ids):
        errors.append("every real-estate item needs a nonempty id")
    if len(home_ids) != len(set(home_ids)):
        errors.append("real-estate ids must be unique")
    for index, home in enumerate(homes):
        linked_id = home.get("linked_debt_id")
        linked_balance = home.get("linked_debt_balance")
        if linked_balance not in (None, 0, 0.0):
            if linked_id not in debt_by_id:
                errors.append(f"assets.real_estate.{index}.linked_debt_id is unresolved")
            elif debt_by_id[linked_id].get("balance") != linked_balance:
                errors.append(f"assets.real_estate.{index}.linked debt balance conflicts with debts.items")
        elif linked_id is not None and linked_id not in debt_by_id:
            errors.append(f"assets.real_estate.{index}.linked_debt_id is unresolved")

    validate_source_tags(state, numeric_paths, errors)
    if calculation_ready:
        if income.get("tax_basis") != "AFTER_TAX":
            errors.append("calculation requires AFTER_TAX income")
        if not stable or any(value is None for value in stable.values()):
            errors.append("calculation requires known stable_annual values")
        if expenses.get("annual_total") is None:
            errors.append("calculation requires annual_total")
        if type(expenses.get("annual_total_includes_debt_payments")) is not bool:
            errors.append("calculation requires debt-payment inclusion basis")
        for key in ("cash", "low_risk_investments", "investments",
                    "other_liquid", "other_non_liquid"):
            if assets.get(key) is None:
                errors.append(f"calculation requires assets.{key}")
        if assets.get("unallocated_financial_assets") not in (0, 0.0):
            errors.append("allocate financial assets before calculation")
        if any(home.get("market_value") is None for home in homes):
            errors.append("calculation requires known real-estate values")
        if any(home.get("linked_debt_balance") is None for home in homes):
            errors.append("calculation requires known linked debt balances")
        if any(item.get("balance") is None or item.get("balance_basis") != "CURRENT_BALANCE"
               for item in items):
            errors.append("calculation requires current debt balances")
    if not calculation_ready and not errors:
        if income.get("tax_basis") != "AFTER_TAX":
            warnings.append("income tax basis needs confirmation before calculation")
        if assets.get("unallocated_financial_assets") not in (0, 0.0, None):
            warnings.append("financial asset composition needs confirmation before calculation")
    return {"status": "FAIL" if errors else "PASS",
            "calculation_ready": calculation_ready and not errors,
            "errors": errors, "warnings": warnings}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("state")
    parser.add_argument("--calculation-ready", action="store_true")
    args = parser.parse_args()
    data = json.loads(Path(args.state).read_text(encoding="utf-8"))
    state = data.get("family_state") if isinstance(data, dict) and "family_state" in data else data
    result = validate_state(state, args.calculation_ready)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 2)


if __name__ == "__main__":
    main()
