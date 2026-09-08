#!/usr/bin/env python3
"""Check this downloaded Skill bundle without changing files or calling a model.

PASS verifies package files and a local calculation, not host auto-activation.
"""
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def check(root=ROOT):
    root = Path(root).resolve()
    issues = []
    required = [
        "SKILL.md", "workflow.yaml", "assets/workflow.compiled.json",
        "scripts/family_freedom_engine.py", "scripts/workflow_orchestrator.py",
        "scripts/integrity_engine.py", "scripts/intake_router.py",
        "scripts/decision_cashflow.py", "scripts/state_diff.py"]
    for relative in required:
        if not (root / relative).is_file():
            issues.append(f"missing file: {relative}")
    entry = root / "SKILL.md"
    if entry.is_file():
        content = entry.read_text(encoding="utf-8")
        if not re.search(r"^name:\s*family-freedom-planner\s*$", content, re.M):
            issues.append("unexpected Skill name")
        for relative in re.findall(r"\]\((references/[^)]+\.md)\)", content):
            candidate = (root / relative).resolve()
            if root not in candidate.parents or not candidate.is_file():
                issues.append(f"missing or outside-bundle reference: {relative}")
    workflow_version = None
    spec_hash = None
    if (root / "assets/workflow.compiled.json").is_file():
        try:
            spec = json.loads((root / "assets/workflow.compiled.json").read_text(encoding="utf-8"))
            workflow_version = spec.get("version")
            spec_hash = spec.pop("spec_hash", None)
            expected = hashlib.sha256(json.dumps(
                spec, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
            if expected != spec_hash:
                issues.append("workflow content/hash mismatch")
            yaml = (root / "workflow.yaml").read_text(encoding="utf-8")
            if f"spec_hash: {spec_hash}" not in yaml:
                issues.append("workflow YAML/hash mismatch")
        except (ValueError, OSError, TypeError, AttributeError) as exc:
            issues.append(f"invalid workflow: {exc}")
    smoke = "NOT_RUN"
    if not issues:
        try:
            command = [sys.executable, str(root / "scripts/family_freedom_engine.py"),
                       "mortgage", "--principal", "120000", "--annual-rate", "0", "--years", "10"]
            process = subprocess.run(command, capture_output=True, text=True, timeout=10)
            output = json.loads(process.stdout)
            if process.returncode != 0 or output.get("monthly_payment") != 1000:
                issues.append("zero-rate mortgage smoke calculation failed")
                smoke = "FAIL"
            else:
                smoke = "PASS"
        except (ValueError, OSError, subprocess.TimeoutExpired, AttributeError):
            issues.append("calculation script could not run")
            smoke = "FAIL"
    return {"status": "FAIL" if issues else "PASS",
            "scope": "installed_bundle_and_local_calculation",
            "workflow_version": workflow_version, "workflow_spec_hash": spec_hash,
            "calculation_smoke": smoke, "host_auto_activation": "NOT_TESTED",
            "network_fact_verification": "NOT_TESTED", "issues": issues}


if __name__ == "__main__":
    result = check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(0 if result["status"] == "PASS" else 1)
