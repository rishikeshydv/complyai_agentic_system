from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import validate


def _schemas_root() -> Path:
    return Path(__file__).resolve().parents[4] / "packages" / "shared" / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    path = _schemas_root() / name
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def validate_against_schema(name: str, payload: dict[str, Any]) -> None:
    schema = load_schema(name)
    validate(instance=payload, schema=schema)
