"""End-to-end chat API tests. The ``client`` fixture injects a hashing embedder
and a FakeLLMProvider, so a real document is ingested and queried without any
model download or provider call."""

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.embeddings import HashingEmbedder
from app.services.llm.base import LLMError

_DOC = b"# FastAPI\n\nFastAPI is a modern Python web framework for building APIs quickly.\n"


def _upload(client) -> None:
    response = client.post(
        "/api/documents",
        files={"file": ("tech.md", _DOC, "text/markdown")},
    )
    assert response.status_code == 201


def test_chat_grounded_answer_with_citations(client):
    _upload(client)
    response = client.post(
        "/api/chat", json={"message": "What is FastAPI, the Python web framework?"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["conversation_id"]
    assert body["citations"]
    citation = body["citations"][0]
    assert citation["filename"] == "tech.md"
    assert citation["marker"] == 1
    assert "snippet" in citation


def test_chat_no_info_when_nothing_relevant(client):
    _upload(client)
    response = client.post(
        "/api/chat", json={"message": "Explain quantum astrophysics telescopes"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is False
    assert body["message"] == "I don't have information about this in your documents."
    assert body["citations"] == []


def test_chat_is_multi_turn(client):
    _upload(client)
    first = client.post("/api/chat", json={"message": "What is the FastAPI web framework?"})
    conv_id = first.json()["conversation_id"]
    second = client.post(
        "/api/chat",
        json={"message": "tell me more", "conversation_id": conv_id},
    )
    assert second.json()["conversation_id"] == conv_id

    detail = client.get(f"/api/conversations/{conv_id}")
    assert detail.status_code == 200
    roles = [m["role"] for m in detail.json()["messages"]]
    assert roles == ["user", "assistant", "user", "assistant"]


def test_conversation_listing_and_deletion(client):
    _upload(client)
    conv_id = client.post("/api/chat", json={"message": "What is FastAPI?"}).json()[
        "conversation_id"
    ]
    listing = client.get("/api/conversations").json()
    assert listing["total"] == 1
    assert listing["conversations"][0]["id"] == conv_id

    assert client.delete(f"/api/conversations/{conv_id}").status_code == 200
    assert client.get("/api/conversations").json()["total"] == 0
    assert client.get(f"/api/conversations/{conv_id}").status_code == 404


def test_missing_message_is_rejected(client):
    assert client.post("/api/chat", json={"message": ""}).status_code == 422


def test_llm_failure_returns_502(test_settings):
    class RaisingLLM:
        model = "raising"

        async def generate(self, *, system, messages):
            raise LLMError("upstream unavailable")

    app = create_app(test_settings, embedder=HashingEmbedder(), llm_provider=RaisingLLM())
    with TestClient(app) as client:
        _upload(client)
        response = client.post("/api/chat", json={"message": "What is FastAPI framework?"})
    assert response.status_code == 502


def test_settings_fixture_available(test_settings: Settings):
    # Guard: the injected settings are isolated to a temp dir.
    assert test_settings.environment == "test"
