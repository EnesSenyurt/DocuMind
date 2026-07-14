import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app
from app.services.embeddings import HashingEmbedder


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
def client(test_settings: Settings):
    # Inject a deterministic embedder so tests need neither torch nor a download.
    app = create_app(test_settings, embedder=HashingEmbedder())
    with TestClient(app) as client:
        yield client
