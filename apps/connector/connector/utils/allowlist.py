from __future__ import annotations

from typing import Any

MISSING = object()


def _set_nested_value(target: dict[str, Any], path: list[str], value: Any) -> None:
    current = target
    for key in path[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[path[-1]] = value


def _get_nested_value(data: dict[str, Any], path: list[str]) -> Any:
    current: Any = data
    for key in path:
        if not isinstance(current, dict) or key not in current:
            return MISSING
        current = current[key]
    return current


def filter_with_allowlist(data: dict[str, Any], allowlist_paths: list[str]) -> dict[str, Any]:
    if not allowlist_paths:
        return data

    filtered: dict[str, Any] = {}
    for raw_path in allowlist_paths:
        path = raw_path.split(".")
        value = _get_nested_value(data, path)
        if value is not MISSING:
            _set_nested_value(filtered, path, value)
    return filtered
