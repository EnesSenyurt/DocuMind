import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.embeddings import HashingEmbedder
from app.services.llm.base import FakeLLMProvider


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(
        _env_file=None,
        environment="test",
        data_dir=tmp_path / "data",
        chunk_size=200,
        chunk_overlap=40,
    )


@pytest.fixture
def fake_llm() -> FakeLLMProvider:
    return FakeLLMProvider()


@pytest.fixture
def client(test_settings: Settings, fake_llm: FakeLLMProvider):
    # Inject a deterministic embedder and a fake LLM so tests need neither torch,
    # a model download, nor a real provider API call.
    app = create_app(test_settings, embedder=HashingEmbedder(), llm_provider=fake_llm)
    with TestClient(app) as client:
        yield client
