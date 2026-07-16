"""Unit tests for the LLM provider abstraction — no network calls.

Each provider short-circuits with an LLMError when its API key is missing
(before any HTTP), so these exercise construction, the factory, and response
parsing without hitting a real endpoint.
"""

import pytest

from app.core.config import Settings
from app.services.llm.anthropic import AnthropicProvider
from app.services.llm.base import LLMError, LLMMessage
from app.services.llm.factory import build_llm_provider
from app.services.llm.gemini import GeminiProvider, _extract_text
from app.services.llm.openai import OpenAIProvider

_COMMON = {"model": "m", "max_tokens": 64, "temperature": 0.2, "timeout_seconds": 5.0}


async def test_gemini_missing_key_raises_before_network():
    provider = GeminiProvider(api_key="", **_COMMON)
    with pytest.raises(LLMError, match="GEMINI_API_KEY"):
        await provider.generate(system="s", messages=[LLMMessage("user", "hi")])


async def test_openai_missing_key_raises_before_network():
    provider = OpenAIProvider(api_key="", **_COMMON)
    with pytest.raises(LLMError, match="OPENAI_API_KEY"):
        await provider.generate(system="s", messages=[LLMMessage("user", "hi")])


async def test_anthropic_missing_key_raises_before_network():
    provider = AnthropicProvider(api_key="", **_COMMON)
    with pytest.raises(LLMError, match="ANTHROPIC_API_KEY"):
        await provider.generate(system="s", messages=[LLMMessage("user", "hi")])


def test_gemini_extract_text_happy_path():
    data = {"candidates": [{"content": {"parts": [{"text": "hello "}, {"text": "world"}]}}]}
    assert _extract_text(data) == "hello world"


def test_gemini_extract_text_no_candidates_raises():
    with pytest.raises(LLMError):
        _extract_text({"candidates": []})


def test_gemini_extract_text_empty_completion_raises():
    with pytest.raises(LLMError):
        _extract_text({"candidates": [{"content": {"parts": [{"text": "   "}]}}]})


def test_gemini_extract_text_max_tokens_empty_gives_actionable_error():
    data = {"candidates": [{"finishReason": "MAX_TOKENS", "content": {"parts": []}}]}
    with pytest.raises(LLMError, match="LLM_MAX_TOKENS"):
        _extract_text(data)


def test_gemini_extract_text_returns_partial_answer_on_truncation():
    data = {
        "candidates": [
            {"finishReason": "MAX_TOKENS", "content": {"parts": [{"text": "partial answer"}]}}
        ]
    }
    assert _extract_text(data) == "partial answer"


async def test_gemini_payload_includes_thinking_level_only_when_set(monkeypatch):
    captured = {}

    async def fake_post(self, url, *, json, headers=None, params=None):
        captured["json"] = json
        return {"candidates": [{"content": {"parts": [{"text": "ok"}]}}]}

    monkeypatch.setattr(GeminiProvider, "_post_json", fake_post)

    # With a thinking level configured -> present in generationConfig.
    provider = GeminiProvider(api_key="k", thinking_level="low", **_COMMON)
    await provider.generate(system="s", messages=[LLMMessage("user", "hi")])
    gen_cfg = captured["json"]["generationConfig"]
    assert gen_cfg["thinkingConfig"] == {"thinkingLevel": "low"}
    assert gen_cfg["maxOutputTokens"] == _COMMON["max_tokens"]

    # Default (empty) -> field omitted, so we never send an unsupported key.
    provider = GeminiProvider(api_key="k", **_COMMON)
    await provider.generate(system="s", messages=[LLMMessage("user", "hi")])
    assert "thinkingConfig" not in captured["json"]["generationConfig"]


@pytest.mark.parametrize(
    ("provider", "cls"),
    [
        ("gemini", GeminiProvider),
        ("openai", OpenAIProvider),
        ("anthropic", AnthropicProvider),
    ],
)
def test_factory_builds_configured_provider(provider, cls):
    settings = Settings(_env_file=None, llm_provider=provider, llm_model="x")
    built = build_llm_provider(settings)
    assert isinstance(built, cls)
    assert built.model == "x"
