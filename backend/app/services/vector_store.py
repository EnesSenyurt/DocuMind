"""ChromaDB-backed vector store (embedded mode).

Wraps a single Chroma collection. Embeddings are always supplied explicitly by
the caller (never computed by Chroma's default embedding function), which keeps
the choice of embedding model in one place and avoids Chroma pulling its own
model at runtime.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from pathlib import Path

import chromadb
from chromadb.config import Settings as ChromaSettings


@dataclass
class RetrievedChunk:
    """A chunk returned from a similarity search, with a normalized score."""

    id: str
    text: str
    metadata: dict
    score: float  # cosine similarity in [0, 1]; higher is more relevant


class VectorStore:
    def __init__(
        self,
        persist_dir: Path | str | None = None,
        collection_name: str | None = None,
    ) -> None:
        # EphemeralClient shares in-process state, so give each ephemeral store a
        # unique collection to keep throwaway/test instances isolated. Persistent
        # stores keep a stable name so the same data is found across restarts.
        if collection_name is None:
            collection_name = (
                "documind" if persist_dir is not None else f"documind_{uuid.uuid4().hex}"
            )

        chroma_settings = ChromaSettings(anonymized_telemetry=False, allow_reset=True)
        if persist_dir is None:
            self._client = chromadb.EphemeralClient(settings=chroma_settings)
        else:
            Path(persist_dir).mkdir(parents=True, exist_ok=True)
            self._client = chromadb.PersistentClient(
                path=str(persist_dir), settings=chroma_settings
            )
        # Cosine space so distance = 1 - cosine_similarity for normalized vectors.
        self._collection = self._client.get_or_create_collection(
            name=collection_name, metadata={"hnsw:space": "cosine"}
        )

    def add(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        documents: list[str],
        metadatas: list[dict],
    ) -> None:
        if not ids:
            return
        self._collection.add(
            ids=ids, embeddings=embeddings, documents=documents, metadatas=metadatas
        )

    def query(
        self,
        query_embedding: list[float],
        top_k: int,
        where: dict | None = None,
    ) -> list[RetrievedChunk]:
        if self._collection.count() == 0:
            return []
        result = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self._collection.count()),
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result["ids"][0]
        documents = result["documents"][0]
        metadatas = result["metadatas"][0]
        distances = result["distances"][0]

        chunks: list[RetrievedChunk] = []
        for cid, text, metadata, distance in zip(
            ids, documents, metadatas, distances, strict=True
        ):
            similarity = max(0.0, min(1.0, 1.0 - float(distance)))
            chunks.append(
                RetrievedChunk(id=cid, text=text, metadata=dict(metadata), score=similarity)
            )
        return chunks

    def delete_document(self, document_id: str) -> None:
        self._collection.delete(where={"document_id": document_id})

    def count(self) -> int:
        return self._collection.count()
