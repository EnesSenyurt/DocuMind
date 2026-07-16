"""Tests for the retrieval evaluation harness (using the offline hashing
embedder so the sample corpus is scored without a model download)."""

import json

from eval.run_eval import DEFAULT_CASES, DEFAULT_CORPUS, evaluate


def _load_cases():
    return json.loads(DEFAULT_CASES.read_text())


def test_sample_cases_file_has_five_pairs():
    cases = _load_cases()
    assert len(cases) == 5
    assert all("question" in c and "expected_source" in c for c in cases)


def test_evaluate_reports_reasonable_hit_rate_on_sample_corpus():
    report = evaluate(_load_cases(), DEFAULT_CORPUS, top_k=5, embedder_name="hashing")
    assert report.total == 5
    # The sample corpus is topically distinct; lexical overlap alone should find
    # the right document for most questions.
    assert report.hit_rate >= 0.6
    assert 0.0 <= report.mrr <= 1.0


def test_evaluate_structure_and_ranks():
    report = evaluate(_load_cases(), DEFAULT_CORPUS, top_k=5, embedder_name="hashing")
    for case in report.cases:
        assert case.retrieved_sources  # something was retrieved
        if case.hit:
            assert case.rank is not None and case.rank >= 1
            assert case.expected_source in case.retrieved_sources


def test_smaller_k_never_improves_hit_rate():
    cases = _load_cases()
    k5 = evaluate(cases, DEFAULT_CORPUS, top_k=5, embedder_name="hashing").hit_rate
    k1 = evaluate(cases, DEFAULT_CORPUS, top_k=1, embedder_name="hashing").hit_rate
    assert k1 <= k5
