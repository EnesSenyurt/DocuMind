"""OpenAI Chat Completions provider."""

from __future__ import annotations

from app.services.llm.base import HttpLLMProvider, LLMError, LLMMessage

_URL = "https://api.openai.com/v1/chat/completions"


class OpenAIProvider(HttpLLMProvider):
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
            raise LLMError("OPENAI_API_KEY is not configured")

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                *({"role": m.role, "content": m.content} for m in messages),
            ],
            "max_tokens": self._max_tokens,
            "temperature": self._temperature,
        }
        data = await self._post_json(
            _URL,
            json=payload,
            headers={"Authorization": f"Bearer {self._api_key}"},
        )
        choices = data.get("choices") or []
        if not choices:
            raise LLMError("OpenAI returned no choices")
        text = (choices[0].get("message", {}).get("content") or "").strip()
        if not text:
            raise LLMError("OpenAI returned an empty completion")
        return text
