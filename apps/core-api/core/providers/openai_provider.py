from __future__ import annotations

from typing import Any

from core.providers.base import LLMProvider


class OpenAIProvider(LLMProvider):
    @property
    def provider_name(self) -> str:
        return "openai"

    @property
    def model_name(self) -> str:
        return "openai-placeholder"

    def generate_json(self, task: str, rendered_prompt: str, context: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("OpenAI provider is a placeholder in this local build")
