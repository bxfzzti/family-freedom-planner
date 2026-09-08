#!/usr/bin/env python3
"""Result integrity checks for Family Freedom Planner v1.4.

Standard-library only.
"""
from __future__ import annotations
import json
import math
from copy import deepcopy


class IntegrityError(Exception):
    pass


def rel_diff(a, b):
    a = float(a); b = float(b)
    denom = max(abs(a), abs(b), 1.0)
    return abs(a-b)/denom


def check_close(name, a, b, tolerance=0.005):
    diff = rel_diff(a,b)
    return {
        "name":name,
        "pass":diff <= tolerance,
        "relative_diff":diff,
        "expected":b,
        "actual":a,
        "tolerance":tolerance
    }


def mortgage_payment_independent(principal, annual_rate, years):
    principal=float(principal); annual_rate=float(annual_rate); years=float(years)
    n=int(round(years*12))
    if annual_rate == 0:
        return principal/n
    r=annual_rate/12
    return principal*r/(1-(1+r)**(-n))


def validate_baseline(metrics):
    checks=[]
    if all(k in metrics for k in ("total_assets","total_debt","net_worth")):
        checks.append(check_close(
            "net_worth_identity",
            metrics["net_worth"],
            metrics["total_assets"]-metrics["total_debt"],
            1e-9
        ))
    if all(k in metrics for k in ("stable_income_annual","annual_spend","annual_surplus")):
        checks.append(check_close(
            "annual_surplus_identity",
            metrics["annual_surplus"],
            metrics["stable_income_annual"]-metrics["annual_spend"],
            1e-9
        ))
    return checks


def validate_housing(data):
    checks=[]
    issues=[]
    before=data.get("pre_purchase_liquid_assets")
    cash_out=data.get("cash_outlay")
    sale_in=data.get("sale_net_inflow",0)
    after=data.get("post_purchase_liquid_assets")
    if None not in (before,cash_out,after):
        expected=float(before)-float(cash_out)+float(sale_in)
        checks.append(check_close("post_purchase_liquidity",after,expected,0.005))

    old=data.get("old_home_price")
    target=data.get("target_home_price")
    spread=data.get("replacement_spread")
    if None not in (old,target,spread):
        checks.append(check_close("replacement_spread",spread,float(target)-float(old),0.005))

    if data.get("final_home_non_sellable") and data.get("final_home_equity_counted_as_portable"):
        issues.append("non-sellable final-home equity cannot be counted as portable assets")

    for k in ("cash_outlay","transaction_costs"):
        if k in data and data[k] is not None and float(data[k]) < 0:
            issues.append(f"{k} cannot be negative")
    return checks, issues


def validate_financing(data):
    checks=[]
    issues=[]
    if (data.get("loan_structure") == "FULLY_AMORTIZING_FIXED_TERM"
            and data.get("refinance_required") is False):
        years = data["years"]
        if (data["balloon_payment"] != 0 or years <= 0
                or not math.isclose(years * 12, round(years * 12), abs_tol=1e-7)
                or years * 12 < 1):
            return [], ["amortizing loan requires whole positive months and zero balloon"]
        try:
            expected = mortgage_payment_independent(
                data["principal"], data["annual_rate"], years)
        except (ValueError, ZeroDivisionError, OverflowError):
            return [], ["independent payment calculation could not be completed"]
        checks.append(check_close("amortizing_monthly_payment",
                                  data["monthly_payment"], expected, 1e-7))
        return checks, issues
    balance=float(data.get("principal_due_or_current_balance",0) or 0)
    refi=float(data.get("confirmed_refinance_amount",0) or 0)
    safe=float(data.get("safely_available_for_debt",0) or 0)
    gap=float(data.get("refinance_gap",0) or 0)
    expected=max(0,balance-refi-safe)
    checks.append(check_close("refinance_gap_identity",gap,expected,0.005))

    if data.get("scenario")=="NO_REFINANCE" and refi != 0:
        issues.append("NO_REFINANCE scenario requires confirmed_refinance_amount=0")

    compliance=data.get("compliance_status")
    executable=data.get("treated_as_confirmed_executable")
    if compliance != "VERIFIED" and executable is True:
        issues.append("unverified financing cannot be treated as confirmed executable")
    return checks, issues


def validate_education(data):
    checks=[]
    issues=[]
    base=data.get("BASE")
    mid=data.get("MID")
    high=data.get("HIGH")
    if all(isinstance(x,(int,float)) for x in (base,mid,high)):
        checks.append({"name": "education_scenario_monotonic",
                       "pass": base <= mid <= high,
                       "actual": {"BASE": base, "MID": mid, "HIGH": high}})
    else:
        issues.append("education scenarios require numeric BASE, MID and HIGH")
    return checks, issues


