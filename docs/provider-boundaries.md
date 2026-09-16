# Provider boundaries

The HTTP API does not depend directly on a vector database, reranker or LLM SDK.

v0.2 defines explicit ports for retrieval, reranking, generation and embeddings. Provider adapters should implement those ports and own provider-specific authentication, timeout, retry/backoff, rate-limit and usage translation.

This keeps business logic testable without network access and makes provider replacement an infrastructure decision rather than an API rewrite.

## Failure policy

Only transient connection and timeout failures are candidates for bounded retries. Authentication, validation and policy failures should surface immediately rather than being retried blindly.

## Cost

Usage is represented separately from retrieval/generation behavior. Real adapters should use provider-reported token usage when available; the local implementation can only estimate it.
