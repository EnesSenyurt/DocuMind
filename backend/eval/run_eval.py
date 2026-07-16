"""Retrieval evaluation harness.

Given a JSON file of (question, expected_source) pairs and a corpus directory,
ingests the corpus through the real pipeline (extract -> chunk -> embed -> store)
and measures how often the expected document appears among the top-k retrieved
chunks (hit-rate@k), plus mean reciprocal rank (MRR).

Usage:
    python -m eval.run_eval                       # defaults: cases.json, corpus/, k=5
    python -m eval.run_eval --top-k 3
    python -m eval.run_eval --embedder hashing    # offline, no model download
    python -m eval.run_eval --json                # machine-readable output
"""

from __future__ import annotations

import argparse
import json
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from app.core.config import Settings
from app.services.documents import DocumentRepository
from app.services.embeddings import (
    EmbeddingModel,
    HashingEmbedder,
    SentenceTransformerEmbedder,
)
from app.services.ingestion.chunker import RecursiveCharacterChunker
from app.services.ingestion.service import IngestionService
from app.services.retrieval.service import RetrievalService
from app.services.vector_store import VectorStore

EVAL_DIR = Path(__file__).parent
DEFAULT_CASES = EVAL_DIR / "cases.json"
DEFAULT_CORPUS = EVAL_DIR / "corpus"


@dataclass
class CaseResult:
    question: str
    expected_source: str
    hit: bool
    rank: int | None  # 1-based position of the first chunk from the expected doc
    retrieved_sources: list[str]


@dataclass
class EvalReport:
    embedder: str
    top_k: int
    total: int
    hits: int
    hit_rate: float
    mrr: float
    cases: list[CaseResult]


def _build_embedder(name: str, settings: Settings) -> EmbeddingModel:
    if name == "hashing":
        return HashingEmbedder()
    return SentenceTransformerEmbedder(settings.embedding_model)


def evaluate(
    cases: list[dict],
    corpus_dir: Path,
    top_k: int = 5,
    embedder_name: str = "sentence-transformers",
    settings: Settings | None = None,
) -> EvalReport:
    settings = settings or Settings(_env_file=None)
    embedder = _build_embedder(embedder_name, settings)
    store = VectorStore(persist_dir=None)

    with tempfile.TemporaryDirectory() as tmp:
        repo = DocumentRepository(Path(tmp) / "eval.db")
        chunker = RecursiveCharacterChunker(settings.chunk_size, settings.chunk_overlap)
        ingestion = IngestionService(chunker, embedder, store, repo)
        for path in sorted(corpus_dir.iterdir()):
            if path.is_file():
                ingestion.ingest(path.name, path.read_bytes())

        # Threshold is 0 here: hit-rate asks whether the right doc is in the
        # top-k at all, independent of the production "no info" cutoff.
        retrieval = RetrievalService(embedder, store, settings)
        results: list[CaseResult] = []
        for case in cases:
            chunks = retrieval.retrieve(case["question"], top_k=top_k, threshold=0.0)
            ordered_sources: list[str] = []
            rank: int | None = None
            for position, chunk in enumerate(chunks, start=1):
                filename = chunk.metadata.get("filename", "unknown")
                if filename not in ordered_sources:
                    ordered_sources.append(filename)
                if rank is None and filename == case["expected_source"]:
                    rank = position
            results.append(
                CaseResult(
                    question=case["question"],
                    expected_source=case["expected_source"],
                    hit=rank is not None,
                    rank=rank,
                    retrieved_sources=ordered_sources,
                )
            )

    hits = sum(1 for r in results if r.hit)
    total = len(results)
    hit_rate = hits / total if total else 0.0
    mrr = (sum(1.0 / r.rank for r in results if r.rank) / total) if total else 0.0
    return EvalReport(
        embedder=embedder_name,
        top_k=top_k,
        total=total,
        hits=hits,
        hit_rate=hit_rate,
        mrr=mrr,
        cases=results,
    )


def _print_report(report: EvalReport) -> None:
    print(f"\nRetrieval evaluation — embedder={report.embedder}, k={report.top_k}\n")
    for result in report.cases:
        mark = "✓" if result.hit else "✗"
        rank = f"rank {result.rank}" if result.rank else "not found"
        print(f"  {mark}  [{rank}]  {result.question}")
        print(f"       expected: {result.expected_source} | retrieved: {result.retrieved_sources}")
    print(
        f"\n  hit-rate@{report.top_k}: {report.hit_rate:.0%} "
        f"({report.hits}/{report.total})   MRR: {report.mrr:.3f}\n"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure retrieval hit-rate@k.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--corpus", type=Path, default=DEFAULT_CORPUS)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument(
        "--embedder",
        choices=["sentence-transformers", "hashing"],
        default="sentence-transformers",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of a table.")
    args = parser.parse_args()

    cases = json.loads(args.cases.read_text())
    report = evaluate(cases, args.corpus, top_k=args.top_k, embedder_name=args.embedder)

    if args.json:
        print(json.dumps(asdict(report), indent=2))
    else:
        _print_report(report)


if __name__ == "__main__":
    main()
