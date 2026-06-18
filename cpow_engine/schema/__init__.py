"""JSON schema validation — stdlib only (no jsonschema dependency)."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_SCHEMA_PATH = Path(__file__).resolve().parents[1] / "config" / "cpow_schema.json"


@dataclass
class ValidationError:
    path: str
    message: str

    def __str__(self) -> str:
        return f"{self.path}: {self.message}"


@dataclass
class ValidationResult:
    ok: bool
    errors: list[ValidationError] = field(default_factory=list)


def _type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int) and not isinstance(value, bool):
        return "integer"
    if isinstance(value, float):
        return "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, list):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def _check_type(value: Any, expected: str | list[str], path: str) -> list[ValidationError]:
    if isinstance(expected, list):
        for option in expected:
            errs = _check_type(value, option, path)
            if not errs:
                return []
        return [ValidationError(path, f"expected one of {expected}, got {_type_name(value)}")]
    actual = _type_name(value)
    if expected == "number" and actual == "integer":
        return []
    if actual != expected:
        return [ValidationError(path, f"expected {expected}, got {actual}")]
    return []


def _validate_node(
    value: Any,
    schema: dict[str, Any],
    path: str,
    root: dict[str, Any],
) -> list[ValidationError]:
    errors: list[ValidationError] = []

    if "$ref" in schema:
        ref = schema["$ref"]
        if not ref.startswith("#/"):
            errors.append(ValidationError(path, f"unsupported ref {ref}"))
            return errors
        parts = ref.lstrip("#/").split("/")
        node: Any = root
        for part in parts:
            node = node[part]
        return _validate_node(value, node, path, root)

    if "oneOf" in schema:
        branches = schema["oneOf"]
        branch_errors: list[list[ValidationError]] = []
        for branch in branches:
            errs = _validate_node(value, branch, path, root)
            if not errs:
                return []
            branch_errors.append(errs)
        return branch_errors[0] if branch_errors else []

    expected_type = schema.get("type")
    if expected_type:
        errors.extend(_check_type(value, expected_type, path))
        if errors:
            return errors

    if isinstance(value, dict):
        props = schema.get("properties", {})
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(ValidationError(f"{path}.{key}", "required field missing"))
        if schema.get("additionalProperties") is False:
            for key in value:
                if key not in props:
                    errors.append(
                        ValidationError(f"{path}.{key}", "additional property not allowed")
                    )
        for key, subschema in props.items():
            if key in value:
                errors.extend(
                    _validate_node(value[key], subschema, f"{path}.{key}", root)
                )

    if isinstance(value, list) and "items" in schema:
        item_schema = schema["items"]
        for i, item in enumerate(value):
            errors.extend(
                _validate_node(item, item_schema, f"{path}[{i}]", root)
            )

    if isinstance(value, str):
        if "minLength" in schema and len(value) < int(schema["minLength"]):
            errors.append(
                ValidationError(path, f"minLength {schema['minLength']} not met")
            )
        if "enum" in schema and value not in schema["enum"]:
            errors.append(ValidationError(path, f"not in enum {schema['enum']}"))

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            errors.append(ValidationError(path, f"below minimum {schema['minimum']}"))

    return errors


class SchemaValidator:
    """Validate CPoW payloads against cpow_schema.json definitions."""

    def __init__(self, schema_path: Path | None = None) -> None:
        path = schema_path or _SCHEMA_PATH
        with path.open(encoding="utf-8") as fh:
            self._schema = json.load(fh)

    def validate(self, data: dict[str, Any], definition: str) -> ValidationResult:
        defs = self._schema.get("definitions", {})
        if definition not in defs:
            return ValidationResult(
                ok=False,
                errors=[ValidationError("$", f"unknown definition {definition}")],
            )
        errors = _validate_node(data, defs[definition], "$", self._schema)
        return ValidationResult(ok=not errors, errors=errors)

    def validate_creative_object(self, data: dict[str, Any]) -> ValidationResult:
        return self.validate(data, "CreativeObject")

    def validate_action_record(self, data: dict[str, Any]) -> ValidationResult:
        return self.validate(data, "ActionRecord")

    def validate_world_delta(self, data: dict[str, Any]) -> ValidationResult:
        return self.validate(data, "WorldDelta")


def validate_creative_object(data: dict[str, Any]) -> ValidationResult:
    return SchemaValidator().validate_creative_object(data)
