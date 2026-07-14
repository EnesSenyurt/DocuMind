"""Text extraction for supported document formats.

Each extractor returns a list of ``PageSegment``s: contiguous blocks of text
tagged with the page number (PDF) and/or section heading (DOCX, Markdown) they
came from. Downstream chunking inherits this metadata so citations can point at
a specific page and section.
"""

from __future__ import annotations

import io
from dataclasses import dataclass
from pathlib import Path

from app.services.errors import UnsupportedFileTypeError


@dataclass
class PageSegment:
    text: str
    page: int | None = None
    section: str | None = None


# Extension -> canonical content type. Extension is the source of truth because
# browsers report inconsistent MIME types for these formats.
SUPPORTED_EXTENSIONS: dict[str, str] = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".txt": "text/plain",
    ".md": "text/markdown",
    ".markdown": "text/markdown",
}


def resolve_content_type(filename: str) -> str:
    """Return the canonical content type for a filename, or raise if unsupported."""
    ext = Path(filename).suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
        raise UnsupportedFileTypeError(filename, detail=f"Supported types: {supported}.")
    return SUPPORTED_EXTENSIONS[ext]


def extract_segments(filename: str, data: bytes) -> list[PageSegment]:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _extract_pdf(data)
    if ext == ".docx":
        return _extract_docx(data)
    if ext in (".md", ".markdown"):
        return _extract_markdown(data)
    if ext == ".txt":
        return _extract_text(data)
    supported = ", ".join(sorted(SUPPORTED_EXTENSIONS))
    raise UnsupportedFileTypeError(filename, detail=f"Supported types: {supported}.")


def _decode(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def _extract_pdf(data: bytes) -> list[PageSegment]:
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(data))
    segments: list[PageSegment] = []
    for page_number, page in enumerate(reader.pages, start=1):
        text = (page.extract_text() or "").strip()
        if text:
            segments.append(PageSegment(text=text, page=page_number))
    return segments


def _extract_docx(data: bytes) -> list[PageSegment]:
    """Split a DOCX into segments by heading, so each carries its section."""
    from docx import Document

    document = Document(io.BytesIO(data))
    segments: list[PageSegment] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            text = "\n".join(buffer).strip()
            if text:
                segments.append(PageSegment(text=text, section=current_section))
            buffer.clear()

    for paragraph in document.paragraphs:
        style = (paragraph.style.name if paragraph.style else "") or ""
        text = paragraph.text.strip()
        if style.startswith("Heading") or style == "Title":
            flush()
            current_section = text or current_section
            if text:
                buffer.append(text)
        elif text:
            buffer.append(text)
    flush()
    return segments


def _extract_markdown(data: bytes) -> list[PageSegment]:
    """Split Markdown into segments by ATX heading (``#`` .. ``######``)."""
    segments: list[PageSegment] = []
    current_section: str | None = None
    buffer: list[str] = []

    def flush() -> None:
        if buffer:
            text = "\n".join(buffer).strip()
            if text:
                segments.append(PageSegment(text=text, section=current_section))
            buffer.clear()

    for line in _decode(data).splitlines():
        stripped = line.lstrip()
        if stripped.startswith("#"):
            heading_text = stripped.lstrip("#").strip()
            flush()
            current_section = heading_text or current_section
            if heading_text:
                buffer.append(heading_text)
        else:
            buffer.append(line)
    flush()
    return segments


def _extract_text(data: bytes) -> list[PageSegment]:
    text = _decode(data).strip()
    return [PageSegment(text=text)] if text else []
