from app.services.conversations import ConversationRepository


def _repo(tmp_path) -> ConversationRepository:
    return ConversationRepository(tmp_path / "db.sqlite")


def test_ensure_and_exists(tmp_path):
    repo = _repo(tmp_path)
    assert repo.exists("c1") is False
    repo.ensure_conversation("c1")
    assert repo.exists("c1") is True
    # Idempotent.
    repo.ensure_conversation("c1")
    assert len(repo.list_conversations()) == 1


def test_add_and_get_messages_in_order(tmp_path):
    repo = _repo(tmp_path)
    repo.ensure_conversation("c1")
    repo.add_message("c1", "user", "hello")
    repo.add_message("c1", "assistant", "hi there", citations=[{"marker": 1}])
    messages = repo.get_messages("c1")
    assert [m.role for m in messages] == ["user", "assistant"]
    assert messages[1].citations == [{"marker": 1}]


def test_recent_messages_limit_and_chronological_order(tmp_path):
    repo = _repo(tmp_path)
    repo.ensure_conversation("c1")
    for i in range(6):
        repo.add_message("c1", "user", f"m{i}")
    recent = repo.recent_messages("c1", limit=3)
    # Last 3, oldest-first.
    assert [m.content for m in recent] == ["m3", "m4", "m5"]


def test_recent_messages_zero_limit_returns_empty(tmp_path):
    repo = _repo(tmp_path)
    repo.ensure_conversation("c1")
    repo.add_message("c1", "user", "hello")
    assert repo.recent_messages("c1", limit=0) == []


def test_list_conversations_uses_first_user_message_as_title(tmp_path):
    repo = _repo(tmp_path)
    repo.ensure_conversation("c1")
    repo.add_message("c1", "user", "What is DocuMind?")
    repo.add_message("c1", "assistant", "A RAG assistant.")
    summary = repo.list_conversations()[0]
    assert summary.title == "What is DocuMind?"
    assert summary.message_count == 2


def test_delete_conversation_cascades_to_messages(tmp_path):
    repo = _repo(tmp_path)
    repo.ensure_conversation("c1")
    repo.add_message("c1", "user", "hello")
    assert repo.delete_conversation("c1") is True
    assert repo.exists("c1") is False
    assert repo.get_messages("c1") == []
    assert repo.delete_conversation("c1") is False
