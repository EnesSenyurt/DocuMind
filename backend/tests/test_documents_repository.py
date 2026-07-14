from datetime import UTC, datetime

from app.services.documents import DocumentRecord, DocumentRepository


def _record(doc_id: str = "abc", filename: str = "a.txt") -> DocumentRecord:
    return DocumentRecord(
        id=doc_id,
        filename=filename,
        content_type="text/plain",
        size_bytes=123,
        num_pages=None,
        num_chunks=4,
        created_at=datetime(2026, 1, 1, tzinfo=UTC),
    )


def test_add_get_roundtrip(tmp_path):
    repo = DocumentRepository(tmp_path / "db.sqlite")
    repo.add(_record())
    fetched = repo.get("abc")
    assert fetched is not None
    assert fetched.filename == "a.txt"
    assert fetched.num_chunks == 4
    assert fetched.created_at == datetime(2026, 1, 1, tzinfo=UTC)


def test_get_missing_returns_none(tmp_path):
    repo = DocumentRepository(tmp_path / "db.sqlite")
    assert repo.get("nope") is None


def test_list_orders_by_created_at_desc(tmp_path):
    repo = DocumentRepository(tmp_path / "db.sqlite")
    older = _record("old", "old.txt")
    older.created_at = datetime(2025, 1, 1, tzinfo=UTC)
    newer = _record("new", "new.txt")
    newer.created_at = datetime(2026, 6, 1, tzinfo=UTC)
    repo.add(older)
    repo.add(newer)
    listed = repo.list()
    assert [r.id for r in listed] == ["new", "old"]


def test_delete_returns_true_then_false(tmp_path):
    repo = DocumentRepository(tmp_path / "db.sqlite")
    repo.add(_record())
    assert repo.delete("abc") is True
    assert repo.delete("abc") is False
    assert repo.get("abc") is None


def test_repository_persists_across_instances(tmp_path):
    db = tmp_path / "db.sqlite"
    DocumentRepository(db).add(_record())
    # A new instance on the same path sees the data.
    assert DocumentRepository(db).get("abc") is not None
