from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / .env.

    Every value has a sensible default so the app boots out of the box;
    anything secret (API keys) must come from the environment.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # App
    app_name: str = "DocuMind"
    environment: Literal["development", "production", "test"] = "development"
    log_level: str = "INFO"
    api_prefix: str = "/api"
    cors_origins: list[str] = Field(default=["http://localhost:5173"])

    # LLM
    llm_provider: Literal["gemini", "openai", "anthropic"] = "gemini"
    llm_model: str = "gemini-3.5-flash"
    gemini_api_key: str = ""
    openai_api_key: str = ""
    anthropic_api_key: str = ""
    # Gemini 2.5/3.x are "thinking" models whose reasoning tokens count against
    # maxOutputTokens; a small budget gets consumed by thinking and truncates the
    # visible answer mid-sentence. Keep this generous so thinking + answer both fit.
    llm_max_tokens: int = Field(default=4096, gt=0)
    llm_temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    llm_timeout_seconds: float = Field(default=60.0, gt=0)
    # Optional, Gemini 3.x only: "minimal" | "low" | "medium" | "high". Empty =
    # don't send it (model default). Lower levels reduce latency for grounded QA.
    # (Gemini 2.5 models use a numeric thinkingBudget instead and ignore this.)
    gemini_thinking_level: str = ""

    # Embeddings
    embedding_model: str = "sentence-transformers/all-MiniLM-L6-v2"

    # Chunking
    chunk_size: int = Field(default=800, gt=0)
    chunk_overlap: int = Field(default=150, ge=0)

    # Retrieval
    retrieval_top_k: int = Field(default=5, gt=0)
    relevance_threshold: float = Field(default=0.25, ge=0.0, le=1.0)

    # Conversation
    # How many prior messages (user + assistant) to replay as chat history.
    max_history_messages: int = Field(default=10, ge=0)

    # Storage
    data_dir: Path = Path("./data")

    @property
    def chroma_dir(self) -> Path:
        return self.data_dir / "chroma"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def sqlite_path(self) -> Path:
        return self.data_dir / "documind.db"


@lru_cache
def get_settings() -> Settings:
    return Settings()
