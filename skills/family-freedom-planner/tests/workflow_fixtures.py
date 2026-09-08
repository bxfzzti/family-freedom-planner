def stress_scenarios():
    """Synthetic numeric scenarios, not empty placeholders."""
    return {
        name: {"income_annual": income, "spending_annual": 50,
               "annual_net_cashflow": income - 50,
               "assumptions": ["Synthetic annual cashflow test"]}
        for name, income in (("NORMAL", 100), ("STRESS", 60), ("SEVERE", 0))
    }
