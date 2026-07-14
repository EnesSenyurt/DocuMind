"""Chat orchestration: retrieve -> (guard) -> prompt -> LLM -> persist.

Ties retrieval, the LLM provider, and conversation history together into a
single async ``chat`` call and enforces the grounding guarantee: if nothing
clears the relevance threshold, the LLM is never called and a fixed "no
information" answer is returned instead of a possible hallucination.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass

from app.core.config import Settings
from app.services.conversations import ConversationRepository
from app.services.llm.base import LLMMessage, LLMProvider
from app.services.llm.prompt import (
    NO_INFO_MESSAGE,
    build_system_prompt,
    build_user_prompt,
)
from app.services.retrieval.service import RetrievalService
from app.services.vector_store import RetrievedChunk

logger = logging.getLogger(__name__)


@dataclass
class ChatResult:
    conversation_id: str
    message: str
    citations: list[dict]
    grounded: bool


class ChatService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        llm_provider: LLMProvider,
        conversation_repo: ConversationRepository,
        settings: Settings,
    ) -> None:
        self._retrieval = retrieval_service
        self._llm = llm_provider
        self._conversations = conversation_repo
        self._settings = settings

    async def chat(self, message: str, conversation_id: str | None = None) -> ChatResult:
        conversation_id = conversation_id or uuid.uuid4().hex
        self._conversations.ensure_conversation(conversation_id)

        # History for the prompt must be the turns *before* this one.
        history = self._conversations.recent_messages(
            conversation_id, limit=self._settings.max_history_messages
        )

        # Retrieval is CPU/IO-bound (embedding + Chroma); keep the loop free.
        chunks = await asyncio.to_thread(self._retrieval.retrieve, message)

        self._conversations.add_message(conversation_id, "user", message)

        if not chunks:
            # Grounding guard: no relevant context -> do not call the LLM.
            logger.info("No relevant context for %s; returning guard.", conversation_id)
            self._conversations.add_message(conversation_id, "assistant", NO_INFO_MESSAGE)
            return ChatResult(
                conversation_id=conversation_id,
                message=NO_INFO_MESSAGE,
                citations=[],
                grounded=False,
            )

        llm_messages = [LLMMessage(role=m.role, content=m.content) for m in history]
        llm_messages.append(LLMMessage(role="user", content=build_user_prompt(message, chunks)))

        answer = await self._llm.generate(
            system=build_system_prompt(), messages=llm_messages
        )
        citations = _build_citations(chunks)
        self._conversations.add_message(
            conversation_id, "assistant", answer, citations=citations
        )
        return ChatResult(
            conversation_id=conversation_id,
            message=answer,
            citations=citations,
            grounded=True,
        )


def _build_citations(chunks: list[RetrievedChunk]) -> list[dict]:
    citations: list[dict] = []
    for marker, chunk in enumerate(chunks, start=1):
        metadata = chunk.metadata
        citations.append(
            {
                "marker": marker,
                "document_id": metadata.get("document_id", ""),
                "filename": metadata.get("filename", "unknown"),
                "page": metadata.get("page"),
                "section": metadata.get("section"),
                "score": round(chunk.score, 4),
                "snippet": chunk.text,
            }
        )
    return citations
