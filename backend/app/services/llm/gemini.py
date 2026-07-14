"""Gemini (Google Generative Language API) provider."""

from __future__ import annotations

from app.services.llm.base import HttpLLMProvider, LLMError, LLMMessage

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiProvider(HttpLLMProvider):
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
            raise LLMError("GEMINI_API_KEY is not configured")

        contents = [
            {
                # Gemini uses "model" for the assistant role.
                "role": "model" if message.role == "assistant" else "user",
                "parts": [{"text": message.content}],
            }
            for message in messages
        ]
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": self._max_tokens,
                "temperature": self._temperature,
            },
        }
        data = await self._post_json(
            f"{_BASE_URL}/{self.model}:generateContent",
            json=payload,
            params={"key": self._api_key},
        )
        return _extract_text(data)


def _extract_text(data: dict) -> str:
    candidates = data.get("candidates") or []
    if not candidates:
        feedback = data.get("promptFeedback", {})
        raise LLMError(f"Gemini returned no candidates (feedback: {feedback})")
    parts = candidates[0].get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()
    if not text:
        raise LLMError("Gemini returned an empty completion")
    return text
