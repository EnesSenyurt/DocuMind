import pytest

from app.core.config import Settings
from app.services.chat.service import ChatService
from app.services.conversations import ConversationRepository
from app.services.embeddings import HashingEmbedder
from app.services.llm.base import FakeLLMProvider, LLMError
from app.services.retrieval.service import RetrievalService
from app.services.vector_store import VectorStore


def _make_service(tmp_path, llm=None, threshold=0.1):
    embedder = HashingEmbedder()
    store = VectorStore(persist_dir=None)
    texts = [
        "python fastapi backend web framework for building apis",
        "chocolate cake dessert recipe baking sugar",
    ]
    store.add(
        ids=["d1:0", "d2:0"],
        embeddings=embedder.embed_documents(texts),
        documents=texts,
        metadatas=[
            {"document_id": "d1", "filename": "tech.md", "page": 1, "section": "Intro"},
            {"document_id": "d2", "filename": "food.md"},
        ],
    )
    settings = Settings(
        _env_file=None, data_dir=tmp_path / "d", relevance_threshold=threshold
    )
    retrieval = RetrievalService(embedder, store, settings)
    repo = ConversationRepository(tmp_path / "db.sqlite")
    return ChatService(retrieval, llm or FakeLLMProvider(), repo, settings), repo


async def test_grounded_answer_returns_citations(tmp_path):
    llm = FakeLLMProvider("FastAPI is a web framework [1].")
    service, _ = _make_service(tmp_path, llm=llm)
    result = await service.chat("What is FastAPI web framework?")

    assert result.grounded is True
    assert result.message == "FastAPI is a web framework [1]."
    assert result.citations
    top = result.citations[0]
    assert top["marker"] == 1
    assert top["document_id"] == "d1"
    assert top["filename"] == "tech.md"
    assert top["page"] == 1
    assert top["section"] == "Intro"
    assert 0.0 <= top["score"] <= 1.0


async def test_no_relevant_context_triggers_guard_without_calling_llm(tmp_path):
    llm = FakeLLMProvider()
    service, repo = _make_service(tmp_path, llm=llm, threshold=0.25)
    result = await service.chat("quantum astrophysics telescope orbit")

    assert result.grounded is False
    assert result.message == "I don't have information about this in your documents."
    assert result.citations == []
    # The LLM must not be invoked when nothing is relevant.
    assert llm.calls == []
    # The turn is still recorded.
    assert [m.role for m in repo.get_messages(result.conversation_id)] == ["user", "assistant"]


async def test_retrieved_context_passed_as_data_in_final_user_message(tmp_path):
    llm = FakeLLMProvider()
    service, _ = _make_service(tmp_path, llm=llm)
    await service.chat("python web framework")

    call = llm.calls[-1]
    final_user = call["messages"][-1]
    assert final_user.role == "user"
    assert "CONTEXT:" in final_user.content
    assert "QUESTION: python web framework" in final_user.content
    # System prompt carries the grounding + injection rules.
    assert "only" in call["system"].lower()


async def test_multi_turn_replays_history(tmp_path):
    llm = FakeLLMProvider()
    service, _ = _make_service(tmp_path, llm=llm)
    first = await service.chat("What is FastAPI web framework?")
    await service.chat("tell me more about it", conversation_id=first.conversation_id)

    # Second call should include the prior user+assistant turn before the new one.
    second_messages = llm.calls[-1]["messages"]
    assert len(second_messages) >= 3
    assert second_messages[0].content == "What is FastAPI web framework?"
    assert second_messages[0].role == "user"
    assert second_messages[1].role == "assistant"


async def test_same_conversation_id_is_reused(tmp_path):
    service, _ = _make_service(tmp_path)
    first = await service.chat("python web framework")
    second = await service.chat("python asyncio", conversation_id=first.conversation_id)
    assert first.conversation_id == second.conversation_id


async def test_llm_error_propagates(tmp_path):
    class RaisingLLM:
        model = "raising"

        async def generate(self, *, system, messages):
            raise LLMError("boom")

    service, _ = _make_service(tmp_path, llm=RaisingLLM())
    with pytest.raises(LLMError):
        await service.chat("python web framework")
