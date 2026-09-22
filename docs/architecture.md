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
- both generators share word-bounded context selection; token estimates and hit trimming are not strict spending caps
- zero-score chunks are excluded from generation and citations
- recognized numeric/version requests require value evidence before generation; general semantic sufficiency is not checked
- external-provider retries/timeouts belong at provider adapters, not in business logic

See the [deployment limitations](../README.md#limits-to-understand-before-deployment) for persistence, access control, index updates, logging, and provider-validation gaps.

The [evidence guard](evidence-check.md) lives inside both generator implementations so direct generator calls, the API, and local evaluation use the same check. It checks the actual truncated text, not excluded chunks or their titles. Failed checks return the existing abstention message with no citations and skip the provider request. Successful checks do not verify the generated answer.
