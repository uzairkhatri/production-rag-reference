from dataclasses import dataclass
from .retrieval import Hit

@dataclass(frozen=True)
class EvalCase:
    question: str
    relevant_document_ids: tuple[str, ...]

@dataclass(frozen=True)
class EvalResult:
    cases: int
    recall_at_k: float
    mrr: float

def score_case(hits: list[Hit], relevant: tuple[str, ...]) -> tuple[float, float]:
    ids=[h.chunk.document_id for h in hits]
    target=set(relevant)
    recall=len(target.intersection(ids))/max(1,len(target))
    rr=0.0
    for rank,doc_id in enumerate(ids,1):
        if doc_id in target:
            rr=1.0/rank
            break
    return recall,rr

def evaluate_cases(cases: list[EvalCase], search) -> EvalResult:
    if not cases:return EvalResult(0,0.0,0.0)
    recall=0.0;mrr=0.0
    for case in cases:
        hits=search(case.question)
        r,rr=score_case(hits,case.relevant_document_ids)
        recall+=r;mrr+=rr
    n=len(cases)
    return EvalResult(n,recall/n,mrr/n)
