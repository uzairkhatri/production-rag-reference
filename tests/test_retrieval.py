from app.ingestion import Chunk
from app.retrieval import InMemoryHybridRetriever
from app.reranking import rerank

def test_retrieval_and_reranking_are_deterministic():
    r=InMemoryHybridRetriever()
    r.add([Chunk("1","d1","RAG reliability","s1","timeouts retries fallback for model calls"),Chunk("2","d2","Cooking","s2","pasta tomato basil")])
    hits=rerank("RAG retries and timeouts",r.search("RAG retries and timeouts",2))
    assert hits[0].chunk.document_id=="d1"
