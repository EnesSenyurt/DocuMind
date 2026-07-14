"""Similarity search with a relevance-threshold gate.

Embeds the query, pulls the top-k nearest chunks from the vector store, then
drops anything below the configured similarity threshold. When everything is
below threshold the result is empty, which the chat layer treats as "no
relevant information" rather than sending weak context to the LLM.
"""

from __future__ import annotations

import logging

from app.core.config import Settings
from app.services.embeddings import EmbeddingModel
from app.services.vector_store import RetrievedChunk, VectorStore

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(
        self,
        embedder: EmbeddingModel,
        vector_store: VectorStore,
        settings: Settings,
    ) -> None:
        self._embedder = embedder
        self._vector_store = vector_store
        self._settings = settings

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        threshold: float | None = None,
    ) -> list[RetrievedChunk]:
        top_k = top_k if top_k is not None else self._settings.retrieval_top_k
        threshold = threshold if threshold is not None else self._settings.relevance_threshold

        query_embedding = self._embedder.embed_query(query)
        candidates = self._vector_store.query(query_embedding, top_k=top_k)
        relevant = [chunk for chunk in candidates if chunk.score >= threshold]

        logger.debug(
            "retrieval: query=%r candidates=%d relevant=%d (threshold=%.2f)",
            query,
            len(candidates),
            len(relevant),
            threshold,
        )
        return relevant
