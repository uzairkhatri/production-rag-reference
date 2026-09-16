# End-to-end demo

## 1. Start locally

```bash
python -m pip install -e ".[dev]"
uvicorn app.main:app --reload
```

## 2. Ingest grounded evidence

```bash
curl -X POST http://127.0.0.1:8000/documents \
  -H "Content-Type: application/json" \
  -d '{"id":"rag-architecture","title":"Production RAG","source":"https://example.test/architecture","text":"Production RAG measures retrieval quality, preserves source metadata for citations, traces requests and applies explicit reliability and cost controls."}'
```

Example response:

```json
{"document_id":"rag-architecture","chunks":1}
```

## 3. Query

```bash
curl -X POST http://127.0.0.1:8000/query \
  -H "Content-Type: application/json" \
  -d '{"question":"What controls does production RAG use?","top_k":4}'
```

The response contains a grounded answer, citation metadata, a request trace ID, the number of retrieved chunks and estimated input tokens.

## 4. Run the retrieval gate

```bash
python scripts/run_eval.py --min-recall 0.80 --min-mrr 0.80
```

The command exits non-zero if Recall@5 or MRR falls below the configured threshold.

## 5. Switch generation provider

Local generation is the default. OpenAI is optional:

```bash
python -m pip install -e ".[openai]"
export RAG_GENERATOR_PROVIDER=openai
export OPENAI_API_KEY=...
uvicorn app.main:app --reload
```

The HTTP contract, retrieval pipeline, reranker and citation construction remain unchanged.
