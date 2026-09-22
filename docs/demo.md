# End-to-end walkthrough

Use the [README setup](../README.md#try-it-locally) to install the project and start a fresh local-mode server. No API key or model download is needed. Keep it bound to `127.0.0.1`; the API has no authentication.

## Run the checked walkthrough

In a second terminal at the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/demo.py
```

On macOS / Linux:

```bash
.venv/bin/python scripts/demo.py
```

This uses Python's standard-library HTTP client. It reads the public text fixture, sends it to the API, and checks:

1. `GET /health` reports `ok`.
2. `POST /documents` produces at least one chunk with the expected document ID.
3. `POST /query` returns an answer with a citation to that document and a valid UUID trace ID.
4. An intentionally unmatched token returns the abstention message and no citations.

The script prints real responses followed by a `PASS` line. Failed checks or an unavailable server produce a nonzero exit code. Use `--port 8001` when starting the API on another port.

Use a fresh server: existing documents can change retrieval ordering. This checks integration, not factual accuracy. The script does not configure the server's provider; set `RAG_GENERATOR_PROVIDER=local` **before starting the server** to avoid a paid model call.

## Inspect individual requests

Open [interactive API docs](http://127.0.0.1:8000/docs), expand an endpoint, and use **Try it out**.

For `POST /documents`, use:

```json
{
  "id": "rag-architecture",
  "title": "Production RAG",
  "source": "https://example.test/architecture",
  "text": "Production RAG measures retrieval quality, preserves source metadata for citations, traces requests and applies explicit reliability and cost controls."
}
```

Expected status: `201`. Expected response:

```json
{"document_id": "rag-architecture", "chunks": 1}
```

For `POST /query`:

```json
{"question": "What controls does production RAG use?", "top_k": 1}
```

In local mode, `answer` is copied from retrieved text. `citations` contain the document ID, title, source, chunk ID, and an excerpt. `trace_id` changes per request; `retrieved` counts selected hits and `estimated_input_tokens` is a word-based estimate, not billing data. If you ran the automated walkthrough first, its similar sample may be selected instead.

To check the no-evidence path:

```json
{"question": "zxqvunsupportedtoken", "top_k": 1}
```

Against only the supplied samples, this returns:

```text
I don't have enough grounded context to answer that question.
```

The response has `citations: []`. This tests zero lexical overlap, not whether the system recognizes every unanswerable natural-language question.

## Tests and retrieval evaluation

Follow [Verify it](../README.md#verify-it) for test installation and commands. The evaluation command does not need a running API; it creates its own index.

The [retrieval gate](evaluation-gate.md) fails when Recall@5 or MRR misses a configured threshold. Its three-question, one-document fixture is deliberately a smoke test.

## Optional provider

See [OpenAI setup](openai-provider.md) after the local walkthrough works. This is a separate, credentialed path that may incur charges. Offline tests use an injected fake client; they do not establish live provider quality or reliability.

The application does not automatically load `.env` files. Restart after changing environment variables. Stop with Ctrl+C when finished; restarting clears in-memory documents.
