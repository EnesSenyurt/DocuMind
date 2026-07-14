import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.fixture
def test_settings(tmp_path) -> Settings:
    return Settings(environment="test", data_dir=tmp_path / "data")


@pytest.fixture
def client(test_settings: Settings):
    app = create_app()
    app.dependency_overrides[get_settings] = lambda: test_settings
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()
