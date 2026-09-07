#!/usr/bin/env python3
"""Result integrity checks for Family Freedom Planner v1.2.

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
    issues=[]
    base=data.get("BASE")
    mid=data.get("MID")
    high=data.get("HIGH")
    if all(isinstance(x,(int,float)) for x in (base,mid,high)):
        if not (base <= mid <= high):
            issues.append("education scenarios must satisfy BASE <= MID <= HIGH")
    return [], issues


def validate_career(data):
    issues=[]
    current=data.get("current_stable_income")
    reduced=data.get("reduced_main_income")
    new_sources=data.get("new_income_sources",0) or 0
    resulting=data.get("resulting_stable_income")
    if None not in (current,reduced,resulting):
        theoretical=float(current)-float(reduced)+float(new_sources)
        if float(resulting) > theoretical*1.01:
            issues.append("career income increased beyond declared new income sources")
    return [], issues


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
