"""Minimal JSON-schema-like validation for tool parameters."""

from __future__ import annotations

from typing import Any, Dict, List, Tuple


def validate_parameters(schema: Dict[str, Any], params: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Validate parameters against a minimal JSON schema subset."""
    errors: List[str] = []
    if not schema:
        return True, errors

    required = schema.get("required", []) or []
    for key in required:
        if key not in params:
            errors.append(f"Missing required parameter: {key}")

    properties = schema.get("properties", {}) or {}
    for key, spec in properties.items():
        if key not in params:
            continue
        expected = spec.get("type")
        if not expected:
            continue
        if not _matches_type(params[key], expected):
            errors.append(f"Invalid type for '{key}': expected {expected}")

    return (len(errors) == 0), errors


def _matches_type(value: Any, expected: str) -> bool:
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    return True
