"""Recursive character text splitting.

Splits text on a descending list of separators (paragraph -> line -> sentence ->
word -> character), merging the pieces into chunks of at most ``chunk_size``
characters with ``chunk_overlap`` characters shared between neighbours. Trying
the coarsest separator first keeps semantically related text together; falling
back to finer separators guarantees no chunk exceeds the size limit.

This mirrors the well-known LangChain ``RecursiveCharacterTextSplitter`` strategy
but is implemented here so the behaviour is fully owned and unit-tested.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.ingestion.extractors import PageSegment

DEFAULT_SEPARATORS: list[str] = ["\n\n", "\n", ". ", " ", ""]


@dataclass
class Chunk:
    text: str
    index: int
    page: int | None = None
    section: str | None = None


class RecursiveCharacterChunker:
    def __init__(
        self,
        chunk_size: int,
        chunk_overlap: int,
        separators: list[str] | None = None,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0:
            raise ValueError("chunk_overlap must be non-negative")
        if chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be smaller than chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._separators = separators or DEFAULT_SEPARATORS

    def split_text(self, text: str) -> list[str]:
        return self._split(text, self._separators)

    def chunk_segments(self, segments: list[PageSegment]) -> list[Chunk]:
        """Chunk each segment independently, preserving page/section metadata.

        Chunks never span a page or section boundary, which keeps citations
        precise, and a running index is assigned across the whole document.
        """
        chunks: list[Chunk] = []
        index = 0
        for segment in segments:
            for piece in self.split_text(segment.text):
                chunks.append(
                    Chunk(
                        text=piece,
                        index=index,
                        page=segment.page,
                        section=segment.section,
                    )
                )
                index += 1
        return chunks

    def _split(self, text: str, separators: list[str]) -> list[str]:
        if not text:
            return []

        # Choose the first separator that appears in the text (or the last one).
        separator = separators[-1]
        remaining_separators: list[str] = []
        for i, sep in enumerate(separators):
            if sep == "":
                separator = ""
                remaining_separators = []
                break
            if sep in text:
                separator = sep
                remaining_separators = separators[i + 1 :]
                break

        splits = list(text) if separator == "" else text.split(separator)

        final_chunks: list[str] = []
        good_splits: list[str] = []
        for piece in splits:
            if len(piece) <= self.chunk_size:
                good_splits.append(piece)
                continue
            # Flush accumulated small pieces, then recurse into the oversized one.
            if good_splits:
                final_chunks.extend(self._merge(good_splits, separator))
                good_splits = []
            if remaining_separators:
                final_chunks.extend(self._split(piece, remaining_separators))
            else:
                final_chunks.append(piece)
        if good_splits:
            final_chunks.extend(self._merge(good_splits, separator))
        return final_chunks

    def _merge(self, splits: list[str], separator: str) -> list[str]:
        """Greedily pack pieces into chunks, carrying overlap between them."""
        sep_len = len(separator)
        chunks: list[str] = []
        current: list[str] = []
        current_len = 0

        for piece in splits:
            addition = len(piece) + (sep_len if current else 0)
            if current_len + addition > self.chunk_size and current:
                chunks.append(separator.join(current).strip())
                # Drop pieces from the front until the remaining tail fits the
                # overlap budget, so the next chunk starts with shared context.
                while current_len > self.chunk_overlap and current:
                    removed = current.pop(0)
                    current_len -= len(removed) + (sep_len if current else 0)
            current.append(piece)
            current_len += len(piece) + (sep_len if len(current) > 1 else 0)

        if current:
            chunks.append(separator.join(current).strip())
        return [chunk for chunk in chunks if chunk]
