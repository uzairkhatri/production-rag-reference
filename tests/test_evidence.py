import pytest
from fastapi.testclient import TestClient

from app import service
from app.evidence import ABSTENTION, required_values, select_evidence
from app.generation import ExtractiveGenerator
from app.ingestion import Chunk
from app.main import app
from app.retrieval import Hit, InMemoryHybridRetriever


def hit(text, score=1.0, identifier="evidence"):
    return Hit(Chunk(identifier + ":0", identifier, "Source", "synthetic://source", text), score)


@pytest.mark.parametrize("question,kind", [
    ("What uptime percentage is promised?", "percentage"),
    ("How much does archive storage cost?", "money"),
    ("Which SDK version is installed?", "version"),
    ("For exactly how many days are exports retained?", "quantity"),
    ("How long are backups retained?", "quantity"),
])
def test_recognizes_value_requests(question, kind):
    assert kind in required_values(question)


@pytest.mark.parametrize("question", [
    "How should input context be budgeted?",
    "What controls keep token costs predictable?",
    "What steps should a version upgrade include?",
    "Why should request logs redact secrets?",
])
def test_procedural_questions_are_not_numeric_requests(question):
    assert required_values(question) == ()


@pytest.mark.parametrize("question,text", [
    ("What uptime percentage does Orion promise?", "Orion uptime commitment is 99.95%."),
    ("What uptime percentage does Orion promise?", "Orion uptime commitment is ninety nine percent."),
    ("What is the Orion archive price?", "Orion archive price is $0.08 per gigabyte."),
    ("What is the Orion archive price?", "Orion archive costs 8 cents per gigabyte."),
    ("Which Orion SDK version is installed?", "Orion SDK version 2.7.1 is installed."),
    ("How many days are Orion exports retained?", "Orion exports are retained for thirty days."),
    ("How long are Orion exports retained?", "Orion exports are retained for 4 weeks."),
    ("How many requests does Orion allow?", "Orion allows 120 requests per minute."),
])
def test_supported_values_are_not_rejected(question, text):
    result = ExtractiveGenerator().generate(question, [hit(text)], 100)
    assert result.used and result.text == text
    assert result.evidence_reason == "value_evidence_present"


@pytest.mark.parametrize("question,text", [
    ("What is the Orion API price?", "Orion API pricing is discussed in the runbook."),
    ("Which Orion SDK version is installed?", "Orion SDK installation notes are available."),
    ("How many days are Orion exports retained?", "Orion exports are retained according to policy."),
    ("What uptime percentage does Orion promise?", "Orion uptime matters. Workshop attendance is 98 percent."),
    ("What is the Orion API price?", "Orion API pricing is unknown. The workshop costs USD 80."),
    ("How many days are Orion exports retained?", "Orion exports remain available for 30 hours."),
    ("Which Orion Java SDK version is installed?", "Orion Python SDK version 2.7.1 is installed."),
    ("What is the Orion archive price?", "Orion archive price is not published; storage occupies 8 gigabytes."),
])
def test_topic_overlap_and_unrelated_values_are_insufficient(question, text):
    result = ExtractiveGenerator().generate(question, [hit(text)], 100)
    assert result.text == ABSTENTION and result.used == ()
    assert result.evidence_reason.startswith("missing_value_evidence:")


def test_title_cannot_lend_subject_to_unrelated_body():
    candidate = Hit(Chunk("x:0", "x", "Orion API pricing", "synthetic://x", "Workshop price is $80."), 1)
    assert not select_evidence("What is the Orion API price?", [candidate], 100).passages


def test_zero_score_chunks_never_supply_values_or_citations():
    candidates = [hit("Orion API pricing is discussed."),
                  hit("Orion API price is USD 2.50.", score=0, identifier="irrelevant")]
    assert not select_evidence("What is the Orion API price?", candidates, 100).passages
    result = ExtractiveGenerator().generate("Explain API pricing", candidates, 100)
    assert [source.chunk.document_id for source in result.used] == ["evidence"]


def test_value_outside_word_budget_cannot_authorize_answer():
    candidate = hit("Orion SDK notes are extensive. Orion SDK version 2.7.1 is installed.")
    assert not select_evidence("Which Orion SDK version is installed?", [candidate], 5).passages
    assert select_evidence("Which Orion SDK version is installed?", [candidate], 100).passages


def test_multiple_value_types_require_all_of_them():
    question = "What are the Orion SDK version and price?"
    version = hit("Orion SDK version 2.7.1 is installed.")
    price = hit("Orion SDK costs USD 10.", identifier="price")
    assert not select_evidence(question, [version], 100).passages
    assert len(select_evidence(question, [version, price], 100).passages) == 2


def test_underspecified_value_question_abstains():
    evidence = select_evidence("What is the price?", [hit("Orion costs USD 10.")], 100)
    assert evidence.reason == "ambiguous_value_request" and not evidence.passages


@pytest.mark.parametrize("candidates,budget", [([], 100), ([hit("text", 0)], 100), ([hit("text")], 0)])
def test_empty_or_unusable_context_abstains(candidates, budget):
    assert not select_evidence("Question", candidates, budget).passages


def test_api_returns_no_citations_for_missing_value_then_answers_with_evidence(monkeypatch):
    monkeypatch.setattr(service, "retriever", InMemoryHybridRetriever())
    monkeypatch.setattr(service, "generator", ExtractiveGenerator())
    with TestClient(app) as client:
        document = {"id": "orion", "title": "Orion SDK", "source": "synthetic://orion",
                    "text": "Orion SDK installation notes are available."}
        assert client.post("/documents", json=document).status_code == 201
        query = {"question": "Which Orion SDK version is installed?", "top_k": 1}
        missing = client.post("/query", json=query).json()
        assert missing["answer"] == ABSTENTION and missing["citations"] == []
        assert missing["trace_id"]
        document["text"] = "Orion SDK version 2.7.1 is installed."
        assert client.post("/documents", json=document).status_code == 201
        supported = client.post("/query", json=query).json()
        assert "2.7.1" in supported["answer"]
        assert supported["citations"][0]["document_id"] == "orion"
