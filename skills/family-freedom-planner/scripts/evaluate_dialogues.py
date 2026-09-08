#!/usr/bin/env python3
"""Audit recorded Agent dialogues and explicit semantic reviews.

Does not call a model or infer correctness from keywords. A PASS means the
provided reviewer approved each criterion with evidence from the bound answer.
It cannot authenticate the reviewer or prove their judgments are correct.
"""
import argparse
import hashlib
import json
from pathlib import Path


def digest(value):
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True,
                   separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def indexed(rows, label):
    result = {}
    if not isinstance(rows, list):
        raise ValueError(f"{label} must be a list")
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{label} rows must be objects")
        key = row.get("id")
        if not isinstance(key, str) or not key.strip() or key in result:
            raise ValueError(f"{label} has missing/duplicate id: {key}")
        result[key] = row
    return result


def evaluate(suite, recordings, reviews):
    cases = indexed(suite["cases"], "cases")
    if not cases:
        raise ValueError("empty case suite")
    runs = indexed(recordings.get("cases", []), "recordings")
    judgments = indexed(reviews.get("cases", []), "reviews")
    if (set(runs) | set(judgments)) - set(cases):
        raise ValueError("unknown case id")
    meta = recordings.get("run", {})
    required_meta = ("model", "skill_revision", "recorded_at", "origin")
    complete_meta = all(isinstance(meta.get(k), str) and meta[k].strip()
                        for k in required_meta)
    complete_meta = complete_meta and meta.get("origin") in ("agent_run", "self_review")
    results = []
    for cid, case in cases.items():
        checks = case.get("criteria")
        prompts = case.get("user_turns")
        if (not isinstance(checks, dict) or not checks
                or not all(isinstance(k, str) and isinstance(v, str) and v.strip()
                           for k, v in checks.items())
                or not isinstance(prompts, list) or not prompts
                or not all(isinstance(p, str) and p.strip() for p in prompts)):
            raise ValueError(f"{cid}: invalid criteria/user_turns")
        issues = []
        failures = []
        run = runs.get(cid, {})
        turns = run.get("turns", [])
        valid_turns = isinstance(turns, list) and len(turns) == len(prompts)
        if valid_turns:
            valid_turns = all(
                isinstance(t, dict) and t.get("user") == p
                and isinstance(t.get("assistant"), str) and t["assistant"].strip()
                for t, p in zip(turns, prompts)
            )
        if not valid_turns:
            issues.append("missing answer or user turns do not match suite")
        review = judgments.get(cid, {})
        if review.get("transcript_sha256") != digest(turns):
            issues.append("missing or stale transcript binding")
        if review.get("case_sha256") != digest(case):
            issues.append("missing or stale case binding")
        if not isinstance(review.get("reviewer"), str) or not review["reviewer"].strip():
            issues.append("missing reviewer")
        grades = review.get("checks", {})
        if not isinstance(grades, dict):
            grades = {}
            issues.append("checks must be an object")
        if set(grades) - set(checks):
            raise ValueError(f"{cid}: unknown review criterion")
        for key in checks:
            grade = grades.get(key, {})
            if not isinstance(grade, dict):
                issues.append(f"{key}: malformed grade")
                continue
            verdict = grade.get("verdict")
            evidence = grade.get("evidence")
            turn_index = grade.get("turn")
            reason = grade.get("reason")
            valid_evidence = (
                valid_turns and type(turn_index) is int
                and 0 <= turn_index < len(turns)
                and isinstance(evidence, str) and bool(evidence.strip())
                and evidence in turns[turn_index]["assistant"]
                and isinstance(reason, str) and bool(reason.strip())
            )
            if verdict not in ("PASS", "FAIL") or not valid_evidence:
                issues.append(f"{key}: missing verdict or grounded evidence")
            elif verdict == "FAIL":
                failures.append(key)
        if not complete_meta:
            issues.append("missing run provenance or unrecognized origin")
        status = "FAIL" if failures else "INCOMPLETE" if issues else "PASS"
        results.append({"id": cid, "status": status,
                        "failures": failures, "issues": issues})
    status = ("FAIL" if any(r["status"] == "FAIL" for r in results)
              else "INCOMPLETE" if any(r["status"] == "INCOMPLETE" for r in results)
              else "PASS")
    return {"status": status, "evaluation_scope": "reviewed_recorded_dialogues",
            "origin": meta.get("origin"), "run": meta,
            "case_count": len(cases), "results": results,
            "limits": "Checks review completeness and evidence binding; does not independently verify semantic judgments."}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite")
    parser.add_argument("recordings")
    parser.add_argument("reviews")
    args = parser.parse_args()
    try:
        result = evaluate(*(json.loads(Path(p).read_text(encoding="utf-8"))
                            for p in (args.suite, args.recordings, args.reviews)))
    except (ValueError, KeyError, TypeError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit({"PASS": 0, "FAIL": 1, "INCOMPLETE": 2}[result["status"]])


if __name__ == "__main__":
    main()
