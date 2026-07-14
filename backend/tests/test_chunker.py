import pytest

from app.services.ingestion.chunker import RecursiveCharacterChunker
from app.services.ingestion.extractors import PageSegment


def test_rejects_overlap_not_smaller_than_size():
    with pytest.raises(ValueError):
        RecursiveCharacterChunker(chunk_size=100, chunk_overlap=100)


def test_short_text_is_a_single_chunk():
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    chunks = chunker.split_text("A short sentence.")
    assert chunks == ["A short sentence."]


def test_no_chunk_exceeds_chunk_size():
    chunker = RecursiveCharacterChunker(chunk_size=120, chunk_overlap=20)
    text = " ".join(f"word{i}" for i in range(300))
    chunks = chunker.split_text(text)
    assert len(chunks) > 1
    assert all(len(chunk) <= 120 for chunk in chunks)


def test_prefers_paragraph_then_sentence_boundaries():
    chunker = RecursiveCharacterChunker(chunk_size=60, chunk_overlap=0)
    text = "First paragraph here.\n\nSecond paragraph is separate."
    chunks = chunker.split_text(text)
    # Split on the blank line rather than mid-sentence.
    assert "First paragraph here." in chunks[0]
    assert any("Second paragraph" in c for c in chunks)


def test_overlap_shares_content_between_neighbours():
    chunker = RecursiveCharacterChunker(chunk_size=50, chunk_overlap=20)
    words = " ".join(f"token{i:02d}" for i in range(40))
    chunks = chunker.split_text(words)
    assert len(chunks) >= 2
    # Consecutive chunks should share at least one token due to overlap.
    for earlier, later in zip(chunks, chunks[1:], strict=False):
        shared = set(earlier.split()) & set(later.split())
        assert shared, f"expected overlap between {earlier!r} and {later!r}"


def test_very_long_unbroken_token_falls_back_to_characters():
    chunker = RecursiveCharacterChunker(chunk_size=10, chunk_overlap=2)
    chunks = chunker.split_text("x" * 35)
    assert chunks
    assert all(len(chunk) <= 10 for chunk in chunks)


def test_chunk_segments_preserve_page_and_section_metadata():
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    segments = [
        PageSegment(text="Intro on page one.", page=1, section="Introduction"),
        PageSegment(text="Details on page two.", page=2, section="Details"),
    ]
    chunks = chunker.chunk_segments(segments)
    assert [c.index for c in chunks] == list(range(len(chunks)))
    assert chunks[0].page == 1 and chunks[0].section == "Introduction"
    assert chunks[-1].page == 2 and chunks[-1].section == "Details"


def test_chunk_never_spans_two_segments():
    chunker = RecursiveCharacterChunker(chunk_size=1000, chunk_overlap=0)
    segments = [
        PageSegment(text="Page one text.", page=1),
        PageSegment(text="Page two text.", page=2),
    ]
    chunks = chunker.chunk_segments(segments)
    # Even though both fit in one chunk_size, they stay separate for citation.
    assert len(chunks) == 2
    assert chunks[0].page == 1
    assert chunks[1].page == 2
