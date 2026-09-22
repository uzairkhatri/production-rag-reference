"""Versioned, offline retrieval and local-generator regression evaluation."""

import hashlib
import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .config import settings
from .eval_runner import score_case
from .generation import ExtractiveGenerator
from .ingestion import chunk_document
from .models import DocumentIn
from .reranking import LexicalReranker
from .retrieval import InMemoryHybridRetriever


class FixtureModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Corpus(FixtureModel):
    schema_version: Literal[1]
    documents: list[DocumentIn] = Field(min_length=1)

    @model_validator(mode="after")
    def check_documents(self):
        ids = [doc.id for doc in self.documents]
        if len(ids) != len(set(ids)):
            raise ValueError("Corpus document IDs must be unique")
        if any(not value.strip() for doc in self.documents for value in doc.model_dump().values()):
            raise ValueError("Corpus document fields must not be whitespace-only")
        return self


class BenchmarkCase(FixtureModel):
    id: str = Field(min_length=1)
    kind: Literal["direct", "paraphrase", "multi_document", "unsupported"]
    question: str = Field(min_length=1)
    relevant_document_ids: list[str]

    @model_validator(mode="after")
    def check_labels(self):
        if not self.id.strip() or not self.question.strip():
            raise ValueError("Case ID and question must not be whitespace-only")
        ids = self.relevant_document_ids
        if len(ids) != len(set(ids)) or any(not value.strip() for value in ids):
            raise ValueError("Relevance labels must be nonempty, unique document IDs")
        if (self.kind == "unsupported") != (len(ids) == 0):
            raise ValueError("Only unsupported questions must have empty relevance labels")
        if self.kind == "multi_document" and len(ids) < 2:
            raise ValueError("Multi-document cases require at least two relevant documents")
        return self


class Dataset(FixtureModel):
    schema_version: Literal[1]
    cases: list[BenchmarkCase] = Field(min_length=1)

    @model_validator(mode="after")
    def check_cases(self):
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("Dataset case IDs must be unique")
        unsupported = sum(case.kind == "unsupported" for case in self.cases)
        if unsupported == 0 or unsupported == len(self.cases):
            raise ValueError("Dataset must contain both answerable and unsupported cases")
        return self


class CaseFloor(FixtureModel):
    recall_at_k: float | None = Field(ge=0, le=1, allow_inf_nan=False)
    reciprocal_rank: float | None = Field(ge=0, le=1, allow_inf_nan=False)
    abstention_correct: bool


class Baseline(FixtureModel):
    schema_version: Literal[1]
    fixture_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    cases: dict[str, CaseFloor] = Field(min_length=1)


