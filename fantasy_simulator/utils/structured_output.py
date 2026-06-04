"""Extract and validate JSON structured output from LLM responses."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

from utils.io_helpers import load_json


class StructuredOutputError(ValueError):
    def __init__(self, message: str, *, raw: str = "", errors: list[str] | None = None) -> None:
        super().__init__(message)
        self.raw = raw
        self.errors = errors or []


_JSON_BLOCK_RE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL | re.IGNORECASE)
_JSON_OBJECT_RE = re.compile(r"\{.*\}", re.DOTALL)


def extract_json_object(text: str) -> dict[str, Any]:
    """Pull the first JSON object from raw LLM text."""
    stripped = text.strip()
    if not stripped:
        raise StructuredOutputError("Empty response", raw=text)

    try:
        parsed = json.loads(stripped)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass

    block = _JSON_BLOCK_RE.search(stripped)
    if block:
        try:
            parsed = json.loads(block.group(1))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError:
            pass

    obj = _JSON_OBJECT_RE.search(stripped)
    if obj:
        try:
            parsed = json.loads(obj.group(0))
            if isinstance(parsed, dict):
                return parsed
        except json.JSONDecodeError as exc:
            raise StructuredOutputError(f"Invalid JSON object: {exc}", raw=text) from exc

    raise StructuredOutputError("No JSON object found in response", raw=text)


def validate_schema(data: dict[str, Any], schema: dict[str, Any], path: str = "") -> list[str]:
    """Minimal JSON Schema validator (subset sufficient for our schemas)."""
    errors: list[str] = []

    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(data, dict):
            return [f"{path or 'root'}: expected object, got {type(data).__name__}"]
        if schema.get("additionalProperties") is False:
            allowed = set(schema.get("properties", {}).keys())
            for key in data:
                if key not in allowed:
                    errors.append(f"{path}.{key}: additional property not allowed")
        for req in schema.get("required", []):
            if req not in data:
                errors.append(f"{path}.{req}: required field missing")
        for key, subschema in schema.get("properties", {}).items():
            if key in data:
                errors.extend(validate_schema(data[key], subschema, f"{path}.{key}" if path else key))
    elif expected_type == "array":
        if not isinstance(data, list):
            return [f"{path or 'root'}: expected array, got {type(data).__name__}"]
        item_schema = schema.get("items")
        if item_schema:
            for i, item in enumerate(data):
                errors.extend(validate_schema(item, item_schema, f"{path}[{i}]"))
    elif expected_type == "string":
        if not isinstance(data, str):
            errors.append(f"{path}: expected string, got {type(data).__name__}")
        enum = schema.get("enum")
        if enum and data not in enum:
            errors.append(f"{path}: value '{data}' not in enum {enum}")
    elif expected_type == "integer":
        if not isinstance(data, int) or isinstance(data, bool):
            errors.append(f"{path}: expected integer, got {type(data).__name__}")
        else:
            if "minimum" in schema and data < schema["minimum"]:
                errors.append(f"{path}: {data} < minimum {schema['minimum']}")
    elif expected_type == "number":
        if not isinstance(data, (int, float)) or isinstance(data, bool):
            errors.append(f"{path}: expected number, got {type(data).__name__}")
        else:
            if "minimum" in schema and data < schema["minimum"]:
                errors.append(f"{path}: {data} < minimum {schema['minimum']}")
            if "maximum" in schema and data > schema["maximum"]:
                errors.append(f"{path}: {data} > maximum {schema['maximum']}")

    return errors


@dataclass
class StructuredOutputClient:
    schemas_dir: Any
    max_retries: int = 3
    repair_on_failure: bool = True

    def load_schema(self, name: str) -> dict[str, Any]:
        path = self.schemas_dir / f"{name}.json"
        return load_json(path)

    def parse_and_validate(self, text: str, schema_name: str) -> dict[str, Any]:
        schema = self.load_schema(schema_name)
        data = extract_json_object(text)
        errors = validate_schema(data, schema)
        if errors:
            raise StructuredOutputError(
                "Schema validation failed",
                raw=text,
                errors=errors,
            )
        return data

    def build_repair_prompt(self, schema_name: str, raw: str, errors: list[str]) -> str:
        schema = self.load_schema(schema_name)
        err_text = "\n".join(f"- {e}" for e in errors)
        return (
            "Your previous response was invalid.\n"
            f"Errors:\n{err_text}\n\n"
            "Return ONLY a corrected JSON object matching this schema:\n"
            f"{json.dumps(schema, ensure_ascii=False, indent=2)}\n\n"
            f"Previous response:\n{raw[:2000]}"
        )
