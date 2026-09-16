from .retrieval import Hit, tokens

def rerank(question: str, hits: list[Hit]) -> list[Hit]:
    """Deterministic v0.1 reranker; replaceable by a cross-encoder/provider."""
    q = set(tokens(question))
    return sorted(
        hits,
        key=lambda hit: (-len(q.intersection(tokens(hit.chunk.title + " " + hit.chunk.text))), -hit.score, hit.chunk.id),
    )
