"""SQLite-backed registry of ingested documents.

Chroma holds the chunk vectors; this table holds one row per document so the
API can list and delete documents quickly without scanning the vector store.
A fresh connection is opened per operation (SQLite handles this well) and WAL
mode keeps concurrent reads from blocking on writes.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class DocumentRecord:
    id: str
    filename: str
    content_type: str
    size_bytes: int
    num_pages: int | None
    num_chunks: int
    created_at: datetime


class DocumentRepository:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS documents (
                    id           TEXT PRIMARY KEY,
                    filename     TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    size_bytes   INTEGER NOT NULL,
                    num_pages    INTEGER,
                    num_chunks   INTEGER NOT NULL,
                    created_at   TEXT NOT NULL
                )
                """
            )

    def add(self, record: DocumentRecord) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO documents
                    (id, filename, content_type, size_bytes, num_pages, num_chunks, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.id,
                    record.filename,
                    record.content_type,
                    record.size_bytes,
                    record.num_pages,
                    record.num_chunks,
                    record.created_at.isoformat(),
                ),
            )

    def list(self) -> list[DocumentRecord]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM documents ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_record(row) for row in rows]

    def get(self, document_id: str) -> DocumentRecord | None:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT * FROM documents WHERE id = ?", (document_id,)
            ).fetchone()
        return self._row_to_record(row) if row else None

    def delete(self, document_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_record(row: sqlite3.Row) -> DocumentRecord:
        return DocumentRecord(
            id=row["id"],
            filename=row["filename"],
            content_type=row["content_type"],
            size_bytes=row["size_bytes"],
            num_pages=row["num_pages"],
            num_chunks=row["num_chunks"],
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def utcnow() -> datetime:
    return datetime.now(UTC)
