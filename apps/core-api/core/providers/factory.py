from core.config import settings
from core.providers.base import LLMProvider
from core.providers.mock_provider import MockLLMProvider
from core.providers.openai_provider import OpenAIProvider


def get_provider() -> LLMProvider:
    if settings.llm_provider.lower() == "openai":
        return OpenAIProvider()
    return MockLLMProvider()
