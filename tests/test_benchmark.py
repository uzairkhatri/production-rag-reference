from copy import deepcopy
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.benchmark import (
    Baseline, BenchmarkCase, Corpus, Dataset, baseline_from_report,
    baseline_regressions, evaluate_benchmark,
)
from app.eval_runner import score_case
from app.generation import ExtractiveGenerator, Generated
from app.ingestion import Chunk
from app.retrieval import Hit, InMemoryHybridRetriever

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def corpus():
    return Corpus.model_validate_json((ROOT / "evals/corpus.json").read_text(encoding="utf-8"))


@pytest.fixture
def dataset():
    return Dataset.model_validate_json((ROOT / "evals/dataset.json").read_text(encoding="utf-8"))


@pytest.fixture
def report(corpus, dataset):
    return evaluate_benchmark(corpus, dataset)


def test_bundled_fixture_is_deterministic_and_baselined(corpus, dataset, report):
    assert report == evaluate_benchmark(corpus, dataset)
    assert report["corpus"] == {"documents": 10, "chunks": 10}
    assert report["summary"]["answerable_cases"] == 18
    assert report["summary"]["unsupported_cases"] == 6
    baseline = Baseline.model_validate_json((ROOT / "evals/baseline.json").read_text(encoding="utf-8"))
    assert baseline_regressions(report, baseline) == []


def test_unsupported_cases_do_not_inflate_retrieval_metrics(report):
    answerable = [row for row in report["cases"] if row["kind"] != "unsupported"]
    unsupported = [row for row in report["cases"] if row["kind"] == "unsupported"]
    assert report["summary"]["recall_at_k"] == pytest.approx(
        sum(row["recall_at_k"] for row in answerable) / 18)
    assert all(row["recall_at_k"] is None and row["reciprocal_rank"] is None for row in unsupported)
    assert report["summary"]["unsupported_abstention_rate"] == pytest.approx(
        sum(row["abstained"] for row in unsupported) / 6)
    assert all("unsupported_answered" in row["failures"] for row in unsupported if not row["abstained"])


def test_multiple_labels_and_duplicate_chunks_do_not_inflate_recall():
    hits = [Hit(Chunk(f"a:{i}", "a", "A", "synthetic://a", "text"), 1) for i in range(2)]
    assert score_case(hits, ("a", "b")) == (0.5, 1.0)
    hits.append(Hit(Chunk("b:0", "b", "B", "synthetic://b", "text"), 1))
    assert score_case(hits, ("b",)) == (1.0, 1 / 3)


def test_empty_retrieval_is_a_regression(corpus, dataset, report, monkeypatch):
    monkeypatch.setattr(InMemoryHybridRetriever, "search", lambda self, question, top_k: [])
    degraded = evaluate_benchmark(corpus, dataset)
    assert degraded["summary"]["recall_at_k"] == 0
    assert degraded["summary"]["mrr"] == 0
    assert baseline_regressions(degraded, baseline_from_report(report))


def test_always_answering_breaks_previously_working_abstention(corpus, dataset, report, monkeypatch):
    monkeypatch.setattr(ExtractiveGenerator, "generate",
                        lambda self, question, hits, max_words: Generated("unsupported", tuple(hits)))
    degraded = evaluate_benchmark(corpus, dataset)
    assert degraded["summary"]["unsupported_abstention_rate"] == 0
    assert any("unsupported-zero-overlap: abstention decision regressed" == failure
               for failure in baseline_regressions(degraded, baseline_from_report(report)))


def test_always_abstaining_is_not_a_success(corpus, dataset, report, monkeypatch):
    monkeypatch.setattr(ExtractiveGenerator, "generate",
                        lambda self, question, hits, max_words: Generated("no evidence", ()))
    degraded = evaluate_benchmark(corpus, dataset)
    assert degraded["summary"]["unsupported_abstention_rate"] == 1
    assert degraded["summary"]["answerable_non_abstention_rate"] == 0
    assert any("retrieval-direct: abstention decision regressed" == failure
               for failure in baseline_regressions(degraded, baseline_from_report(report)))


def test_per_case_regression_is_not_hidden_by_improvement_elsewhere(report):
    baseline = baseline_from_report(report)
    changed = deepcopy(report)
    changed["cases"][0]["reciprocal_rank"] = 0.5
    improved = next(row for row in changed["cases"] if row["id"] == "budget-paraphrase")
    improved["recall_at_k"] = improved["reciprocal_rank"] = 1.0
    failures = baseline_regressions(changed, baseline)
    assert failures == ["retrieval-direct: reciprocal_rank decreased from 1.0 to 0.5"]


