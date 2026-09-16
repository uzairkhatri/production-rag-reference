# Architecture

## Request path

```text
POST /query
    |
    v
Hybrid Retriever
    |
    v
Reranker
    |
    v
Context / Token Budget
    |
    v
Generator
    |
    +--> Citations
    +--> Trace ID / logs
    +--> Evaluation hooks
```

## Provider boundaries

v0.1 deliberately runs without external services. `InMemoryHybridRetriever` and `ExtractiveGenerator` are local defaults, not claims that lexical retrieval or extractive generation are sufficient for every production workload.

The important architectural property is that retrieval, reranking and generation are separate boundaries. A deployment can replace them with OpenSearch/pgvector/Pinecone/Qdrant, a cross-encoder, and an LLM provider without changing the HTTP contract.

## Production concerns represented

- grounded source metadata survives ingestion through citations
- retrieval and reranking are independently testable
- query responses include a trace identifier
- context has an explicit budget
- unknown/zero-evidence queries fail closed rather than inventing an answer
- external-provider retries/timeouts belong at provider adapters, not in business logic
