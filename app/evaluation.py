from dataclasses import dataclass
from .retrieval import Hit, tokens

@dataclass(frozen=True)
class RetrievalMetrics:
    top_score: float
    query_coverage: float

def retrieval_metrics(question: str, hits: list[Hit]) -> RetrievalMetrics:
    if not hits:
        return RetrievalMetrics(0.0, 0.0)
    q=set(tokens(question))
    covered=set()
    for hit in hits:
        covered |= q.intersection(tokens(hit.chunk.text))
    return RetrievalMetrics(hits[0].score, len(covered)/max(1,len(q)))
