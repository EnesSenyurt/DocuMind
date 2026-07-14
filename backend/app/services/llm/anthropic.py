"""Anthropic Messages API provider."""

from __future__ import annotations

from app.services.llm.base import HttpLLMProvider, LLMError, LLMMessage

_URL = "https://api.anthropic.com/v1/messages"
_API_VERSION = "2023-06-01"


class AnthropicProvider(HttpLLMProvider):
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        max_tokens: int,
        temperature: float,
        timeout_seconds: float,
    ) -> None:
        super().__init__(model=model, timeout_seconds=timeout_seconds)
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._temperature = temperature

    async def generate(self, *, system: str, messages: list[LLMMessage]) -> str:
        if not self._api_key:
            raise LLMError("ANTHROPIC_API_KEY is not configured")

        payload = {
            "model": self.model,
            "system": system,
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        data = await self._post_json(
            _URL,
            json=payload,
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": _API_VERSION,
                "content-type": "application/json",
            },
        )
        blocks = data.get("content") or []
        text = "".join(
            block.get("text", "") for block in blocks if block.get("type") == "text"
        ).strip()
        if not text:
            raise LLMError("Anthropic returned an empty completion")
        return text