def evaluate_benchmark(corpus: Corpus, dataset: Dataset, top_k: int = 5) -> dict:
    if not 1 <= top_k <= 20:
        raise ValueError("top_k must be between 1 and 20")
    document_ids = {doc.id for doc in corpus.documents}
    for case in dataset.cases:
        missing = set(case.relevant_document_ids) - document_ids
        if missing:
            raise ValueError(f"{case.id}: relevance labels absent from corpus: {sorted(missing)}")

    configuration = {
        "top_k": top_k,
        "chunk_words": settings.chunk_words,
        "chunk_overlap": settings.chunk_overlap,
        "max_context_words": settings.max_context_words,
        "generator": "local-extractive",
    }
    fixture = {"corpus": corpus.model_dump(), "dataset": dataset.model_dump(),
               "configuration": configuration}
    fingerprint = hashlib.sha256(json.dumps(fixture, sort_keys=True).encode("utf-8")).hexdigest()
    retriever = InMemoryHybridRetriever()
    chunks = [chunk for doc in corpus.documents
              for chunk in chunk_document(doc, settings.chunk_words, settings.chunk_overlap)]
    retriever.add(chunks)
    reranker = LexicalReranker()
    # Never use the environment-selected factory: evaluation must not call a paid provider.
    generator = ExtractiveGenerator()
    results = []
    for case in dataset.cases:
        hits = reranker.rank(case.question, retriever.search(case.question, top_k))
        expected_abstention = case.kind == "unsupported"
        recall, rr = (None, None) if expected_abstention else score_case(
            hits, tuple(case.relevant_document_ids))
        generated = generator.generate(case.question, hits, settings.max_context_words)
        abstained = not generated.used
        retrieved_ids = [hit.chunk.document_id for hit in hits]
        missing_ids = sorted(set(case.relevant_document_ids) - set(retrieved_ids))
        failures = []
        if missing_ids:
            failures.append("missing_relevant_documents")
        if rr is not None and rr < 1:
            failures.append("first_result_not_relevant")
        if abstained != expected_abstention:
            failures.append("unsupported_answered" if expected_abstention else "answerable_abstained")
        results.append({
            "id": case.id, "kind": case.kind, "question": case.question,
            "relevant_document_ids": case.relevant_document_ids,
            "retrieved_document_ids": retrieved_ids,
            "retrieved_chunk_ids": [hit.chunk.id for hit in hits],
            "missing_document_ids": missing_ids,
            "recall_at_k": recall, "reciprocal_rank": rr,
            "expected_abstention": expected_abstention, "abstained": abstained,
            "abstention_correct": abstained == expected_abstention,
            "evidence_reason": generated.evidence_reason,
            "answer_excerpt": generated.text[:240], "failures": failures,
        })

    answerable = [row for row in results if not row["expected_abstention"]]
    unsupported = [row for row in results if row["expected_abstention"]]
    slices = {}
    for kind in ("direct", "paraphrase", "multi_document"):
        group = [row for row in answerable if row["kind"] == kind]
        if group:
            slices[kind] = {"cases": len(group),
                            "recall_at_k": sum(row["recall_at_k"] for row in group) / len(group),
                            "mrr": sum(row["reciprocal_rank"] for row in group) / len(group)}
    return {
        "schema_version": 1, "fixture_sha256": fingerprint, "configuration": configuration,
        "corpus": {"documents": len(corpus.documents), "chunks": len(chunks)},
        "summary": {
            "cases": len(results), "answerable_cases": len(answerable),
            "unsupported_cases": len(unsupported),
            "recall_at_k": sum(row["recall_at_k"] for row in answerable) / len(answerable),
            "mrr": sum(row["reciprocal_rank"] for row in answerable) / len(answerable),
            "unsupported_abstention_rate": sum(row["abstained"] for row in unsupported) / len(unsupported),
            "answerable_non_abstention_rate": sum(not row["abstained"] for row in answerable) / len(answerable),
            "failed_case_ids": [row["id"] for row in results if row["failures"]],
            "slices": slices,
        },
        "cases": results,
    }


def baseline_from_report(report: dict) -> Baseline:
    return Baseline(schema_version=1, fixture_sha256=report["fixture_sha256"], cases={
        row["id"]: CaseFloor(recall_at_k=row["recall_at_k"],
                             reciprocal_rank=row["reciprocal_rank"],
                             abstention_correct=row["abstention_correct"])
        for row in report["cases"]
    })


def baseline_regressions(report: dict, baseline: Baseline) -> list[str]:
    if baseline.fixture_sha256 != report["fixture_sha256"]:
        raise ValueError("Baseline fixture/configuration mismatch; review a new baseline explicitly")
    if set(baseline.cases) != {row["id"] for row in report["cases"]}:
        raise ValueError("Baseline case IDs do not match the dataset")
    regressions = []
    for row in report["cases"]:
        floor = baseline.cases[row["id"]]
        for metric in ("recall_at_k", "reciprocal_rank"):
            old, new = getattr(floor, metric), row[metric]
            if (old is None) != (new is None):
                raise ValueError(f"{row['id']}: baseline metric applicability mismatch")
            if old is not None and new + 1e-12 < old:
                regressions.append(f"{row['id']}: {metric} decreased from {old} to {new}")
        if floor.abstention_correct and not row["abstention_correct"]:
            regressions.append(f"{row['id']}: abstention decision regressed")
    return regressions
