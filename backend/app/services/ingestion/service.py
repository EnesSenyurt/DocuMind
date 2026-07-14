"""Ingestion orchestration: extract -> chunk -> embed -> store.

Ties the pieces together and records one row per document in the registry. All
methods are synchronous and CPU/IO-bound; the API layer runs them in a thread
pool so the event loop stays responsive.
"""

from __future__ import annotations

import logging
import uuid

from app.services.documents import DocumentRecord, DocumentRepository, utcnow
from app.services.embeddings import EmbeddingModel
from app.services.errors import EmptyDocumentError
from app.services.ingestion.chunker import Chunk, RecursiveCharacterChunker
from app.services.ingestion.extractors import extract_segments, resolve_content_type
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


class IngestionService:
    def __init__(
        self,
        chunker: RecursiveCharacterChunker,
        embedder: EmbeddingModel,
        vector_store: VectorStore,
        repository: DocumentRepository,
    ) -> None:
        self._chunker = chunker
        self._embedder = embedder
        self._vector_store = vector_store
        self._repository = repository

    def ingest(self, filename: str, data: bytes) -> DocumentRecord:
        # Raises UnsupportedFileTypeError for unknown extensions.
        content_type = resolve_content_type(filename)

        segments = extract_segments(filename, data)
        chunks = self._chunker.chunk_segments(segments)
        if not chunks:
            raise EmptyDocumentError(filename)

        document_id = uuid.uuid4().hex
        embeddings = self._embedder.embed_documents([chunk.text for chunk in chunks])

        ids = [f"{document_id}:{chunk.index}" for chunk in chunks]
        metadatas = [self._metadata(document_id, filename, chunk) for chunk in chunks]
        documents = [chunk.text for chunk in chunks]
        self._vector_store.add(ids, embeddings, documents, metadatas)

        pages = [segment.page for segment in segments if segment.page is not None]
        record = DocumentRecord(
            id=document_id,
            filename=filename,
            content_type=content_type,
            size_bytes=len(data),
            num_pages=max(pages) if pages else None,
            num_chunks=len(chunks),
            created_at=utcnow(),
        )
        self._repository.add(record)
        logger.info(
            "Ingested %r as %s (%d chunks, %s pages)",
            filename,
            document_id,
            len(chunks),
            record.num_pages if record.num_pages is not None else "n/a",
        )
        return record

    def list_documents(self) -> list[DocumentRecord]:
        return self._repository.list()

    def delete_document(self, document_id: str) -> bool:
        record = self._repository.get(document_id)
        if record is None:
            return False
        self._vector_store.delete_document(document_id)
        self._repository.delete(document_id)
        logger.info("Deleted document %s (%r)", document_id, record.filename)
        return True

    @staticmethod
    def _metadata(document_id: str, filename: str, chunk: Chunk) -> dict:
        # Chroma rejects None metadata values, so only include keys we actually have.
        metadata: dict = {
            "document_id": document_id,
            "filename": filename,
            "chunk_index": chunk.index,
        }
        if chunk.page is not None:
            metadata["page"] = chunk.page
        if chunk.section:
            metadata["section"] = chunk.section
        return metadata
