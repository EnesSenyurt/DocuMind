"""Unit tests for the ingestion orchestrator, wired with real (lightweight)
extractors + chunker + an ephemeral Chroma store + the hashing embedder."""

import pytest

from app.services.documents import DocumentRepository
from app.services.embeddings import HashingEmbedder
from app.services.errors import EmptyDocumentError, UnsupportedFileTypeError
from app.services.ingestion.chunker import RecursiveCharacterChunker
from app.services.ingestion.service import IngestionService
from app.services.vector_store import VectorStore


@pytest.fixture
def service(tmp_path):
    return IngestionService(
        chunker=RecursiveCharacterChunker(chunk_size=120, chunk_overlap=20),
        embedder=HashingEmbedder(),
        vector_store=VectorStore(persist_dir=None),
        repository=DocumentRepository(tmp_path / "db.sqlite"),
    )


def test_ingest_stores_chunks_and_registers_document(service):
    text = ("Retrieval augmented generation grounds answers in documents. " * 20).encode()
    record = service.ingest("guide.txt", text)

    assert record.num_chunks > 1
    assert record.content_type == "text/plain"
    assert record.size_bytes == len(text)
    # Registered and retrievable.
    assert service.list_documents()[0].id == record.id


def test_ingest_rejects_unsupported_type(service):
    with pytest.raises(UnsupportedFileTypeError):
        service.ingest("data.csv", b"a,b,c\n1,2,3")


def test_ingest_rejects_empty_document(service):
    with pytest.raises(EmptyDocumentError):
        service.ingest("empty.txt", b"    \n\t  ")


def test_delete_document_removes_registry_and_vectors(service):
    record = service.ingest("doc.md", b"# Heading\n\nSome content here to embed.")
    assert service.delete_document(record.id) is True
    assert service.list_documents() == []
    # Deleting again is a no-op.
    assert service.delete_document(record.id) is False


def test_markdown_section_metadata_reaches_vector_store(service):
    md = b"# Alpha\n\nAlpha body text here.\n\n# Beta\n\nBeta body text here.\n"
    record = service.ingest("sections.md", md)
    results = service._vector_store.query(
        service._embedder.embed_query("Beta body"), top_k=5
    )
    sections = {r.metadata.get("section") for r in results}
    assert "Beta" in sections
    assert all(r.metadata["document_id"] == record.id for r in results)
