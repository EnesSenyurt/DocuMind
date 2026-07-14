import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.routes import documents, health
from app.core.config import Settings, get_settings
from app.core.logging import configure_logging
from app.services.documents import DocumentRepository
from app.services.embeddings import EmbeddingModel, build_embedder
from app.services.ingestion.chunker import RecursiveCharacterChunker
from app.services.ingestion.service import IngestionService
from app.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    settings.data_dir.mkdir(parents=True, exist_ok=True)

    # Build the service graph once. The embedder loads its model lazily, so this
    # stays cheap; a test-supplied embedder override takes precedence.
    embedder: EmbeddingModel = app.state.embedder_override or build_embedder(settings)
    vector_store = VectorStore(persist_dir=settings.chroma_dir)
    repository = DocumentRepository(settings.sqlite_path)
    chunker = RecursiveCharacterChunker(settings.chunk_size, settings.chunk_overlap)

    app.state.embedder = embedder
    app.state.vector_store = vector_store
    app.state.repository = repository
    app.state.ingestion_service = IngestionService(
        chunker=chunker,
        embedder=embedder,
        vector_store=vector_store,
        repository=repository,
    )

    logger.info(
        "%s v%s starting (environment=%s, data_dir=%s)",
        settings.app_name,
        __version__,
        settings.environment,
        settings.data_dir.resolve(),
    )
    yield
    logger.info("%s shutting down", settings.app_name)


def create_app(
    settings: Settings | None = None,
    *,
    embedder: EmbeddingModel | None = None,
) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        description="Chat with your own documents — a self-hosted RAG knowledge assistant.",
        lifespan=lifespan,
    )
    app.state.settings = settings
    # Optional embedder injection for tests (avoids loading the real model).
    app.state.embedder_override = embedder

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router, prefix=settings.api_prefix)
    app.include_router(documents.router, prefix=settings.api_prefix)
    return app


app = create_app()
