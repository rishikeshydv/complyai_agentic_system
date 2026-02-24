from __future__ import annotations

from pathlib import Path

import yaml

from connector.config import settings


def load_allowlist() -> dict[str, list[str]]:
    path: Path = settings.resolved_allowlist_path
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("allowlist", {})
