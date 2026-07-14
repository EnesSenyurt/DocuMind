"""Chat + conversation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, status

from app.api.dependencies import ChatServiceDep, ConversationRepositoryDep
from app.models.chat import (
    ChatRequest,
    ChatResponse,
    Citation,
    ConversationDetail,
    ConversationListResponse,
    ConversationSummaryOut,
    MessageOut,
)
from app.models.document import DeleteResponse
from app.services.llm.base import LLMError

router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, service: ChatServiceDep) -> ChatResponse:
    try:
        result = await service.chat(request.message, request.conversation_id)
    except LLMError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The language model provider failed: {exc}",
        ) from exc
    return ChatResponse(
        conversation_id=result.conversation_id,
        message=result.message,
        citations=[Citation(**citation) for citation in result.citations],
        grounded=result.grounded,
    )


@router.get("/conversations", response_model=ConversationListResponse)
async def list_conversations(repo: ConversationRepositoryDep) -> ConversationListResponse:
    summaries = repo.list_conversations()
    return ConversationListResponse(
        conversations=[
            ConversationSummaryOut(
                id=s.id,
                created_at=s.created_at,
                message_count=s.message_count,
                title=s.title,
            )
            for s in summaries
        ],
        total=len(summaries),
    )


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str, repo: ConversationRepositoryDep
) -> ConversationDetail:
    if not repo.exists(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id!r} not found.",
        )
    messages = repo.get_messages(conversation_id)
    return ConversationDetail(
        id=conversation_id,
        messages=[
            MessageOut(
                role=m.role,
                content=m.content,
                citations=[Citation(**c) for c in m.citations],
                created_at=m.created_at,
            )
            for m in messages
        ],
    )


@router.delete("/conversations/{conversation_id}", response_model=DeleteResponse)
async def delete_conversation(
    conversation_id: str, repo: ConversationRepositoryDep
) -> DeleteResponse:
    if not repo.delete_conversation(conversation_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id!r} not found.",
        )
    return DeleteResponse(id=conversation_id, deleted=True)
