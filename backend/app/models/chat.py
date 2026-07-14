from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Citation(BaseModel):
    """A source chunk backing an answer, matching an inline [marker]."""

    marker: int = Field(description="1-based index matching the [n] used in the answer.")
    document_id: str
    filename: str
    page: int | None = None
    section: str | None = None
    score: float
    snippet: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1)
    conversation_id: str | None = Field(
        default=None,
        description="Omit to start a new conversation; pass to continue an existing one.",
    )


class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    citations: list[Citation]
    grounded: bool = Field(
        description="False when no relevant context was found and the assistant declined to answer."
    )


class MessageOut(BaseModel):
    role: str
    content: str
    citations: list[Citation] = []
    created_at: datetime


class ConversationSummaryOut(BaseModel):
    id: str
    created_at: datetime
    message_count: int
    title: str | None = None


class ConversationListResponse(BaseModel):
    conversations: list[ConversationSummaryOut]
    total: int


class ConversationDetail(BaseModel):
    id: str
    messages: list[MessageOut]
