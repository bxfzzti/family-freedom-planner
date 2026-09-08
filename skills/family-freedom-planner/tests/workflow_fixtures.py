import json
from pathlib import Path


def family_state():
    root = Path(__file__).resolve().parents[1]
    return json.loads((root / "examples" / "sample_household.json").read_text())


def state_build():
    state = family_state()
    return {"family_state": state, "source_tags": state["source_tags"]}


def baseline_output():
    state = family_state()
    stable = sum(state["income"]["stable_annual"].values())
    spend = state["expenses"]["annual_total"]
    cash = state["assets"]["cash"]
    low = state["assets"]["low_risk_investments"]
    financial = cash + low + state["assets"]["investments"] + state["assets"]["other_liquid"]
    total_assets = financial + sum(x["market_value"] for x in state["assets"]["real_estate"])
    debt = sum(x["balance"] for x in state["debts"]["items"])
    return {"derived_metrics": {
        "stable_income_annual": stable, "annual_spend": spend,
        "mandatory_cashflow_annual": state["expenses"]["annual_mandatory"],
        "annual_surplus": stable - spend, "savings_rate": (stable - spend) / stable,
        "financial_assets": financial, "low_risk_assets": cash + low,
        "total_assets": total_assets, "total_debt": debt,
        "net_worth": total_assets - debt,
        "runway_months": (cash + low) / (state["expenses"]["annual_mandatory"] / 12),
        "runway_basis": "zero_income_mandatory_spending_coverage",
        "mandatory_spending_basis": "user_provided",
        "high_income_dependency": state["income"]["high_risk_annual"] / stable,
        "property_lock_ratio": 0.0},
        "calculation_source": "REFERENCE_ENGINE"}


def stress_scenarios():
    """Synthetic numeric scenarios, not empty placeholders."""
    return {
        name: {"income_annual": income, "spending_annual": 50,
               "annual_net_cashflow": income - 50,
               "assumptions": ["Synthetic annual cashflow test"]}
        for name, income in (("NORMAL", 100), ("STRESS", 60), ("SEVERE", 0))
    }
