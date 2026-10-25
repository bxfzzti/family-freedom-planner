"""Execute the JSON Schema subset used by this bundle; no third-party runtime."""
import json
import math
import re
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"


def validate(value, schema, path="$"):
    errors = []
    if "$ref" in schema:
        ref = schema["$ref"]
        target = (ASSETS / ref).resolve()
        if target.parent != ASSETS or not target.is_file():
            return [f"{path}: unsupported schema reference"]
        return validate(value, json.loads(target.read_text(encoding="utf-8")), path)
    types = schema.get("type")
    if types:
        types = [types] if isinstance(types, str) else types
        matches = {
            "object": isinstance(value, dict), "array": isinstance(value, list),
            "string": isinstance(value, str), "boolean": type(value) is bool,
            "null": value is None,
            "number": type(value) in (int, float) and math.isfinite(value),
            "integer": type(value) is int}
        if not any(matches.get(t, False) for t in types):
            return [f"{path}: expected {'/'.join(types)}"]
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        errors.append(f"{path}: wrong constant")
    if "enum" in schema and not any(type(value) is type(x) and value == x for x in schema["enum"]):
        errors.append(f"{path}: invalid enum value")
    if type(value) in (int, float):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(f"{path}: below minimum")
        if "maximum" in schema and value > schema["maximum"]:
            errors.append(f"{path}: above maximum")
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0):
            errors.append(f"{path}: string too short")
        if "pattern" in schema and re.fullmatch(schema["pattern"], value) is None:
            errors.append(f"{path}: invalid format")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        for key in schema.get("required", []):
            if key not in value:
                errors.append(f"{path}.{key}: required")
        for key, item in value.items():
            if not isinstance(key, str):
                errors.append(f"{path}: object keys must be strings")
                continue
            rule = properties.get(key, schema.get("additionalProperties", True))
            if rule is False:
                errors.append(f"{path}.{key}: unknown field")
            elif isinstance(rule, dict):
                errors.extend(validate(item, rule, f"{path}.{key}"))
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0) or len(value) > schema.get("maxItems", float("inf")):
            errors.append(f"{path}: invalid array length")
        if schema.get("uniqueItems"):
            seen = set()
            for item in value:
                encoded = json.dumps(item, sort_keys=True, ensure_ascii=False)
                if encoded in seen:
                    errors.append(f"{path}: duplicate item")
                seen.add(encoded)
        if isinstance(schema.get("items"), dict):
            for index, item in enumerate(value):
                errors.extend(validate(item, schema["items"], f"{path}[{index}]"))
    return errors


def validate_named(value, name):
    return validate(value, json.loads((ASSETS / name).read_text(encoding="utf-8")))
