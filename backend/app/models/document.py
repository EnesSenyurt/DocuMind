from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.services.documents import DocumentRecord


class DocumentMeta(BaseModel):
    """Public metadata for an ingested document."""

    id: str
    filename: str
    content_type: str
    size_bytes: int
    num_pages: int | None = Field(
        default=None, description="Page count when the format is paginated (PDF); null otherwise."
    )
    num_chunks: int
    created_at: datetime

    @classmethod
    def from_record(cls, record: DocumentRecord) -> DocumentMeta:
        return cls(
            id=record.id,
            filename=record.filename,
            content_type=record.content_type,
            size_bytes=record.size_bytes,
            num_pages=record.num_pages,
            num_chunks=record.num_chunks,
            created_at=record.created_at,
        )


class IngestResponse(BaseModel):
    document: DocumentMeta


class DocumentListResponse(BaseModel):
    documents: list[DocumentMeta]
    total: int


class DeleteResponse(BaseModel):
    id: str
    deleted: bool
