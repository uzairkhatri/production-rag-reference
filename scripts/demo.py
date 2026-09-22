"""Exercise a local API with public sample data; no extra client dependency needed."""

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import UUID

ROOT = Path(__file__).resolve().parents[1]
ABSTENTION = "I don't have enough grounded context to answer that question."


def request(base_url: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = Request(base_url + path, data=data, headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=10) as response:
        return json.load(response)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def run_demo(base_url: str) -> dict:
    require(request(base_url, "/health") == {"status": "ok"}, "Health check failed")
    document = {
        "id": "walkthrough-production-rag",
        "title": "Production RAG",
        "source": "local://examples/documents/production-rag.txt",
        "text": (ROOT / "examples/documents/production-rag.txt").read_text(encoding="utf-8"),
    }
    ingested = request(base_url, "/documents", document)
    require(ingested.get("document_id") == document["id"], "Unexpected document ID")
    require(ingested.get("chunks", 0) > 0, "No chunks were ingested")
    answer = request(base_url, "/query", {
        "question": "How does production RAG handle retrieval quality and citations?",
        "top_k": 1,
    })
    require(bool(answer.get("answer")), "The answer is empty")
    require(any(c.get("document_id") == document["id"] for c in answer.get("citations", [])),
            "The sample document was not cited; use a fresh local-mode server")
    UUID(answer["trace_id"])
    # An intentionally unmatched token tests zero lexical evidence, not semantic safety.
    no_evidence = request(base_url, "/query", {"question": "zxqvunsupportedtoken", "top_k": 1})
    require(no_evidence.get("answer") == ABSTENTION and no_evidence.get("citations") == [],
            "Expected abstention for a query with no lexical evidence")
    return {"ingestion": ingested, "answer": answer, "no_evidence": no_evidence}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000, help="Local API port (default: 8000)")
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    base_url = f"http://127.0.0.1:{args.port}"
    try:
        result = run_demo(base_url)
    except (URLError, OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Demo failed: {exc}\nStart a fresh local-mode API at {base_url}; see docs/demo.md.",
              file=sys.stderr)
        return 1
    print(json.dumps(result, indent=2))
    print("PASS: ingestion, source citation, trace ID, and zero-evidence abstention")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
