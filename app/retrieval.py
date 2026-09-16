import math
import re
from collections import Counter
from dataclasses import dataclass
from .ingestion import Chunk

WORD = re.compile(r"[a-zA-Z0-9_]+")

def tokens(text: str) -> list[str]:
    return [x.lower() for x in WORD.findall(text)]

@dataclass(frozen=True)
class Hit:
    chunk: Chunk
    score: float

class InMemoryHybridRetriever:
    """Local deterministic retriever.

    v0.1 combines lexical overlap and cosine similarity over hashed token
    vectors. The interface is deliberately replaceable by a production
    vector/keyword backend without changing the API layer.
    """
    def __init__(self) -> None:
        self._chunks: list[Chunk] = []

    def add(self, chunks: list[Chunk]) -> None:
        known = {c.id for c in chunks}
        self._chunks = [c for c in self._chunks if c.id not in known] + chunks

    @staticmethod
    def _cosine(a: Counter, b: Counter) -> float:
        dot = sum(v * b[k] for k, v in a.items())
        na = math.sqrt(sum(v*v for v in a.values()))
        nb = math.sqrt(sum(v*v for v in b.values()))
        return dot / (na * nb) if na and nb else 0.0

    def search(self, query: str, top_k: int) -> list[Hit]:
        q = Counter(tokens(query))
        qset = set(q)
        hits = []
        for chunk in self._chunks:
            ct = Counter(tokens(chunk.text))
            lexical = len(qset.intersection(ct)) / max(1, len(qset))
            semantic_proxy = self._cosine(q, ct)
            hits.append(Hit(chunk, 0.6 * lexical + 0.4 * semantic_proxy))
        return sorted(hits, key=lambda h: (-h.score, h.chunk.id))[:top_k]
