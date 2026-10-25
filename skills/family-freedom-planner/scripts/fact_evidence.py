"""Validate evidence metadata offline; this does not certify source truth."""
from datetime import date, datetime, timezone
from urllib.parse import urlparse


def evaluate(output, today=None, expected_region=None):
    today = today or datetime.now(timezone.utc).date()
    facts = output.get("facts")
    if not isinstance(facts, list) or not all(isinstance(x, dict) for x in facts):
        return {"status": "UNVERIFIED", "issues": ["facts must be a list of evidence objects"]}
    if not facts:
        return {"status": "UNVERIFIED", "issues": ["no external evidence supplied"]}
    issues = []
    identifiers = set()
    for index, fact in enumerate(facts):
        prefix = f"fact[{index}]"
        for key in ("id", "region", "source", "verification_method", "as_of", "valid_until"):
            if not isinstance(fact.get(key), str) or not fact[key].strip():
                issues.append(f"{prefix}: missing {key}")
        if "value" not in fact or fact["value"] is None:
            issues.append(f"{prefix}: missing value")
        if expected_region is not None and fact.get("region") != expected_region:
            issues.append(f"{prefix}: evidence region does not match decision region")
        fid = fact.get("id")
        if isinstance(fid, str):
            if fid in identifiers:
                issues.append(f"{prefix}: duplicate id")
            identifiers.add(fid)
        if fact.get("source_type") not in ("OFFICIAL", "BANK_DOCUMENT"):
            issues.append(f"{prefix}: source must be official or an inspected bank document")
        source = fact.get("source", "")
        if fact.get("source_type") == "OFFICIAL":
            parsed = urlparse(source) if isinstance(source, str) else None
            if not parsed or parsed.scheme != "https" or not parsed.netloc:
                issues.append(f"{prefix}: official source needs an HTTPS URL")
        try:
            as_of = date.fromisoformat(fact["as_of"])
            until = date.fromisoformat(fact["valid_until"])
            if as_of > today or until < today or until < as_of:
                issues.append(f"{prefix}: future, expired or reversed evidence dates")
            maximum_age = 30 if fact.get("kind") in ("price", "rate") else 365
            if (today - as_of).days > maximum_age:
                issues.append(f"{prefix}: refresh evidence before this decision")
        except (KeyError, TypeError, ValueError):
            issues.append(f"{prefix}: invalid evidence date")
    return {"status": "PARTIAL" if issues else "VERIFIED", "issues": issues,
            "scope": "metadata_and_freshness_only"}
