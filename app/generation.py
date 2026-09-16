from dataclasses import dataclass
from .retrieval import Hit

@dataclass(frozen=True)
class Generated:
    text: str
    used: tuple[Hit, ...]

class ExtractiveGenerator:
    """Safe local default: synthesizes only from retrieved text."""
    def generate(self, question: str, hits: list[Hit], max_words: int) -> Generated:
        if not hits or all(hit.score == 0 for hit in hits):
            return Generated("I don't have enough grounded context to answer that question.", ())
        selected=[]; remaining=max_words
        for hit in hits:
            words=hit.chunk.text.split()
            if remaining <= 0: break
            selected.append((hit, " ".join(words[:remaining])))
            remaining -= min(len(words), remaining)
        body=" ".join(text for _,text in selected)
        return Generated(body, tuple(hit for hit,_ in selected))
