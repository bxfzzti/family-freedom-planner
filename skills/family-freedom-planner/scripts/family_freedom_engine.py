#!/usr/bin/env python3
"""Family Freedom Planner deterministic reference engine v0.7.

Standard-library only. Amounts are in yuan. Rates are decimals (3% = 0.03).
This module performs arithmetic; it does not predict markets or policy.
"""
from __future__ import annotations

import argparse
import json
import math
import importlib.util
from pathlib import Path
from typing import Any


def validate_calculation_state(state):
    path = Path(__file__).with_name("validate_family_state.py")
    spec = importlib.util.spec_from_file_location("ffp_state_validator", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    result = module.validate_state(state, calculation_ready=True)
    if result["status"] != "PASS":
        raise ValueError("family state is not calculation-ready: " + "; ".join(result["errors"]))


def n(value: Any, default: float | None = None, *, allow_negative=False) -> float:
    if value is None and default is not None:
        value = default
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("expected a known numeric amount; unknown is not zero")
    value = float(value)
    if not math.isfinite(value) or (value < 0 and not allow_negative):
        raise ValueError("amount must be finite and non-negative")
    return value


def mapping(value, label):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an explicit object")
    return value


def records(value, label):
    if not isinstance(value, list) or not all(isinstance(x, dict) for x in value):
        raise ValueError(f"{label} must be an explicit list of objects; use [] if none")
    return value


def mortgage_payment(principal: float, annual_rate: float, years: float) -> float:
    principal, annual_rate, years = n(principal), n(annual_rate), n(years)
    if principal < 0 or annual_rate < 0 or years <= 0:
        raise ValueError("principal/rate must be non-negative; years must be positive")
    months = int(round(n(years * 12)))
    if months < 1 or not math.isclose(years * 12, months, rel_tol=0, abs_tol=1e-7):
        raise ValueError("term must contain a positive whole number of months")
    if annual_rate == 0:
        return principal / months
    r = annual_rate / 12
    if r == 0:
        return principal / months
    denominator = -math.expm1(-months * math.log1p(r))
    return n(principal * (r / denominator))


def baseline(state: dict) -> dict:
    validate_calculation_state(state)
    mapping(state, "state")
    income = mapping(state.get("income"), "income")
    expenses = mapping(state.get("expenses"), "expenses")
    assets = mapping(state.get("assets"), "assets")
    debts = mapping(state.get("debts"), "debts")
    stable = mapping(income.get("stable_annual"), "income.stable_annual")
    homes = records(assets.get("real_estate"), "assets.real_estate")
    debt_items = records(debts.get("items"), "debts.items")

    stable_income = sum(n(v) for v in stable.values())
    high_risk_income = (None if income.get("high_risk_annual") is None
                        else n(income["high_risk_annual"]))
    if high_risk_income is not None and high_risk_income > stable_income:
        raise ValueError("high_risk_annual is a subset of stable_annual, not additional income")
    annual_spend = n(expenses.get("annual_total"))
    mandatory = n(expenses.get("annual_mandatory"), annual_spend)
    if mandatory > annual_spend:
        raise ValueError("mandatory spending cannot exceed total spending")

    cash = n(assets.get("cash"))
    low_risk = n(assets.get("low_risk_investments"))
    investments = n(assets.get("investments"))
    other_liquid = n(assets.get("other_liquid"))
    financial_assets = cash + low_risk + investments + other_liquid

    real_estate_value = sum(n(x.get("market_value")) for x in homes)
    total_assets = financial_assets + real_estate_value + n(assets.get("other_non_liquid", 0))
    total_debt = sum(n(x.get("balance")) for x in debt_items)
    net_worth = total_assets - total_debt

    annual_surplus = stable_income - annual_spend
    monthly_mandatory = mandatory / 12 if mandatory > 0 else 0
    runway = None if monthly_mandatory <= 0 else (cash + low_risk) / monthly_mandatory
    dependency = (None if stable_income <= 0 or high_risk_income is None
                  else high_risk_income / stable_income)

    locked_equity = 0.0
    lock_known = all(type(home.get("sellable_for_plan")) is bool for home in homes)
    for home in homes:
        if home.get("sellable_for_plan") is False:
            locked_equity += max(
                0.0,
                n(home.get("market_value")) - n(home.get("linked_debt_balance"))
            )
    lock_ratio = (None if net_worth <= 0 or not lock_known
                  else min(max(locked_equity / net_worth, 0), 1))

    return {
        "stable_income_annual": stable_income,
        "annual_spend": annual_spend,
        "mandatory_cashflow_annual": mandatory,
        "annual_surplus": annual_surplus,
        "savings_rate": None if stable_income <= 0 else annual_surplus / stable_income,
        "financial_assets": financial_assets,
        "low_risk_assets": cash + low_risk,
        "total_assets": total_assets,
        "total_debt": total_debt,
        "net_worth": net_worth,
        "runway_months": runway,
        "runway_basis": "zero_income_mandatory_spending_coverage",
        "mandatory_spending_basis": ("user_provided" if expenses.get("annual_mandatory") is not None
                                     else "annual_total_conservative_fallback"),
        "high_income_dependency": dependency,
        "property_lock_ratio": lock_ratio,
    }


def sell_and_rent(case: dict) -> dict:
    sale_price = n(case["current_home_sale_price"])
    home_debt = n(case["current_home_debt"])
    tx = n(case.get("transaction_costs"))
    monthly_rent = n(case["monthly_rent"])
    wait_years = n(case["wait_years"])
    low_risk_return = n(case.get("low_risk_return"), allow_negative=True)
    if low_risk_return <= -1:
        raise ValueError("low_risk_return must be greater than -1")
    loan_rate = n(case.get("current_home_loan_rate"))
    friction = n(case.get("moving_and_other_friction"))

    net_sale = sale_price - home_debt - tx
    if net_sale < 0:
        raise ValueError("net sale proceeds are negative in this simplified model")

    future_value = net_sale * ((1 + low_risk_return) ** wait_years)
    investment_gain = future_value - net_sale
    rent_cost = monthly_rent * 12 * wait_years
    avoided_interest = home_debt * loan_rate * wait_years
    wait_net_cost = rent_cost - investment_gain - avoided_interest + friction
    breakeven = None if sale_price <= 0 else wait_net_cost / sale_price

    return {
        "net_sale_proceeds": net_sale,
        "investment_gain": investment_gain,
        "rent_cost": rent_cost,
        "avoided_interest": avoided_interest,
        "wait_net_cost": wait_net_cost,
        "breakeven_old_home_decline_pct": breakeven,
    }


def refinance(case: dict) -> dict:
    balance = n(case.get("principal_due_or_current_balance"))
    confirmed = n(case.get("confirmed_refinance_amount"))
    low_risk_assets = n(case.get("low_risk_assets_available"))
    emergency_floor = n(case.get("emergency_fund_floor"))
    committed_24m = n(case.get("committed_24m_capex"))

    safe_for_debt = max(0.0, low_risk_assets - emergency_floor - committed_24m)
    gap = max(0.0, balance - confirmed - safe_for_debt)

    if gap == 0 and confirmed >= 0.8 * balance:
        level = "HIGH"
    elif gap == 0:
        level = "MEDIUM"
    elif gap <= max(100000.0, 0.2 * balance):
        level = "LOW"
    else:
        level = "CRITICAL"

    return {
        "safely_available_for_debt": safe_for_debt,
        "refinance_gap": gap,
        "heuristic_level": level,
    }


def read_json(path: str) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump(data: dict) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False))


def main() -> None:
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("mortgage")
    p.add_argument("--principal", type=float, required=True)
    p.add_argument("--annual-rate", type=float, required=True)
    p.add_argument("--years", type=float, required=True)

    for cmd in ("baseline", "sell-rent", "refinance"):
        sp = sub.add_parser(cmd)
        sp.add_argument("json_file")

    args = parser.parse_args()
    if args.command == "mortgage":
        monthly = mortgage_payment(args.principal, args.annual_rate, args.years)
        dump({
            "monthly_payment": monthly,
            "annual_payment": monthly * 12,
            "principal": args.principal,
            "annual_rate": args.annual_rate,
            "years": args.years,
        })
    elif args.command == "baseline":
        dump(baseline(read_json(args.json_file)))
    elif args.command == "sell-rent":
        dump(sell_and_rent(read_json(args.json_file)))
    elif args.command == "refinance":
        dump(refinance(read_json(args.json_file)))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
