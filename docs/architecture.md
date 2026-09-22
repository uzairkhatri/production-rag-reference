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

- source metadata survives ingestion through citations; it does not verify answer claims
- retrieval and reranking are independently testable
- query responses include a trace identifier
- local generation has a word limit; token estimates and hit trimming are not strict spending caps
- empty retrieval or all-zero lexical scores trigger abstention; semantic sufficiency is not checked
- external-provider retries/timeouts belong at provider adapters, not in business logic

See the [deployment limitations](../README.md#limits-to-understand-before-deployment) for persistence, access control, index updates, logging, and provider-validation gaps.