def test_improved_known_failure_is_allowed(report):
    baseline = baseline_from_report(report)
    improved = deepcopy(report)
    row = next(row for row in improved["cases"] if row["id"] == "unsupported-finance")
    row["abstention_correct"] = True
    assert baseline_regressions(improved, baseline) == []


def test_baseline_mismatch_requires_review(corpus, dataset, report):
    baseline = baseline_from_report(report)
    changed = corpus.model_copy(deep=True)
    changed.documents[0].text += " Changed evidence."
    with pytest.raises(ValueError, match="fixture/configuration mismatch"):
        baseline_regressions(evaluate_benchmark(changed, dataset), baseline)
    with pytest.raises(ValueError, match="fixture/configuration mismatch"):
        baseline_regressions(evaluate_benchmark(corpus, dataset, top_k=3), baseline)


def test_missing_baseline_case_is_rejected(report):
    baseline = baseline_from_report(report)
    baseline.cases.pop("retrieval-direct")
    with pytest.raises(ValueError, match="case IDs"):
        baseline_regressions(report, baseline)


def test_unknown_relevance_id_is_rejected(corpus, dataset):
    raw = dataset.model_dump()
    raw["cases"][0]["relevant_document_ids"] = ["not-in-corpus"]
    with pytest.raises(ValueError, match="absent from corpus"):
        evaluate_benchmark(corpus, Dataset.model_validate(raw))


@pytest.mark.parametrize("mutation", ["empty", "duplicate", "only_answerable", "only_unsupported"])
def test_invalid_datasets_rejected(dataset, mutation):
    raw = dataset.model_dump()
    if mutation == "empty":
        raw["cases"] = []
    elif mutation == "duplicate":
        raw["cases"].append(raw["cases"][0])
    elif mutation == "only_answerable":
        raw["cases"] = [case for case in raw["cases"] if case["kind"] != "unsupported"]
    else:
        raw["cases"] = [case for case in raw["cases"] if case["kind"] == "unsupported"]
    with pytest.raises(ValidationError):
        Dataset.model_validate(raw)


@pytest.mark.parametrize("kind,labels", [
    ("direct", []), ("unsupported", ["a"]), ("direct", ["a", "a"]),
    ("multi_document", ["a"]), ("direct", [" "]),
])
def test_inconsistent_case_labels_rejected(kind, labels):
    with pytest.raises(ValidationError):
        BenchmarkCase(id="case", kind=kind, question="Question?", relevant_document_ids=labels)


@pytest.mark.parametrize("mutation", ["empty", "duplicate", "blank_text"])
def test_invalid_corpus_rejected(corpus, mutation):
    raw = corpus.model_dump()
    if mutation == "empty":
        raw["documents"] = []
    elif mutation == "duplicate":
        raw["documents"].append(raw["documents"][0])
    else:
        raw["documents"][0]["text"] = "   "
    with pytest.raises(ValidationError):
        Corpus.model_validate(raw)


def test_environment_cannot_select_paid_generation(corpus, dataset, report, monkeypatch):
    monkeypatch.setenv("RAG_GENERATOR_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert evaluate_benchmark(corpus, dataset) == report


def test_original_supported_cases_preserved_with_better_abstention(report):
    assert report["summary"]["answerable_non_abstention_rate"] == 1.0
    assert report["summary"]["unsupported_abstention_rate"] >= 5 / 6
    assert report["summary"]["recall_at_k"] >= 17 / 18


def test_additional_numeric_and_procedural_cases():
    corpus = Corpus.model_validate_json((ROOT / "evals/evidence-corpus.json").read_text(encoding="utf-8"))
    dataset = Dataset.model_validate_json((ROOT / "evals/evidence-dataset.json").read_text(encoding="utf-8"))
    baseline = Baseline.model_validate_json((ROOT / "evals/evidence-baseline.json").read_text(encoding="utf-8"))
    report = evaluate_benchmark(corpus, dataset)
    assert report["summary"]["answerable_non_abstention_rate"] == 1.0
    assert report["summary"]["unsupported_abstention_rate"] >= 0.75
    assert baseline_regressions(report, baseline) == []
    for row in report["cases"]:
        if row["id"].startswith("value-"):
            assert row["evidence_reason"] == "value_evidence_present"
