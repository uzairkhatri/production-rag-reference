# Production RAG Reference

**A runnable Python reference for inspecting a RAG pipeline before connecting a model provider.**

[![CI](https://github.com/uzairkhatri/production-rag-reference/actions/workflows/ci.yml/badge.svg)](https://github.com/uzairkhatri/production-rag-reference/actions/workflows/ci.yml)
[![Retrieval gate](https://github.com/uzairkhatri/production-rag-reference/actions/workflows/rag-evaluation.yml/badge.svg)](https://github.com/uzairkhatri/production-rag-reference/actions/workflows/rag-evaluation.yml)

Ingest a document, retrieve and rerank its chunks, return source citations, and run a retrieval regression gate. The default path runs locally without an API key, model download, vector database, or paid service.

This demonstrates **production-oriented design decisions**, not a production-ready deployment. Its default generator copies retrieved text; it is not an LLM.

## Why this exists

A plausible answer alone does not tell you whether retrieval found the right evidence or whether a change broke the pipeline. This reference separates those responsibilities so they can be inspected and tested independently.

| Engineering question | What you can inspect here |
| --- | --- |
| Where did an answer come from? | Source metadata carried from chunks into response citations |
| Which component selected the evidence? | Separate retrieval and reranking implementations |
| Did retrieval regress? | A labelled fixture, Recall@5 / MRR, and a failing exit code |
| What happens without lexical evidence? | Deterministic abstention with no citations |
| Where does a model provider belong? | A generator interface and optional OpenAI adapter |
| How can a request be identified? | A response trace ID and application logging calls |

## Try it locally

Requires Git and Python 3.10 or newer. Run from the repository root. Start a fresh server in **local** mode; the walkthrough writes one public sample document into its in-memory index.

### Windows PowerShell

```powershell
git clone https://github.com/uzairkhatri/production-rag-reference.git
cd production-rag-reference
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e .
$env:RAG_GENERATOR_PROVIDER = "local"
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, open the same repository directory and run:

```powershell
.\.venv\Scripts\python.exe scripts/demo.py
```

<details>
<summary>macOS / Linux</summary>

```bash
git clone https://github.com/uzairkhatri/production-rag-reference.git
cd production-rag-reference
python3 -m venv .venv
.venv/bin/python -m pip install -e .
RAG_GENERATOR_PROVIDER=local .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal, open the same repository directory and run:

```bash
.venv/bin/python scripts/demo.py
```

</details>

The walkthrough prints actual JSON responses and checks ingestion, a citation to the sample document, a UUID trace ID, and zero-evidence abstention. Success ends with:

```text
PASS: ingestion, source citation, trace ID, and zero-evidence abstention
```

Explore the API at [localhost:8000/docs](http://127.0.0.1:8000/docs). If port 8000 is occupied, use another port in both the server command and `scripts/demo.py --port 8001`. Stop with Ctrl+C; documents are not persisted.

See the [walkthrough](docs/demo.md) for individual requests and what each response proves.

## Architecture

```text
Document + source metadata
          |
     Word chunking
          |
 In-memory lexical retrieval -> Lexical reranking
                                      |
                             Context selection
                                      |
                         Generator (local / optional OpenAI)
                                      |
                         Answer + citations + trace ID

Labelled queries -> retrieval + reranking -> Recall@5 / MRR -> CI gate
```

| Boundary | Current implementation | Deliberate tradeoff |
| --- | --- | --- |
| Ingestion | Word chunks with overlap and source metadata | Text payloads only; no PDF loader or ingestion queue |
| Retrieval | Token overlap plus cosine similarity over token-frequency vectors | Deterministic; no dense embeddings or semantic search |
| Reranking | Lexical overlap with chunk title and text | No learned reranker or extra model dependency |
| Local generation | Concatenated source excerpts, limited by a word budget | Exercises the contract without model quality or API cost |
| Optional generation | OpenAI adapter behind the generator interface | Separate installation and credentials; offline tests use a fake client |
| Evaluation | 10 synthetic documents and 24 labelled questions, with per-case regression floors | Exercises competing evidence and failure cases; not a production accuracy benchmark |

The name `InMemoryHybridRetriever` refers to the two lexical scoring signals above, not a vector database. Interfaces live in [app/ports.py](app/ports.py); composition is in [app/service.py](app/service.py) and [app/factory.py](app/factory.py). Replacing retrieval or reranking requires code changes, not an environment switch.

## Verify it

Windows PowerShell, from the repository root:

```powershell
$env:RAG_GENERATOR_PROVIDER = "local"
.\.venv\Scripts\python.exe -m pip install -e ".[dev]"
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts/run_eval.py --baseline evals/baseline.json --output reports/evaluation.json --summary-output reports/evaluation.md
```

On macOS / Linux, set `export RAG_GENERATOR_PROVIDER=local` and replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`.

The bundled suite contains 8 direct questions, 8 paraphrases, 2 multi-document questions, and 6 unsupported questions. Two topic-overlapping distractor documents compete with the runbooks. Initial measured results:

| Measure | Result |
| --- | --- |
| Recall@5, answerable questions only | 0.9444 |
| MRR, answerable questions only | 0.9167 |
| Unsupported questions correctly rejected | 1 / 6 |
| Answerable questions not rejected | 18 / 18 |

**Strong retrieval does not imply safe abstention.** The suite exposes a missed budget paraphrase, a lower-ranked provider paraphrase, and five unsupported questions that receive source text instead of abstention. These remain visible failures even when the regression gate passes. This small, authored synthetic suite is not a production accuracy or safety benchmark. See [measured results and known gaps](docs/evaluation-results.md).

CI requires Recall@5 and MRR of at least 0.80 and rejects individual regressions against the committed baseline. It publishes JSON evidence and a readable summary, including known failures. To demand correct abstention on every unsupported question, add `--min-abstention 1`; **that stricter check currently fails**, intentionally exposing the existing limitation.

Tests cover metrics, invalid fixtures, threshold validation, baseline compatibility, per-case regression detection, deliberately broken retrieval/abstention, the API walkthrough, and existing pipeline behaviors. CI runs tests on Python 3.10-3.13 and the evaluation gate on pull requests and main. See [evaluation commands and baseline review](docs/evaluation-gate.md).

## Limits to understand before deployment

- **Not a hosted service:** no authentication, tenant isolation, rate limits, durable storage, or document deletion API. Keep the demo bound to loopback. Multiple workers do not share an index.
- **Citations are metadata, not factual verification:** a cited chunk does not prove each claim follows from it. Mixed relevant and irrelevant chunks can both enter the answer. Token-overlap grounding is only a heuristic.
- **Abstention is lexical:** empty retrieval or all-zero scores trigger abstention. An unsupported question sharing words with a document may still produce an answer.
- **Budgets are approximate:** token usage is estimated from words before trimming, not measured provider usage. Trimming hit counts is not a strict token or spending cap. The local word limit does not impose an equivalent input-context limit on the optional provider.
- **Observability is a starting point:** trace IDs and logging calls exist; log formatting, export, dashboards, and distributed tracing are not configured.
- **Provider behavior needs deployment testing:** offline tests do not validate live output, billing, timeouts, or every SDK error/retry path.
- **Updates need care:** re-ingesting an ID replaces matching chunk IDs, but shorter replacements can leave old trailing chunks behind. Restart the demo for a clean index.

Before using this pattern with real users, add representative positive and negative evaluation cases, persistent access-controlled retrieval, bounded resource usage, and application-specific security and failure tests.

## Explore the code and decisions

- [End-to-end walkthrough](docs/demo.md)
- [Architecture and boundaries](docs/architecture.md)
- [Retrieval gate and limitations](docs/evaluation-gate.md)
- [Measured results and known failures](docs/evaluation-results.md)
- [Evaluation strategy](docs/evaluation.md)
- [Provider interfaces](docs/provider-boundaries.md)
- [Optional OpenAI setup](docs/openai-provider.md)

`.env.example` documents provider settings; the application does **not** automatically load `.env` files. Set environment variables explicitly before starting the server. Local mode needs no credentials.

Built by [Uzair Khatri](https://uzairkhatri.com). Licensed under [MIT](LICENSE).
