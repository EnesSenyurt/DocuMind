"""LLM provider interface and shared HTTP plumbing.

The chat layer depends only on the ``LLMProvider`` protocol, so providers
(Gemini, OpenAI, Anthropic) are interchangeable via config and tests can inject
a fake. Each concrete provider talks to its vendor's HTTP API directly, which
keeps dependencies light and the surface easy to reason about.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Protocol, runtime_checkable

import httpx

Role = Literal["user", "assistant"]


@dataclass
class LLMMessage:
    role: Role
    content: str


class LLMError(Exception):
    """Raised when a provider call fails (network, timeout, bad status, or an
    unparseable/empty response). The API layer maps this to a 502."""


@runtime_checkable
class LLMProvider(Protocol):
    model: str

    async def generate(self, *, system: str, messages: list[LLMMessage]) -> str:
        ...


class HttpLLMProvider:
    """Base for HTTP-based providers: one JSON POST with uniform error handling."""

    def __init__(self, *, model: str, timeout_seconds: float) -> None:
        self.model = model
        self._timeout = timeout_seconds

    async def _post_json(
        self,
        url: str,
        *,
        json: dict,
        headers: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                response = await client.post(url, json=json, headers=headers, params=params)
        except httpx.HTTPError as exc:
            raise LLMError(f"request to {self.__class__.__name__} failed: {exc}") from exc

        if response.status_code >= 400:
            # Surface a trimmed body to aid debugging without dumping everything.
            raise LLMError(
                f"{self.__class__.__name__} returned {response.status_code}: "
                f"{response.text[:300]}"
            )
        try:
            return response.json()
        except ValueError as exc:
            raise LLMError(f"{self.__class__.__name__} returned non-JSON response") from exc


class FakeLLMProvider:
    """Deterministic in-memory provider for tests.

    Records every call so tests can assert the no-info guard skipped the LLM and
    that retrieved context is passed as data in the final user message.
    """

    def __init__(self, response: str = "Grounded answer from your documents [1].") -> None:
        self.model = "fake"
        self._response = response
        self.calls: list[dict] = []

    async def generate(self, *, system: str, messages: list[LLMMessage]) -> str:
        self.calls.append({"system": system, "messages": messages})
        return self._response
