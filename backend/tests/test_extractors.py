import pytest

from app.services.errors import UnsupportedFileTypeError
from app.services.ingestion.extractors import (
    extract_segments,
    resolve_content_type,
)


def test_resolve_content_type_maps_known_extensions():
    assert resolve_content_type("notes.txt") == "text/plain"
    assert resolve_content_type("README.md") == "text/markdown"
    assert resolve_content_type("paper.PDF") == "application/pdf"


def test_resolve_content_type_rejects_unknown():
    with pytest.raises(UnsupportedFileTypeError):
        resolve_content_type("archive.zip")


def test_extract_txt_single_segment():
    segments = extract_segments("a.txt", b"hello world")
    assert len(segments) == 1
    assert segments[0].text == "hello world"
    assert segments[0].page is None


def test_extract_txt_empty_returns_no_segments():
    assert extract_segments("a.txt", b"   \n  ") == []


def test_extract_markdown_splits_by_heading_and_tracks_section():
    md = b"# Title\n\nIntro text.\n\n## Section A\n\nBody of A.\n"
    segments = extract_segments("doc.md", md)
    sections = [s.section for s in segments]
    assert "Title" in sections
    assert "Section A" in sections
    section_a = next(s for s in segments if s.section == "Section A")
    assert "Body of A." in section_a.text


def test_extract_unsupported_extension_raises():
    with pytest.raises(UnsupportedFileTypeError):
        extract_segments("data.csv", b"a,b,c")


def test_extract_docx_reads_paragraphs_and_headings():
    docx = pytest.importorskip("docx")
    import io

    document = docx.Document()
    document.add_heading("Overview", level=1)
    document.add_paragraph("This is the overview body.")
    document.add_heading("Method", level=1)
    document.add_paragraph("The method paragraph.")
    buffer = io.BytesIO()
    document.save(buffer)

    segments = extract_segments("report.docx", buffer.getvalue())
    sections = [s.section for s in segments]
    assert "Overview" in sections
    assert "Method" in sections
    assert any("overview body" in s.text for s in segments)
