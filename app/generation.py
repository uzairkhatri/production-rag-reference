from dataclasses import dataclass
from .evidence import ABSTENTION, select_evidence
from .retrieval import Hit

@dataclass(frozen=True)
class Generated:
    text: str
    used: tuple[Hit, ...]
    evidence_reason: str = "not_reported"

class ExtractiveGenerator:
    """Local excerpt generator with a bounded value-presence guard."""
    def generate(self, question: str, hits: list[Hit], max_words: int) -> Generated:
        evidence = select_evidence(question, hits, max_words)
        if not evidence.passages:
            return Generated(ABSTENTION, (), evidence.reason)
        body = " ".join(passage.text for passage in evidence.passages)
        return Generated(body, tuple(passage.hit for passage in evidence.passages), evidence.reason)
