from pathlib import Path

from app.core.config import Settings


def test_defaults_are_sane():
    settings = Settings(_env_file=None)
    assert settings.chunk_overlap < settings.chunk_size
    assert 0.0 <= settings.relevance_threshold <= 1.0
    assert settings.llm_provider == "gemini"


def test_env_overrides(monkeypatch):
    monkeypatch.setenv("CHUNK_SIZE", "1200")
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("DATA_DIR", "/srv/documind")
    settings = Settings(_env_file=None)
    assert settings.chunk_size == 1200
    assert settings.llm_provider == "openai"
    assert settings.data_dir == Path("/srv/documind")


def test_derived_paths_live_under_data_dir():
    settings = Settings(_env_file=None, data_dir=Path("/x"))
    assert settings.chroma_dir == Path("/x/chroma")
    assert settings.uploads_dir == Path("/x/uploads")
    assert settings.sqlite_path == Path("/x/documind.db")
