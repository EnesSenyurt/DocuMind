"""Document management endpoints: upload, list, delete."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, File, HTTPException, UploadFile, status
from fastapi.concurrency import run_in_threadpool

from app.api.dependencies import IngestionServiceDep
from app.models.document import (
    DeleteResponse,
    DocumentListResponse,
    DocumentMeta,
    IngestResponse,
)
from app.services.errors import EmptyDocumentError, UnsupportedFileTypeError

router = APIRouter(prefix="/documents", tags=["documents"])


@router.post("", response_model=IngestResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    service: IngestionServiceDep,
    file: Annotated[UploadFile, File()],
) -> IngestResponse:
    filename = file.filename or "upload"
    data = await file.read()
    if not data:
        # 422 Unprocessable Entity (constant name varies across Starlette versions).
        raise HTTPException(status_code=422, detail="Uploaded file is empty.")
    try:
        # Ingestion is blocking (parsing + embedding); keep the event loop free.
        record = await run_in_threadpool(service.ingest, filename, data)
    except UnsupportedFileTypeError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail=str(exc)
        ) from exc
    except EmptyDocumentError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return IngestResponse(document=DocumentMeta.from_record(record))


@router.get("", response_model=DocumentListResponse)
async def list_documents(service: IngestionServiceDep) -> DocumentListResponse:
    records = await run_in_threadpool(service.list_documents)
    documents = [DocumentMeta.from_record(record) for record in records]
    return DocumentListResponse(documents=documents, total=len(documents))


@router.delete("/{document_id}", response_model=DeleteResponse)
async def delete_document(document_id: str, service: IngestionServiceDep) -> DeleteResponse:
    deleted = await run_in_threadpool(service.delete_document, document_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Document {document_id!r} not found.",
        )
    return DeleteResponse(id=document_id, deleted=True)
