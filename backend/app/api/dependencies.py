"""FastAPI dependencies.

Services are built once at startup and stashed on ``app.state`` (see
``app.main``); these dependencies just hand them to route handlers. Reading
settings from ``app.state`` — rather than the module-level singleton — lets
tests construct an app with isolated settings.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Request

from app.core.config import Settings
from app.services.chat.service import ChatService
from app.services.conversations import ConversationRepository
from app.services.documents import DocumentRepository
from app.services.embeddings import EmbeddingModel
from app.services.ingestion.service import IngestionService
from app.services.retrieval.service import RetrievalService
from app.services.vector_store import VectorStore


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


def get_embedder(request: Request) -> EmbeddingModel:
    return request.app.state.embedder


def get_vector_store(request: Request) -> VectorStore:
    return request.app.state.vector_store


def get_repository(request: Request) -> DocumentRepository:
    return request.app.state.repository


def get_ingestion_service(request: Request) -> IngestionService:
    return request.app.state.ingestion_service


def get_retrieval_service(request: Request) -> RetrievalService:
    return request.app.state.retrieval_service


def get_conversation_repository(request: Request) -> ConversationRepository:
    return request.app.state.conversation_repository


def get_chat_service(request: Request) -> ChatService:
    return request.app.state.chat_service


SettingsDep = Annotated[Settings, Depends(get_settings)]
EmbedderDep = Annotated[EmbeddingModel, Depends(get_embedder)]
VectorStoreDep = Annotated[VectorStore, Depends(get_vector_store)]
IngestionServiceDep = Annotated[IngestionService, Depends(get_ingestion_service)]
RetrievalServiceDep = Annotated[RetrievalService, Depends(get_retrieval_service)]
ConversationRepositoryDep = Annotated[
    ConversationRepository, Depends(get_conversation_repository)
]
ChatServiceDep = Annotated[ChatService, Depends(get_chat_service)]
