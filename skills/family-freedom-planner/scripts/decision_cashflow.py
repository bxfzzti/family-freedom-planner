#!/usr/bin/env python3
"""Monthly, zero-return cashflow scenarios for a family decision.

Amounts are yuan; annual income/spending are after-tax cash amounts.
Monthly netting ignores intra-month timing and is not a retirement forecast.
"""
import argparse
import json
from pathlib import Path

from family_freedom_engine import n, mapping, records


def month(value, horizon, label):
    if type(value) is not int or not 1 <= value <= horizon:
        raise ValueError(f"{label} must be an integer in 1..{horizon}")
    return value


def simulate(case):
    mapping(case, "case")
    horizon = case.get("horizon_months")
    if type(horizon) is not int or not 1 <= horizon <= 1200:
        raise ValueError("horizon_months must be an integer in 1..1200")
    initial = n(case.get("initial_low_risk_assets"))
    inflow = n(case.get("upfront_net_inflow"))
    outflow = n(case.get("upfront_outflow"))
    reserve = n(case.get("protected_reserve"))
    starting = initial + inflow - outflow
    scenarios = mapping(case.get("scenarios"), "scenarios")
    if set(scenarios) != {"NORMAL", "STRESS", "SEVERE"}:
        raise ValueError("provide exactly NORMAL, STRESS and SEVERE scenarios")
    result = {}
    for name, raw in scenarios.items():
        scenario = mapping(raw, name)
        income = n(scenario.get("income_annual"))
        spend = n(scenario.get("spending_annual"))
        changes = records(scenario.get("changes"), f"{name}.changes")
        payments = records(scenario.get("one_off_expenses"), f"{name}.one_off_expenses")
        by_month = {}
        for change in changes:
            at = month(change.get("month"), horizon, "change.month")
            if at in by_month:
                raise ValueError("combine income/spending changes in the same month")
            fields = set(change) - {"month"}
            if not fields or not fields <= {"income_annual", "spending_annual"}:
                raise ValueError("change must update income_annual and/or spending_annual")
            by_month[at] = {key: n(change[key]) for key in fields}
        costs = {}
        for payment in payments:
            at = month(payment.get("month"), horizon, "one_off.month")
            costs[at] = costs.get(at, 0) + n(payment.get("amount"))
        balance = starting
        lowest = starting
        floor_breach = 0 if balance < reserve else None
        cash_shortfall = 0 if balance < 0 else None
        for at in range(1, horizon + 1):
            change = by_month.get(at, {})
            income = change.get("income_annual", income)
            spend = change.get("spending_annual", spend)
            balance += (income - spend) / 12 - costs.get(at, 0)
            # Avoid a floating-point residue changing an exact boundary.
            balance = round(balance, 8)
            lowest = min(lowest, balance)
            if floor_breach is None and balance < reserve:
                floor_breach = at
            if cash_shortfall is None and balance < 0:
                cash_shortfall = at
        result[name] = {
            "ending_low_risk_assets": round(balance, 2),
            "minimum_low_risk_assets": round(lowest, 2),
            "first_reserve_breach_month": floor_breach,
            "first_cash_shortfall_month": cash_shortfall,
            "maximum_reserve_gap": round(max(0, reserve - lowest), 2),
            "maximum_cash_shortfall": round(max(0, -lowest), 2),
            "final_annual_net_cashflow": income - spend,
        }
    return {"post_decision_low_risk_assets": starting, "protected_reserve": reserve,
            "horizon_months": horizon, "scenarios": result,
            "basis": "monthly_net_cashflow_zero_investment_return",
            "limits": "No intra-month timing; no-breach means only within this horizon. Reserve is a user input or explicit assumption, not a universal safety standard."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case")
    args = parser.parse_args()
    try:
        result = simulate(json.loads(Path(args.case).read_text(encoding="utf-8")))
        print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    except (ValueError, KeyError, TypeError, OSError, OverflowError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)


if __name__ == "__main__":
    main()
