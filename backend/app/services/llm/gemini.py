"""Gemini (Google Generative Language API) provider."""

from __future__ import annotations

import logging

from app.services.llm.base import HttpLLMProvider, LLMError, LLMMessage

logger = logging.getLogger(__name__)

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
        thinking_level: str = "",
    ) -> None:
        super().__init__(model=model, timeout_seconds=timeout_seconds)
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._thinking_level = thinking_level

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
        generation_config: dict = {
            "maxOutputTokens": self._max_tokens,
            "temperature": self._temperature,
        }
        # Gemini 3.x only; omitted by default so we never send an unsupported field.
        if self._thinking_level:
            generation_config["thinkingConfig"] = {"thinkingLevel": self._thinking_level}

        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": generation_config,
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

    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    parts = candidate.get("content", {}).get("parts") or []
    text = "".join(part.get("text", "") for part in parts).strip()

    if not text:
        if finish_reason == "MAX_TOKENS":
            # Thinking consumed the whole budget before any answer was produced.
            raise LLMError(
                "Gemini hit the output token limit before returning an answer "
                "(thinking used the budget). Increase LLM_MAX_TOKENS."
            )
        raise LLMError(f"Gemini returned an empty completion (finishReason={finish_reason})")

    if finish_reason == "MAX_TOKENS":
        # Partial answer: usable, but warn so the token limit can be raised.
        logger.warning("Gemini answer truncated at token limit; consider raising LLM_MAX_TOKENS.")
    return text