def validate_career(data):
    checks=[]
    issues=[]
    current=data.get("current_stable_income")
    reduced=data.get("reduced_main_income")
    new_sources=data.get("new_income_sources",0) or 0
    resulting=data.get("resulting_stable_income")
    if None not in (current,reduced,resulting):
        theoretical=float(current)-float(reduced)+float(new_sources)
        checks.append(check_close("career_income_identity", resulting, theoretical, 0.005))
    else:
        issues.append("career integrity inputs are incomplete")
    return checks, issues


def summarize(checks, issues):
    failed=[x for x in checks if not x["pass"]]
    if issues or failed:
        return {
            "status":"FAIL",
            "confidence":"LOW",
            "issues":issues+[f"cross-check failed: {x['name']}" for x in failed]
        }
    if not checks:
        return {"status":"WARN","confidence":"MEDIUM","issues":["no independent numeric cross-check available"]}
    return {"status":"PASS","confidence":"HIGH","issues":[]}


def validate(domain, data):
    numeric_fields = {
        "baseline": ("total_assets", "total_debt", "net_worth",
                     "stable_income_annual", "annual_spend", "annual_surplus"),
        "housing": ("pre_purchase_liquid_assets", "cash_outlay", "sale_net_inflow",
                    "post_purchase_liquid_assets", "old_home_price",
                    "target_home_price", "replacement_spread", "transaction_costs"),
        "financing": ("principal_due_or_current_balance", "confirmed_refinance_amount",
                      "safely_available_for_debt", "refinance_gap"),
        "education": ("BASE", "MID", "HIGH"),
        "career": ("current_stable_income", "reduced_main_income",
                   "new_income_sources", "resulting_stable_income"),
    }
    signed = {"net_worth", "annual_surplus", "replacement_spread",
              "post_purchase_liquid_assets"}
    if (domain == "financing" and isinstance(data, dict)
            and data.get("loan_structure") == "FULLY_AMORTIZING_FIXED_TERM"
            and data.get("refinance_required") is False):
        numeric_fields["financing"] = ("principal", "annual_rate", "years",
                                       "monthly_payment", "balloon_payment")
    input_issues = []
    if not isinstance(data, dict):
        input_issues.append("result must be an object")
    else:
        for key in numeric_fields.get(domain, ()):
            if key not in data:
                if domain == "financing":
                    input_issues.append(f"missing required financing value: {key}")
                continue
            value = data[key]
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or (key not in signed and value < 0)):
                input_issues.append(f"invalid numeric value: {key}")
    if input_issues:
        return {"domain": domain, "cross_checks": [],
                "integrity": summarize([], input_issues)}
    if domain=="baseline":
        checks=validate_baseline(data)
        issues=[]
    elif domain=="housing":
        checks,issues=validate_housing(data)
    elif domain=="financing":
        checks,issues=validate_financing(data)
    elif domain=="education":
        checks,issues=validate_education(data)
    elif domain=="career":
        checks,issues=validate_career(data)
    else:
        checks=[]; issues=[]
    return {
        "domain":domain,
        "cross_checks":checks,
        "integrity":summarize(checks,issues)
    }


def detect_state_anomalies(old_state, new_state, thresholds=None):
    thresholds=thresholds or {
        "income":0.5,
        "assets":0.5,
        "housing":0.3,
        "debts":0.3
    }
    anomalies=[]
    for group,limit in thresholds.items():
        old=old_state.get(group,{})
        new=new_state.get(group,{})
        if isinstance(old,dict) and isinstance(new,dict):
            for k in set(old)&set(new):
                a,b=old[k],new[k]
                if isinstance(a,(int,float)) and isinstance(b,(int,float)) and a!=0:
                    change=abs(b-a)/abs(a)
                    if change>limit:
                        anomalies.append({
                            "path":f"{group}.{k}",
                            "old":a,"new":b,
                            "relative_change":change,
                            "issue":"POSSIBLE_PARSE_ERROR_OR_REAL_DELTA"
                        })
    return anomalies


def invalidate_downstream(changed_fields, dependency_graph):
    invalid=set()
    frontier=list(changed_fields)
    seen=set()
    while frontier:
        node=frontier.pop()
        if node in seen:
            continue
        seen.add(node)
        for dep in dependency_graph.get(node,[]):
            if dep not in invalid:
                invalid.add(dep)
                frontier.append(dep)
    return sorted(invalid)
