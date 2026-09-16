from dataclasses import dataclass
from .models import DocumentIn

@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    title: str
    source: str
    text: str

def chunk_document(doc: DocumentIn, size: int = 120, overlap: int = 20) -> list[Chunk]:
    words = doc.text.split()
    if not words:
        return []
    step = max(1, size - overlap)
    chunks = []
    for index, start in enumerate(range(0, len(words), step)):
        text = " ".join(words[start:start + size])
        if not text:
            break
        chunks.append(Chunk(f"{doc.id}:{index}", doc.id, doc.title, doc.source, text))
        if start + size >= len(words):
            break
    return chunks
