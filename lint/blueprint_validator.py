#!/usr/bin/env python3
"""
Blueprint Registry Validator

Validates registry/capabilities.json for:
- Valid JSON syntax
- Correct top-level structure (object with capabilities array)
- Required fields present on every capability entry
- No duplicate capability IDs
- No duplicate capability names
- Sorted by ID for deterministic output

Exit codes:
  0 — validation passed
  1 — validation failed (details printed to stderr)
"""

import json
import sys
from pathlib import Path

REQUIRED_FIELDS = {"id", "name", "description", "language", "module", "type", "function"}
OPTIONAL_FIELDS = set()
VALID_LANGUAGES = {"python", "javascript", "typescript", "shell"}

def validate_registry(path: Path) -> list[str]:
    errors = []

    if not path.exists():
        errors.append(f"Registry file not found: {path}")
        return errors

    try:
        with path.open("r", encoding="utf-8") as f:
            raw = f.read()
    except Exception as e:
        errors.append(f"Failed to read {path}: {e}")
        return errors

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        errors.append(f"Invalid JSON in {path}: {e}")
        return errors

    if not isinstance(data, dict):
        errors.append("Top-level value must be a JSON object")
        return errors

    if "capabilities" not in data:
        errors.append("Missing 'capabilities' key in registry")
        return errors

    caps = data["capabilities"]
    if not isinstance(caps, list):
        errors.append("'capabilities' must be an array")
        return errors

    seen_ids = set()
    seen_names = set()

    for i, cap in enumerate(caps):
        prefix = f"capabilities[{i}]"

        if not isinstance(cap, dict):
            errors.append(f"{prefix}: entry must be an object, got {type(cap).__name__}")
            continue

        for field in REQUIRED_FIELDS:
            if field not in cap:
                errors.append(f"{prefix}: missing required field '{field}'")
            elif not isinstance(cap[field], str) or not cap[field].strip():
                errors.append(f"{prefix}: field '{field}' must be a non-empty string")

        cap_id = cap.get("id", "")
        if cap_id:
            if cap_id in seen_ids:
                errors.append(f"{prefix}: duplicate id '{cap_id}'")
            seen_ids.add(cap_id)

        cap_name = cap.get("name", "")
        if cap_name:
            if cap_name in seen_names:
                errors.append(f"{prefix}: duplicate name '{cap_name}'")
            seen_names.add(cap_name)

        lang = cap.get("language", "")
        if lang and lang not in VALID_LANGUAGES:
            errors.append(f"{prefix}: unknown language '{lang}' (expected one of {sorted(VALID_LANGUAGES)})")

        unknown_fields = set(cap.keys()) - REQUIRED_FIELDS - OPTIONAL_FIELDS
        if unknown_fields:
            errors.append(f"{prefix}: unexpected fields {sorted(unknown_fields)}")

    ids_list = [c.get("id", "") for c in caps if isinstance(c, dict)]
    if ids_list != sorted(ids_list):
        errors.append("Capabilities are not sorted by 'id'. Run blueprint_update_github.py to fix.")

    return errors


def main() -> None:
    repo_root = Path(__file__).resolve().parent.parent
    registry_path = repo_root / "registry" / "capabilities.json"

    print(f"Validating: {registry_path}")
    errors = validate_registry(registry_path)

    if errors:
        print(f"\nFAILED — {len(errors)} error(s) found:\n", file=sys.stderr)
        for err in errors:
            print(f"  ✗ {err}", file=sys.stderr)
        sys.exit(1)
    else:
        caps_count = 0
        try:
            with registry_path.open() as f:
                caps_count = len(json.load(f).get("capabilities", []))
        except Exception:
            pass
        print(f"PASSED — {caps_count} capabilities validated, no errors.")
        sys.exit(0)


if __name__ == "__main__":
    main()
