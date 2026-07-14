from app.core.config import Settings
from app.services.embeddings import HashingEmbedder
from app.services.retrieval.service import RetrievalService
from app.services.vector_store import VectorStore


def _build(threshold: float, top_k: int = 5) -> RetrievalService:
    embedder = HashingEmbedder()
    store = VectorStore(persist_dir=None)
    docs = {
        "d1": "python fastapi backend web framework",
        "d2": "chocolate cake dessert recipe baking",
        "d3": "python asyncio concurrency event loop",
    }
    ids = list(docs)
    texts = [docs[i] for i in ids]
    store.add(
        ids=ids,
        embeddings=embedder.embed_documents(texts),
        documents=texts,
        metadatas=[{"document_id": i, "filename": f"{i}.txt"} for i in ids],
    )
    settings = Settings(
        _env_file=None, retrieval_top_k=top_k, relevance_threshold=threshold
    )
    return RetrievalService(embedder, store, settings)


def test_retrieves_relevant_chunks_above_threshold():
    service = _build(threshold=0.1)
    results = service.retrieve("python web framework")
    assert results
    assert results[0].metadata["document_id"] == "d1"
    assert all(r.score >= 0.1 for r in results)


def test_returns_empty_when_nothing_clears_threshold():
    # An impossibly high threshold filters everything out -> "no info" path.
    service = _build(threshold=0.99)
    assert service.retrieve("python web framework") == []


def test_unrelated_query_filtered_out_at_default_threshold():
    service = _build(threshold=0.25)
    assert service.retrieve("quantum astrophysics telescope") == []


def test_respects_top_k_override():
    service = _build(threshold=0.0, top_k=5)
    results = service.retrieve("python", top_k=1)
    assert len(results) == 1
