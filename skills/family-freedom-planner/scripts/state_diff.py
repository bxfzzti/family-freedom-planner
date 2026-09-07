#!/usr/bin/env python3
"""Compare two Family Context Capsules and emit a compact delta.

Standard-library only.
"""
import argparse
import json
from pathlib import Path

MISSING = object()


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            out.update(flatten(value, path))
    elif isinstance(obj, list):
        out[prefix] = obj
    else:
        out[prefix] = obj
    return out


def diff(old, new):
    a, b = flatten(old), flatten(new)
    changes = []
    for key in sorted(set(a) | set(b)):
        av = a.get(key, MISSING)
        bv = b.get(key, MISSING)
        if av == bv:
            continue
        if av is MISSING:
            kind = "ADDED"
            old_value = None
            new_value = bv
        elif bv is MISSING:
            kind = "REMOVED"
            old_value = av
            new_value = None
        else:
            kind = "CHANGED"
            old_value = av
            new_value = bv
        changes.append({
            "path": key,
            "change_type": kind,
            "old": old_value,
            "new": new_value,
        })
    return changes


def classify(path):
    if path.startswith("income."):
        return "INCOME_CHANGE"
    if path.startswith("expenses."):
        return "EXPENSE_CHANGE"
    if path.startswith("assets."):
        return "ASSET_CHANGE"
    if path.startswith("housing."):
        return "HOUSING_PRICE_CHANGE"
    if path.startswith("debts."):
        return "DEBT_CHANGE"
    if path.startswith("career."):
        return "CAREER_CHANGE"
    if path.startswith("education."):
        return "EDUCATION_CHANGE"
    if path.startswith("preferences."):
        return "PREFERENCE_CHANGE"
    if path.startswith("goals"):
        return "NEW_GOAL_OR_GOAL_CHANGE"
    return "OTHER_CHANGE"


def summarize(old, new):
    changes = diff(old, new)
    for item in changes:
        item["delta_type"] = classify(item["path"])
    return {
        "change_count": len(changes),
        "changes": changes
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old_json")
    parser.add_argument("new_json")
    args = parser.parse_args()
    old = json.loads(Path(args.old_json).read_text(encoding="utf-8"))
    new = json.loads(Path(args.new_json).read_text(encoding="utf-8"))
    print(json.dumps(summarize(old, new), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
