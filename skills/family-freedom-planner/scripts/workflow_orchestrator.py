#!/usr/bin/env python3
"""Family Freedom Planner Workflow Orchestrator v1.1.

A fail-closed control plane for step ordering, output validation,
explicit skips, recommendation gating, and execution ledger.

Standard-library only.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_PATH = ROOT / "assets" / "workflow.compiled.json"

INTEGRITY_RESULTS_KEY = "integrity_results"

def _load_integrity_module():
    import importlib.util
    p = ROOT / "scripts" / "integrity_engine.py"
    spec = importlib.util.spec_from_file_location("ffp_integrity_engine", p)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod



class WorkflowError(Exception):
    pass


def now():
    return datetime.now(timezone.utc).isoformat()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def save_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def load_workflow():
    workflow = load_json(WORKFLOW_PATH)
    content = {key: value for key, value in workflow.items() if key != "spec_hash"}
    if workflow.get("spec_hash") != output_digest(content):
        raise WorkflowError("workflow content does not match spec_hash")
    return workflow


def ensure_run_spec(run):
    workflow = load_workflow()
    if (run.get("workflow_spec_hash") != workflow["spec_hash"]
            or run.get("workflow_version") != workflow["version"]):
        raise WorkflowError("run uses an older/different workflow; initialize a new run from confirmed inputs")


def step_map(workflow):
    return {x["id"]: x for x in workflow["steps"]}


def route_topics(user_text):
    # One shared candidate router prevents CLI and Agent entrypoints drifting.
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "ffp_intake_router", ROOT / "scripts" / "intake_router.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.route(user_text)["selected_topics"]


def valid_topics(topics):
    allowed = {"GENERAL", "HOUSING_EXISTING", "HOUSING_FIRST_BUY", "EDUCATION",
               "CAREER", "SPOUSE_BREAK", "FINANCING", "PARENT_CARE", "RELOCATION", "INVESTING"}
    return (isinstance(topics, list) and 1 <= len(topics) <= 3
            and all(isinstance(t, str) and t in allowed for t in topics)
            and len(set(topics)) == len(topics))


def output_digest(output):
    import hashlib
    return hashlib.sha256(json.dumps(
        output, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
        allow_nan=False).encode("utf-8")).hexdigest()


def clear_gates(run):
    run["gate"] = None
    run["integrity_gate"] = None
    for sid in ("INTEGRITY_GATE", "RECOMMENDATION_GATE", "FINALIZE"):
        if sid in run["steps"]:
            run["steps"][sid].update(status="PENDING", output=None, validation=None)


def applicable(step, run):
    expr = step["applicability"]
    if expr == "always":
        return True, None
    if expr.startswith("topic:"):
        options = expr.split(":",1)[1].split("|")
        selected = set(run["context"]["selected_topics"])
        ok = bool(selected.intersection(options))
        return ok, None if ok else f"not_selected_topic:{'|'.join(options)}"
    if expr.startswith("flag:"):
        flag = expr.split(":",1)[1]
        ok = bool(run["context"].get(flag))
        return ok, None if ok else f"flag_false:{flag}"
    raise WorkflowError(f"unknown applicability: {expr}")


def prereqs_satisfied(step, run):
    ensure_run_spec(run)
    for req in step["requires"]:
        status = run["steps"][req]["status"]
        if status not in ("COMPLETE", "SKIPPED"):
            return False, f"prerequisite {req} is {status}"
    return True, None


def init_run(input_data):
    wf = load_workflow()
    selected_topics = input_data.get("selected_topics") or route_topics(input_data.get("user_text",""))
    if not valid_topics(selected_topics):
        raise WorkflowError("selected_topics must contain 1..3 unique known topics")
    run = {
        "workflow_version": wf["version"],
        "workflow_spec_hash": wf["spec_hash"],
        "run_id": input_data.get("run_id") or f"ffp-{int(datetime.now().timestamp())}",
        "created_at": now(),
        "context": {
            "user_text": input_data.get("user_text",""),
            "selected_topics": selected_topics,
            "requires_external_facts": bool(input_data.get("requires_external_facts", False)),
            "known_context": input_data.get("known_context", {}),
        },
        "steps": {},
        "ledger": [],
        "gate": None,
        "integrity_gate": None,
        "integrity_results": {},
        "snapshots": [],
    }
    for step in wf["steps"]:
        run["steps"][step["id"]] = {
            "status": "PENDING",
            "output": None,
            "validation": None,
            "skip_reason": None,
            "order": None,
        }

    # Auto-skip inapplicable non-system domain steps, explicitly ledgered.
    for step in wf["steps"]:
        ok, reason = applicable(step, run)
        if not ok:
            run["steps"][step["id"]]["status"] = "SKIPPED"
            run["steps"][step["id"]]["skip_reason"] = reason
            run["steps"][step["id"]]["order"] = len(run["ledger"]) + 1
            run["ledger"].append({
                "order": len(run["ledger"]) + 1,
                "step": step["id"],
                "action": "AUTO_SKIP",
                "reason": reason,
                "at": now()
            })
    return run


def require_keys(output, keys):
    if not isinstance(output, dict):
        raise WorkflowError("step output must be an object")
    missing = [k for k in keys if k not in output]
    if missing:
        raise WorkflowError(f"missing required output keys: {missing}")


def _nonempty_list(value):
    return isinstance(value, list) and len(value) > 0


def finite_number(value):
    return type(value) in (int, float) and math.isfinite(value)


# ---------- validators ----------
def validate_intake_route(output, run):
    if not valid_topics(output["selected_topics"]):
        return False, "invalid selected_topics"
    if set(output["selected_topics"]) != set(run["context"]["selected_topics"]):
        return False, "topics changed; initialize a new run with corrected domains"
    return True, "ok"


def validate_state_build(output, run):
    if not isinstance(output["family_state"], dict):
        return False, "family_state must be object"
    if not isinstance(output["source_tags"], dict):
        return False, "source_tags must be object"
    return True, "ok"


def validate_input_validate(output, run):
    if output["status"] not in ("READY","PARTIAL","BLOCKED"):
        return False, "invalid input status"
    if not isinstance(output["missing_p0"], list) or not isinstance(output["conflicts"], list):
        return False, "missing_p0/conflicts must be lists"
    return True, "ok"


def validate_deadlines(output, run):
    if not isinstance(output["deadlines"], list):
        return False, "deadlines must be list"
    if not isinstance(output["deadline_collision"], bool):
        return False, "deadline_collision must be bool"
    return True, "ok"


def validate_baseline(output, run):
    d = output["derived_metrics"]
    if not isinstance(d, dict):
        return False, "derived_metrics must be object"
    required = [
        "stable_income_annual","annual_spend","financial_assets",
        "total_debt","net_worth","runway_months","high_income_dependency"
    ]
    missing = [k for k in required if k not in d]
    if missing:
        return False, f"baseline missing metrics: {missing}"
    for key in required:
        value = d[key]
        if value is None and key in ("runway_months", "high_income_dependency"):
            continue
        if not finite_number(value) or (key != "net_worth" and value < 0):
            return False, f"invalid baseline metric: {key}"
    if d["high_income_dependency"] is not None and d["high_income_dependency"] > 1:
        return False, "high_income_dependency must be in 0..1 or null"
    if output["calculation_source"] not in ("REFERENCE_ENGINE","VERIFIED_TOOL"):
        return False, "critical baseline must come from deterministic/verified calculation"
    return True, "ok"


def validate_housing(output, run):
    topics = set(run["context"]["selected_topics"])
    results = output["results"]
    if not isinstance(results, dict):
        return False, "housing results must be object"
    if "HOUSING_EXISTING" in topics:
        if not results.get("target_home_considered", False):
            return False, "existing-home decision must consider target home"
        if not results.get("replacement_spread_checked", False):
            return False, "existing-home decision must check replacement spread"
    if "HOUSING_FIRST_BUY" in topics:
        if "post_purchase_liquid_assets" not in results:
            return False, "first-home analysis must show post-purchase liquid assets"
    return True, "ok"


def validate_education(output, run):
    scenarios = output["education_scenarios"]
    if not isinstance(scenarios, dict):
        return False, "education_scenarios must be object"
    for key in ("BASE","MID","HIGH"):
        if key not in scenarios:
            return False, f"education scenario missing {key}"
    return True, "ok"


def validate_career(output, run):
    scenarios = output["transition_scenarios"]
    if not isinstance(scenarios, list) or len(scenarios) < 2:
        return False, "career requires at least current + transition scenarios"
    if output["career_deadline"] in (None,""):
        return False, "career_deadline required"
    return True, "ok"


def validate_financing(output, run):
    if output["nominal_principal_checked"] is not True:
        return False, "nominal principal must be checked"
    if output["refinance_failure_tested"] is not True:
        results = output.get("results")
        reason = results.get("refinance_not_applicable_reason") if isinstance(results, dict) else None
        balloon = results.get("balloon_payment") if isinstance(results, dict) else None
        not_applicable = (
            output["refinance_failure_tested"] is False
            and output.get("refinance_required") is False
            and output.get("loan_structure") == "FULLY_AMORTIZING_FIXED_TERM"
            and finite_number(balloon) and balloon == 0
            and isinstance(reason, str) and bool(reason.strip()))
        if not not_applicable:
            return False, "test refinance failure or document a fully amortizing loan with no renewal/balloon"
    if output["compliance_status"] not in ("VERIFIED","REQUIRES_VERIFICATION","NOT_APPLICABLE"):
        return False, "invalid compliance_status"
    return True, "ok"


def validate_generic_domain(output, run):
    return True, "ok"


def validate_external_facts(output, run):
    if output["verification_status"] not in ("VERIFIED","PARTIAL","UNVERIFIED"):
        return False, "invalid verification_status"
    if output["verification_status"] != "VERIFIED" and output["conditionalized_if_unverified"] is not True:
        return False, "unverified external facts must be conditionalized"
    return True, "ok"


def validate_stress(output, run):
    scenarios = output["scenarios"]
    if not isinstance(scenarios, dict):
        return False, "scenarios must be object"
    for key in ("NORMAL","STRESS","SEVERE"):
        if key not in scenarios:
            return False, f"stress test missing {key}"
        scenario = scenarios[key]
        if not isinstance(scenario, dict):
            return False, f"{key} must be an object"
        for metric in ("income_annual", "spending_annual", "annual_net_cashflow"):
            if not finite_number(scenario.get(metric)):
                return False, f"{key} needs a finite {metric}"
        if scenario["income_annual"] < 0 or scenario["spending_annual"] < 0:
            return False, f"{key} income/spending cannot be negative"
        expected = scenario["income_annual"] - scenario["spending_annual"]
        if not math.isclose(scenario["annual_net_cashflow"], expected, rel_tol=1e-9, abs_tol=0.01):
            return False, f"{key} annual cashflow identity failed"
        if not isinstance(scenario.get("assumptions"), list):
            return False, f"{key} assumptions must be explicit"
    if not isinstance(output["material_failures"], list):
        return False, "material_failures must be a list"
    return True, "ok"


def validate_options_build(output, run):
    options = output["options"]
    if not isinstance(options, list) or len(options) < 2:
        return False, "need at least 2 comparable options"
    for i, option in enumerate(options):
        for key in ("id","label","tradeoffs","failure_triggers"):
            if key not in option:
                return False, f"option[{i}] missing {key}"
    return True, "ok"


def validate_options_validate(output, run):
    if not isinstance(output["critical_errors"], list):
        return False, "critical_errors must be list"
    if not isinstance(output["option_checks"], list):
        return False, "option_checks must be list"
    if output["all_options_validated"] is True and output["critical_errors"]:
        return False, "validated options cannot have critical errors"
    built = run["steps"]["OPTIONS_BUILD"]["output"] or {}
    expected = {x["id"] for x in built.get("options", [])}
    checks = output["option_checks"]
    if not all(isinstance(x, dict) and isinstance(x.get("id"), str)
               and type(x.get("pass")) is bool for x in checks):
        return False, "each option check needs id and boolean pass"
    actual = [x["id"] for x in checks]
    if len(actual) != len(set(actual)) or set(actual) != expected:
        return False, "option checks must cover every built option exactly once"
    if output["all_options_validated"] is True and any(not x["pass"] for x in checks):
        return False, "failed option cannot be marked fully validated"
    return True, "ok"


VALIDATORS = {k:v for k,v in globals().items() if k.startswith("validate_") and callable(v)}


def complete_step(run, step_id, output):
    wf = load_workflow()
    steps = step_map(wf)
    if step_id not in steps:
        raise WorkflowError(f"unknown step: {step_id}")
    step = steps[step_id]
    if step.get("system_managed"):
        raise WorkflowError(f"{step_id} is system-managed")
    state = run["steps"][step_id]
    if state["status"] == "SKIPPED":
        raise WorkflowError(f"{step_id} was auto-skipped as inapplicable")
    if state["status"] == "COMPLETE":
        raise WorkflowError(f"{step_id} already complete")

    ok, reason = applicable(step, run)
    if not ok:
        raise WorkflowError(f"{step_id} is not applicable: {reason}")

    ok, reason = prereqs_satisfied(step, run)
    if not ok:
        raise WorkflowError(f"cannot execute {step_id}: {reason}")

    require_keys(output, step["required_output_keys"])
    validation_results = []
    for name in step["validators"]:
        fn = VALIDATORS[name]
        valid, detail = fn(output, run)
        validation_results.append({"validator": name, "pass": valid, "detail": detail})
        if not valid:
            raise WorkflowError(f"{step_id} validation failed: {name}: {detail}")

    state["status"] = "COMPLETE"
    state["output"] = copy.deepcopy(output)
    state["validation"] = validation_results
    state["order"] = len(run["ledger"]) + 1
    run["ledger"].append({
        "order": len(run["ledger"]) + 1,
        "step": step_id,
        "action": "COMPLETE",
        "validation": validation_results,
        "at": now()
    })
    # Save a lightweight snapshot of statuses after each valid completion.
    run.setdefault("snapshots", []).append({
        "after_step": step_id,
        "statuses": {k:v["status"] for k,v in run["steps"].items()},
        "ledger_length": len(run["ledger"]),
        "at": now()
    })
    return run


def manual_skip(run, step_id, reason):
    ensure_run_spec(run)
    wf = load_workflow()
    steps = step_map(wf)
    if step_id not in steps:
        raise WorkflowError(f"unknown step: {step_id}")
    step = steps[step_id]
    ok, auto_reason = applicable(step, run)
    if ok:
        raise WorkflowError(f"cannot skip applicable step {step_id}")
    if run["steps"][step_id]["status"] == "SKIPPED":
        return run
    run["steps"][step_id]["status"] = "SKIPPED"
    run["steps"][step_id]["skip_reason"] = reason or auto_reason
    return run


def next_steps(run):
    ensure_run_spec(run)
    wf = load_workflow()
    available = []
    blocked = []
    for step in wf["steps"]:
        sid = step["id"]
        status = run["steps"][sid]["status"]
        if status not in ("PENDING", "STALE"):
            continue
        if step.get("system_managed"):
            continue
        ok, reason = applicable(step, run)
        if not ok:
            continue
        pre, why = prereqs_satisfied(step, run)
        if pre:
            available.append(sid)
        else:
            blocked.append({"step": sid, "reason": why})
    return {"available": available, "blocked": blocked}



def record_integrity_result(run, step_id, result):
    ensure_run_spec(run)
    if step_id not in run["steps"]:
        raise WorkflowError(f"unknown step for integrity: {step_id}")
    if run["steps"][step_id]["status"] != "COMPLETE":
        raise WorkflowError("integrity results require a completed current step")
    if not isinstance(result, dict) or not isinstance(result.get("integrity"), dict):
        raise WorkflowError("missing integrity result")
    expected_domain = {
        "BASELINE_CALCULATE": "baseline", "HOUSING_ANALYSIS": "housing",
        "FINANCING_ANALYSIS": "financing", "EDUCATION_ANALYSIS": "education",
        "CAREER_ANALYSIS": "career"}.get(step_id)
    if expected_domain and result.get("domain") != expected_domain:
        raise WorkflowError(f"{step_id} requires {expected_domain} integrity evidence")
    integrity = result["integrity"]
    status = integrity.get("status")
    checks = result.get("cross_checks")
    if (status not in ("PASS", "WARN", "FAIL") or not isinstance(checks, list)
            or not isinstance(integrity.get("issues"), list)):
        raise WorkflowError("invalid integrity status/checks/issues")
    if status == "PASS" and (not checks or integrity["issues"]
                            or not all(isinstance(x, dict) and x.get("pass") is True for x in checks)):
        raise WorkflowError("PASS requires successful nonempty cross-checks and no issues")
    result = copy.deepcopy(result)
    # Recompute available baseline identities from the actual stored output,
    # rather than trusting an externally supplied PASS label.
    if step_id == "BASELINE_CALCULATE":
        metrics = run["steps"][step_id]["output"]["derived_metrics"]
        runtime = _load_integrity_module().validate("baseline", metrics)
        needed = {"total_assets", "total_debt", "net_worth", "stable_income_annual",
                  "annual_spend", "annual_surplus"}
        if needed - set(metrics) and runtime["integrity"]["status"] != "FAIL":
            runtime["integrity"] = {
                "status": "WARN", "confidence": "MEDIUM",
                "issues": ["baseline identities incomplete: " + ", ".join(sorted(needed - set(metrics)))]}
        result["runtime_verification"] = runtime
        result["cross_checks"].extend(runtime["cross_checks"])
        runtime_status = runtime["integrity"]["status"]
        if runtime_status == "FAIL":
            result["integrity"] = {
                "status": "FAIL", "confidence": "LOW",
                "issues": integrity["issues"] + runtime["integrity"]["issues"]}
        elif runtime_status == "WARN" and status == "PASS":
            result["integrity"] = runtime["integrity"]
    if status in ("WARN", "FAIL") and not result["integrity"]["issues"]:
        result["integrity"]["issues"] = ["integrity check did not pass"]
    current_digest = output_digest(run["steps"][step_id]["output"])
    if result.get("output_sha256", current_digest) != current_digest:
        raise WorkflowError("integrity result refers to a different output")
    result["output_sha256"] = current_digest
    clear_gates(run)
    run.setdefault("integrity_results", {})[step_id] = result
    run["ledger"].append({
        "order": len(run["ledger"]) + 1,
        "step": step_id,
        "action": "INTEGRITY_CHECK",
        "result": result.get("integrity",{}).get("status"),
        "at": now()
    })
    if result.get("integrity",{}).get("status") == "FAIL":
        run["steps"][step_id]["status"] = "QUARANTINED"
    return run


def evaluate_integrity_gate(run):
    wf=load_workflow()
    steps=step_map(wf)
    gate_step=steps["INTEGRITY_GATE"]
    ok, reason=prereqs_satisfied(gate_step, run)
    if not ok:
        raise WorkflowError(f"integrity gate prerequisites not satisfied: {reason}")

    issues=[]
    conditional=[]
    quarantined=[]

    # Any applicable completed domain step with explicit integrity FAIL is blocked.
    for sid, result in run.get("integrity_results",{}).items():
        status=result.get("integrity",{}).get("status")
        if result.get("output_sha256") != output_digest(run["steps"][sid]["output"]):
            issues.append(f"stale integrity check for {sid}")
        if status not in ("PASS", "WARN", "FAIL"):
            issues.append(f"invalid integrity status for {sid}")
        if status=="FAIL":
            issues.extend([f"{sid}: {x}" for x in result.get("integrity",{}).get("issues",[])])
            quarantined.append(sid)
        elif status=="WARN":
            conditional.extend([f"{sid}: {x}" for x in result.get("integrity",{}).get("issues",[])])

    # Critical deterministic steps require an integrity result.
    critical=["BASELINE_CALCULATE"]
    topics=set(run["context"].get("selected_topics",[]))
    if topics.intersection({"HOUSING_EXISTING","HOUSING_FIRST_BUY"}):
        critical.append("HOUSING_ANALYSIS")
    if "FINANCING" in topics:
        critical.append("FINANCING_ANALYSIS")
    if "EDUCATION" in topics:
        critical.append("EDUCATION_ANALYSIS")
    if topics.intersection({"CAREER","SPOUSE_BREAK"}):
        critical.append("CAREER_ANALYSIS")

    for sid in critical:
        if run["steps"][sid]["status"]=="COMPLETE" and sid not in run.get("integrity_results",{}):
            issues.append(f"missing integrity check for critical step {sid}")

    # External facts can cause conditional integrity.
    ext=run["steps"]["EXTERNAL_FACT_CHECK"]
    if ext["status"]=="COMPLETE":
        o=ext["output"]
        if o.get("verification_status")!="VERIFIED":
            conditional.append("external facts are not fully verified")

    if issues:
        status="BLOCKED"
    elif conditional:
        status="CONDITIONAL_PASS"
    else:
        status="PASS"

    output={
        "status":status,
        "issues":issues,
        "conditional_constraints":conditional,
        "quarantined_steps":quarantined
    }
    run["steps"]["INTEGRITY_GATE"]["status"]="COMPLETE"
    run["steps"]["INTEGRITY_GATE"]["output"]=output
    run["steps"]["INTEGRITY_GATE"]["order"]=len(run["ledger"])+1
    run["integrity_gate"]=output
    run["ledger"].append({
        "order":len(run["ledger"])+1,
        "step":"INTEGRITY_GATE",
        "action":"INTEGRITY_GATE",
        "result":status,
        "issues":issues,
        "conditional_constraints":conditional,
        "at":now()
    })
    return run


def rollback_steps(run, step_ids, reason):
    ensure_run_spec(run)
    if not isinstance(step_ids, list) or any(sid not in run["steps"] for sid in step_ids):
        raise WorkflowError("rollback requires a list of known step ids")
    # Traverse actual workflow dependencies, not only the caller's partial list.
    targets = set(step_ids)
    changed = True
    while changed:
        changed = False
        for step in load_workflow()["steps"]:
            if step["id"] not in targets and targets.intersection(step["requires"]):
                targets.add(step["id"])
                changed = True
    affected=[]
    for sid in sorted(targets):
        run.get("integrity_results", {}).pop(sid, None)
        if run["steps"][sid]["status"] in ("COMPLETE","QUARANTINED"):
            run["steps"][sid]["status"]="STALE"
            affected.append(sid)
    clear_gates(run)
    run["ledger"].append({
        "order":len(run["ledger"])+1,
        "step":"SYSTEM",
        "action":"ROLLBACK_INVALIDATE",
        "affected":affected,
        "reason":reason,
        "at":now()
    })
    return run


def evaluate_gate(run):
    wf = load_workflow()
    steps = step_map(wf)
    gate_step = steps["RECOMMENDATION_GATE"]
    ok, reason = prereqs_satisfied(gate_step, run)
    if not ok:
        raise WorkflowError(f"gate prerequisites not satisfied: {reason}")

    reasons = []
    conditional = []

    integrity_gate = run.get("integrity_gate")
    if not integrity_gate:
        reasons.append("Integrity Gate has not run")
    elif integrity_gate.get("status") == "BLOCKED":
        reasons.append(f"Integrity Gate blocked: {integrity_gate.get('issues', [])}")
    elif integrity_gate.get("status") == "CONDITIONAL_PASS":
        conditional.extend(integrity_gate.get("conditional_constraints", []))
    elif integrity_gate.get("status") != "PASS":
        reasons.append("Integrity Gate has an invalid status")

    # Every applicable non-system pre-gate step must be complete.
    for step in wf["steps"]:
        sid = step["id"]
        if sid in ("RECOMMENDATION_GATE","FINALIZE"):
            continue
        app, _ = applicable(step, run)
        status = run["steps"][sid]["status"]
        if app and status != "COMPLETE":
            reasons.append(f"applicable step {sid} is {status}")

    iv = run["steps"]["INPUT_VALIDATE"]["output"] or {}
    if iv.get("status") == "BLOCKED":
        reasons.append("input validation is BLOCKED")
    unresolved_p0 = list(iv.get("missing_p0", []))
    conflicts = list(iv.get("conflicts", []))
    if conflicts:
        reasons.append(f"input conflicts unresolved: {conflicts}")
    if unresolved_p0:
        reasons.append(f"P0 inputs unresolved: {unresolved_p0}")

    ov = run["steps"]["OPTIONS_VALIDATE"]["output"] or {}
    if ov.get("all_options_validated") is not True:
        reasons.append("options are not fully validated")
    if ov.get("critical_errors"):
        reasons.append(f"critical option errors: {ov['critical_errors']}")

    financing = run["steps"]["FINANCING_ANALYSIS"]
    if (financing["status"] == "COMPLETE"
            and financing["output"].get("compliance_status") == "REQUIRES_VERIFICATION"):
        conditional.append("financing contract/compliance must be verified before execution")

    ext = run["steps"]["EXTERNAL_FACT_CHECK"]
    if ext["status"] == "COMPLETE":
        exto = ext["output"]
        if exto.get("verification_status") != "VERIFIED":
            if exto.get("conditionalized_if_unverified") is True:
                conditional.append("external facts not fully verified; final answer must remain conditional")
            else:
                reasons.append("external facts unverified and not conditionalized")

    if reasons:
        status = "BLOCKED"
    elif conditional:
        status = "CONDITIONAL_PASS"
    else:
        status = "PASS"

    output = {
        "status": status,
        "reasons": reasons,
        "unresolved_p0": unresolved_p0,
        "conditional_constraints": conditional,
    }
    run["steps"]["RECOMMENDATION_GATE"]["status"] = "COMPLETE"
    run["steps"]["RECOMMENDATION_GATE"]["output"] = output
    run["steps"]["RECOMMENDATION_GATE"]["order"] = len(run["ledger"]) + 1
    run["gate"] = output
    run["ledger"].append({
        "order": len(run["ledger"]) + 1,
        "step": "RECOMMENDATION_GATE",
        "action": "GATE",
        "result": status,
        "reasons": reasons,
        "conditional_constraints": conditional,
        "at": now()
    })
    return run


def finalize(run, output):
    gate = run.get("gate")
    if not gate:
        raise WorkflowError("Recommendation Gate has not run")
    # Re-evaluate freshness immediately before delivery, even if a cached gate
    # passed before an input/result was edited.
    evaluate_integrity_gate(run)
    evaluate_gate(run)
    gate = run["gate"]
    if gate["status"] not in ("PASS","CONDITIONAL_PASS"):
        raise WorkflowError(f"cannot finalize: gate is {gate['status']}")
    if gate["status"] == "CONDITIONAL_PASS":
        if output.get("final_output_mode") != "CONDITIONAL":
            raise WorkflowError("CONDITIONAL_PASS requires final_output_mode=CONDITIONAL")
        if not output.get("conditional_constraints_acknowledged"):
            raise WorkflowError("conditional constraints must be acknowledged")

    require_keys(output, ["final_output_mode","decision_summary"])
    run["steps"]["FINALIZE"]["status"] = "COMPLETE"
    run["steps"]["FINALIZE"]["output"] = output
    run["steps"]["FINALIZE"]["order"] = len(run["ledger"]) + 1
    run["ledger"].append({
        "order": len(run["ledger"]) + 1,
        "step": "FINALIZE",
        "action": "FINALIZE",
        "mode": output["final_output_mode"],
        "at": now()
    })
    return run


def cli():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("init")
    p.add_argument("input_json")
    p.add_argument("run_json")

    p = sub.add_parser("next")
    p.add_argument("run_json")

    p = sub.add_parser("complete")
    p.add_argument("run_json")
    p.add_argument("step")
    p.add_argument("output_json")

    p = sub.add_parser("skip")
    p.add_argument("run_json")
    p.add_argument("step")
    p.add_argument("--reason", default="not_applicable")

    p = sub.add_parser("integrity-gate")
    p.add_argument("run_json")

    p = sub.add_parser("integrity-record")
    p.add_argument("run_json")
    p.add_argument("step")
    p.add_argument("integrity_json")

    p = sub.add_parser("rollback")
    p.add_argument("run_json")
    p.add_argument("steps_json")
    p.add_argument("--reason", default="upstream_correction")

    p = sub.add_parser("gate")
    p.add_argument("run_json")

    p = sub.add_parser("finalize")
    p.add_argument("run_json")
    p.add_argument("output_json")

    p = sub.add_parser("ledger")
    p.add_argument("run_json")

    args = parser.parse_args()

    try:
        if args.cmd == "init":
            run = init_run(load_json(args.input_json))
            save_json(args.run_json, run)
            print(json.dumps(next_steps(run), ensure_ascii=False, indent=2))
        elif args.cmd == "next":
            run = load_json(args.run_json)
            print(json.dumps(next_steps(run), ensure_ascii=False, indent=2))
        elif args.cmd == "complete":
            run = load_json(args.run_json)
            run = complete_step(run, args.step, load_json(args.output_json))
            save_json(args.run_json, run)
            print(json.dumps(next_steps(run), ensure_ascii=False, indent=2))
        elif args.cmd == "skip":
            run = load_json(args.run_json)
            run = manual_skip(run, args.step, args.reason)
            save_json(args.run_json, run)
            print(json.dumps(next_steps(run), ensure_ascii=False, indent=2))
        elif args.cmd == "integrity-gate":
            run = load_json(args.run_json)
            run = evaluate_integrity_gate(run)
            save_json(args.run_json, run)
            print(json.dumps(run["integrity_gate"], ensure_ascii=False, indent=2))
        elif args.cmd == "integrity-record":
            run = load_json(args.run_json)
            result = load_json(args.integrity_json)
            run = record_integrity_result(run, args.step, result)
            save_json(args.run_json, run)
            print(json.dumps({"status":"RECORDED","step":args.step}, ensure_ascii=False, indent=2))
        elif args.cmd == "rollback":
            run = load_json(args.run_json)
            step_ids = load_json(args.steps_json)
            run = rollback_steps(run, step_ids, args.reason)
            save_json(args.run_json, run)
            print(json.dumps({"status":"ROLLED_BACK","affected":step_ids}, ensure_ascii=False, indent=2))
        elif args.cmd == "gate":
            run = load_json(args.run_json)
            run = evaluate_gate(run)
            save_json(args.run_json, run)
            print(json.dumps(run["gate"], ensure_ascii=False, indent=2))
        elif args.cmd == "finalize":
            run = load_json(args.run_json)
            run = finalize(run, load_json(args.output_json))
            save_json(args.run_json, run)
            print(json.dumps({"status":"FINALIZED","gate":run["gate"]["status"]}, ensure_ascii=False, indent=2))
        elif args.cmd == "ledger":
            run = load_json(args.run_json)
            print(json.dumps(run["ledger"], ensure_ascii=False, indent=2))
    except WorkflowError as e:
        print(json.dumps({"status":"ERROR","error":str(e)}, ensure_ascii=False, indent=2))
        raise SystemExit(2)


if __name__ == "__main__":
    cli()
