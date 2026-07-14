"""SQLite-backed conversation + message store for multi-turn chat.

Lives in the same database file as the document registry (separate tables).
Assistant messages carry their citations as JSON so a conversation can be
replayed with sources intact.
"""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path


@dataclass
class Message:
    conversation_id: str
    role: str  # "user" | "assistant"
    content: str
    created_at: datetime
    citations: list[dict] = field(default_factory=list)
    id: int | None = None


@dataclass
class ConversationSummary:
    id: str
    created_at: datetime
    message_count: int
    title: str | None  # first user message, truncated


class ConversationRepository:
    def __init__(self, db_path: Path | str) -> None:
        self._db_path = str(db_path)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_schema(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS conversations (
                    id         TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS messages (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    conversation_id TEXT NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
                    role            TEXT NOT NULL,
                    content         TEXT NOT NULL,
                    citations_json  TEXT,
                    created_at      TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_messages_conversation "
                "ON messages(conversation_id, id)"
            )

    def ensure_conversation(self, conversation_id: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO conversations (id, created_at) VALUES (?, ?)",
                (conversation_id, _utcnow().isoformat()),
            )

    def exists(self, conversation_id: str) -> bool:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT 1 FROM conversations WHERE id = ?", (conversation_id,)
            ).fetchone()
        return row is not None

    def add_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        citations: list[dict] | None = None,
    ) -> Message:
        created_at = _utcnow()
        citations_json = json.dumps(citations) if citations else None
        with self._connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO messages (conversation_id, role, content, citations_json, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (conversation_id, role, content, citations_json, created_at.isoformat()),
            )
            message_id = cursor.lastrowid
        return Message(
            id=message_id,
            conversation_id=conversation_id,
            role=role,
            content=content,
            citations=citations or [],
            created_at=created_at,
        )

    def recent_messages(self, conversation_id: str, limit: int) -> list[Message]:
        """Return up to ``limit`` most-recent messages, in chronological order."""
        if limit <= 0:
            return []
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id DESC LIMIT ?",
                (conversation_id, limit),
            ).fetchall()
        return [self._row_to_message(row) for row in reversed(rows)]

    def get_messages(self, conversation_id: str) -> list[Message]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM messages WHERE conversation_id = ? ORDER BY id ASC",
                (conversation_id,),
            ).fetchall()
        return [self._row_to_message(row) for row in rows]

    def list_conversations(self) -> list[ConversationSummary]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT
                    c.id AS id,
                    c.created_at AS created_at,
                    COUNT(m.id) AS message_count,
                    (
                        SELECT content FROM messages
                        WHERE conversation_id = c.id AND role = 'user'
                        ORDER BY id ASC LIMIT 1
                    ) AS first_user_message
                FROM conversations c
                LEFT JOIN messages m ON m.conversation_id = c.id
                GROUP BY c.id
                ORDER BY c.created_at DESC
                """
            ).fetchall()
        summaries: list[ConversationSummary] = []
        for row in rows:
            title = row["first_user_message"]
            if title and len(title) > 80:
                title = title[:77] + "..."
            summaries.append(
                ConversationSummary(
                    id=row["id"],
                    created_at=datetime.fromisoformat(row["created_at"]),
                    message_count=row["message_count"],
                    title=title,
                )
            )
        return summaries

    def delete_conversation(self, conversation_id: str) -> bool:
        with self._connect() as conn:
            cursor = conn.execute(
                "DELETE FROM conversations WHERE id = ?", (conversation_id,)
            )
        return cursor.rowcount > 0

    @staticmethod
    def _row_to_message(row: sqlite3.Row) -> Message:
        citations = json.loads(row["citations_json"]) if row["citations_json"] else []
        return Message(
            id=row["id"],
            conversation_id=row["conversation_id"],
            role=row["role"],
            content=row["content"],
            citations=citations,
            created_at=datetime.fromisoformat(row["created_at"]),
        )


def _utcnow() -> datetime:
    return datetime.now(UTC)
