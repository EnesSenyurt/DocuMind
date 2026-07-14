"""End-to-end API tests for the document endpoints (upload -> list -> delete),
using the hashing embedder injected by the ``client`` fixture."""


def test_upload_then_list_then_delete(client):
    content = b"# Notes\n\n" + b"DocuMind grounds answers in your own documents. " * 10
    response = client.post(
        "/api/documents",
        files={"file": ("notes.md", content, "text/markdown")},
    )
    assert response.status_code == 201
    document = response.json()["document"]
    assert document["filename"] == "notes.md"
    assert document["content_type"] == "text/markdown"
    assert document["num_chunks"] >= 1
    doc_id = document["id"]

    listing = client.get("/api/documents").json()
    assert listing["total"] == 1
    assert listing["documents"][0]["id"] == doc_id

    deleted = client.delete(f"/api/documents/{doc_id}")
    assert deleted.status_code == 200
    assert deleted.json() == {"id": doc_id, "deleted": True}
    assert client.get("/api/documents").json()["total"] == 0


def test_upload_unsupported_type_returns_415(client):
    response = client.post(
        "/api/documents",
        files={"file": ("data.csv", b"a,b,c", "text/csv")},
    )
    assert response.status_code == 415


def test_upload_empty_file_returns_422(client):
    response = client.post(
        "/api/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
    )
    assert response.status_code == 422


def test_upload_whitespace_only_returns_422(client):
    response = client.post(
        "/api/documents",
        files={"file": ("blank.txt", b"   \n\t ", "text/plain")},
    )
    assert response.status_code == 422


def test_delete_missing_document_returns_404(client):
    assert client.delete("/api/documents/does-not-exist").status_code == 404
