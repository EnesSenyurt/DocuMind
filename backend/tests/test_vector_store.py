from app.services.embeddings import HashingEmbedder
from app.services.vector_store import VectorStore


def _seed(store: VectorStore, embedder: HashingEmbedder) -> None:
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
        metadatas=[{"document_id": i} for i in ids],
    )


def test_query_on_empty_store_returns_nothing():
    store = VectorStore(persist_dir=None)
    result = store.query([0.0] * 8, top_k=5)
    assert result == []


def test_query_ranks_relevant_chunks_first_with_bounded_scores():
    embedder = HashingEmbedder()
    store = VectorStore(persist_dir=None)
    _seed(store, embedder)

    results = store.query(embedder.embed_query("python web framework"), top_k=3)
    assert results
    # The FastAPI doc shares the most words with the query.
    assert results[0].id == "d1"
    # Scores are similarities in [0, 1], sorted descending.
    scores = [r.score for r in results]
    assert all(0.0 <= s <= 1.0 for s in scores)
    assert scores == sorted(scores, reverse=True)


def test_unrelated_query_scores_low():
    embedder = HashingEmbedder()
    store = VectorStore(persist_dir=None)
    _seed(store, embedder)

    results = store.query(embedder.embed_query("quantum astrophysics telescope"), top_k=3)
    # Nothing in the corpus is about this; top score should be modest.
    assert results[0].score < 0.5


def test_delete_document_removes_its_chunks():
    embedder = HashingEmbedder()
    store = VectorStore(persist_dir=None)
    _seed(store, embedder)
    assert store.count() == 3

    store.delete_document("d2")
    assert store.count() == 2
    remaining = {r.id for r in store.query(embedder.embed_query("recipe"), top_k=5)}
    assert "d2" not in remaining
