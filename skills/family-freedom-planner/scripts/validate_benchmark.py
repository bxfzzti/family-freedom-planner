#!/usr/bin/env python3
"""Validate benchmark_cases.json for v1.0 release gates."""
import json
import sys
from pathlib import Path

REQUIRED = {
    "id", "kind", "prompt", "expected_modules",
    "must", "must_not", "risk_tags", "difficulty"
}
VALID_KINDS = {"STANDARD", "COUNTERFACTUAL", "INVARIANCE"}
VALID_DIFFICULTY = {"BASIC", "INTERMEDIATE", "HARD"}

def validate(path):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    cases = data["cases"]
    errors = []
    ids = set()
    risk_tags = set()
    cf = 0
    inv = 0

    for i, case in enumerate(cases):
        missing = REQUIRED - set(case)
        if missing:
            errors.append(f"case[{i}] missing {sorted(missing)}")
        cid = case.get("id")
        if cid in ids:
            errors.append(f"duplicate id: {cid}")
        ids.add(cid)

        if case.get("kind") not in VALID_KINDS:
            errors.append(f"{cid}: invalid kind")
        if case.get("difficulty") not in VALID_DIFFICULTY:
            errors.append(f"{cid}: invalid difficulty")
        if not case.get("prompt"):
            errors.append(f"{cid}: empty prompt")
        if not case.get("must"):
            errors.append(f"{cid}: must is empty")
        if not case.get("must_not"):
            errors.append(f"{cid}: must_not is empty")
        risk_tags.update(case.get("risk_tags", []))
        cf += case.get("kind") == "COUNTERFACTUAL"
        inv += case.get("kind") == "INVARIANCE"

    if len(cases) < 25:
        errors.append("need at least 25 cases")
    if len(risk_tags) < 10:
        errors.append("need at least 10 unique risk tags")
    if cf < 5:
        errors.append("need at least 5 counterfactual cases")
    if inv < 3:
        errors.append("need at least 3 invariance cases")

    return {
        "case_count": len(cases),
        "unique_ids": len(ids),
        "unique_risk_tags": len(risk_tags),
        "counterfactual_cases": cf,
        "invariance_cases": inv,
        "errors": errors,
        "status": "PASS" if not errors else "FAIL"
    }

if __name__ == "__main__":
    result = validate(sys.argv[1])
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
