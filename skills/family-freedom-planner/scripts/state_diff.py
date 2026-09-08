#!/usr/bin/env python3
"""Compare two Family Context Capsules and emit a compact delta.

Standard-library only.
"""
import argparse
import json
from copy import deepcopy
from pathlib import Path

MISSING = object()


def flatten(obj, prefix=""):
    out = {}
    if isinstance(obj, dict):
        if not obj and prefix:
            out[prefix] = {}
        for key, value in obj.items():
            path = f"{prefix}.{key}" if prefix else key
            out.update(flatten(value, path))
    elif isinstance(obj, list):
        out[prefix] = obj
    else:
        out[prefix] = obj
    return out


def diff(old, new):
    if not isinstance(old, dict) or not isinstance(new, dict):
        raise ValueError("old/new context must be objects")
    a, b = flatten(old), flatten(new)
    changes = []
    for key in sorted(set(a) | set(b)):
        av = a.get(key, MISSING)
        bv = b.get(key, MISSING)
        if same_value(av, bv):
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


def same_value(a, b):
    # Python equates True and 1; a parser changing amount to boolean is a delta.
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    if isinstance(a, list) and isinstance(b, list):
        return len(a) == len(b) and all(same_value(x, y) for x, y in zip(a, b))
    if isinstance(a, dict) and isinstance(b, dict):
        return a.keys() == b.keys() and all(same_value(a[k], b[k]) for k in a)
    return a == b


def merge_update(old, update):
    """Missing fields preserve old state; explicit null means unknown, not delete.

    Lists replace the whole list. This is deliberately not JSON Merge Patch's
    null-deletion convention. Inputs are never mutated.
    """
    if not isinstance(old, dict) or not isinstance(update, dict):
        raise ValueError("context/update must be objects")
    merged = deepcopy(old)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = merge_update(merged[key], value)
        else:
            merged[key] = deepcopy(value)
    return merged


def classify(path):
    if path == "deadlines" or path.startswith("deadlines.") or "deadline" in path.split(".")[-1]:
        return "DEADLINE_CHANGE"
    if path == "housing.primary_home_debt":
        return "DEBT_CHANGE"
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


def summarize(old, new, mode="snapshot"):
    if mode not in ("snapshot", "update"):
        raise ValueError("mode must be snapshot or update")
    if mode == "update":
        new = merge_update(old, new)
    changes = diff(old, new)
    for item in changes:
        item["delta_type"] = classify(item["path"])
    return {
        "comparison_mode": mode,
        "change_count": len(changes),
        "changes": changes
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("old_json")
    parser.add_argument("new_json")
    parser.add_argument("--mode", choices=("snapshot", "update"), default="snapshot",
                        help="snapshot compares full states; update preserves unmentioned fields")
    args = parser.parse_args()
    old = json.loads(Path(args.old_json).read_text(encoding="utf-8"))
    new = json.loads(Path(args.new_json).read_text(encoding="utf-8"))
    print(json.dumps(summarize(old, new, args.mode), ensure_ascii=False, indent=2, allow_nan=False))


if __name__ == "__main__":
    try:
        main()
    except (ValueError, TypeError, OSError) as exc:
        print(json.dumps({"status": "ERROR", "error": str(exc)}, ensure_ascii=False))
        raise SystemExit(2)
