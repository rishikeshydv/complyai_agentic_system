from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import ValidationError, validate

from core.config import settings


def schema_path(name: str) -> Path:
    return settings.shared_root / "schemas" / name


def load_schema(name: str) -> dict[str, Any]:
    with schema_path(name).open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_json(name: str, payload: dict[str, Any]) -> None:
    schema = load_schema(name)
    validate(instance=payload, schema=schema)


def is_valid(name: str, payload: dict[str, Any]) -> tuple[bool, str | None]:
    try:
        validate_json(name, payload)
        return True, None
    except ValidationError as exc:
        return False, exc.message
