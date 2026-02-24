from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from core.config import settings


def _env_for(dir_name: str) -> Environment:
    base: Path = settings.shared_root / dir_name
    return Environment(loader=FileSystemLoader(str(base)), autoescape=False, trim_blocks=True, lstrip_blocks=True)


def render_prompt(template_name: str, context: dict) -> str:
    env = _env_for("prompts")
    return env.get_template(template_name).render(**context)


def render_markdown(template_name: str, context: dict) -> str:
    env = _env_for("templates")
    return env.get_template(template_name).render(**context)
