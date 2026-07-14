"""Embedding models behind a small interface.

The rest of the app depends only on the ``EmbeddingModel`` protocol, so the
concrete backend (sentence-transformers today) is swappable and tests can
inject a lightweight deterministic embedder instead of downloading a model.
"""

from __future__ import annotations

import hashlib
import math
from typing import Protocol, runtime_checkable

from app.core.config import Settings


@runtime_checkable
class EmbeddingModel(Protocol):
    @property
    def dimension(self) -> int:
        ...

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        ...

    def embed_query(self, text: str) -> list[float]:
        ...


class SentenceTransformerEmbedder:
    """sentence-transformers backend (default: all-MiniLM-L6-v2).

    The model is loaded lazily on first use so that importing this module — and
    constructing the embedder at app startup — stays cheap and offline.
    Embeddings are L2-normalized so cosine similarity reduces to a dot product.
    """

    def __init__(self, model_name: str) -> None:
        self._model_name = model_name
        self._model = None

    def _ensure_model(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self._model_name)
        return self._model

    @property
    def dimension(self) -> int:
        return int(self._ensure_model().get_sentence_embedding_dimension())

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        model = self._ensure_model()
        vectors = model.encode(
            texts,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return vectors.tolist()

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class HashingEmbedder:
    """Deterministic, dependency-free embedder for tests and offline use.

    Hashes tokens into a fixed number of buckets (a bag-of-words hashing trick)
    and L2-normalizes. It is not semantically strong, but texts that share words
    land close together, which is enough to exercise retrieval logic without
    torch or a model download.
    """

    def __init__(self, dimension: int = 128) -> None:
        self._dimension = dimension

    @property
    def dimension(self) -> int:
        return self._dimension

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self._dimension
        for token in text.lower().split():
            bucket = int(hashlib.md5(token.encode()).hexdigest(), 16) % self._dimension
            vec[bucket] += 1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


def build_embedder(settings: Settings) -> EmbeddingModel:
    """Construct the configured embedding backend."""
    return SentenceTransformerEmbedder(settings.embedding_model)
