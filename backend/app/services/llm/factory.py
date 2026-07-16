"""Select and construct the configured LLM provider."""

from __future__ import annotations

from app.core.config import Settings
from app.services.llm.anthropic import AnthropicProvider
from app.services.llm.base import LLMProvider
from app.services.llm.gemini import GeminiProvider
from app.services.llm.openai import OpenAIProvider


def build_llm_provider(settings: Settings) -> LLMProvider:
    common = {
        "model": settings.llm_model,
        "max_tokens": settings.llm_max_tokens,
        "temperature": settings.llm_temperature,
        "timeout_seconds": settings.llm_timeout_seconds,
    }
    if settings.llm_provider == "gemini":
        return GeminiProvider(
            api_key=settings.gemini_api_key,
            thinking_level=settings.gemini_thinking_level,
            **common,
        )
    if settings.llm_provider == "openai":
        return OpenAIProvider(api_key=settings.openai_api_key, **common)
    if settings.llm_provider == "anthropic":
        return AnthropicProvider(api_key=settings.anthropic_api_key, **common)
    raise ValueError(f"Unknown LLM provider: {settings.llm_provider!r}")
