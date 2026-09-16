import logging,uuid
from .config import settings
from .cost import estimate_usage
from .generation import ExtractiveGenerator
from .grounding import citation_coverage
from .ingestion import chunk_document
from .models import Citation,DocumentIn,QueryOut
from .reranking import LexicalReranker
from .retrieval import InMemoryHybridRetriever
logger=logging.getLogger("production_rag")
retriever=InMemoryHybridRetriever();reranker=LexicalReranker();generator=ExtractiveGenerator()
def ingest(doc:DocumentIn)->int:
    chunks=chunk_document(doc,settings.chunk_words,settings.chunk_overlap);retriever.add(chunks)
    logger.info("document_ingested",extra={"document_id":doc.id,"chunks":len(chunks)});return len(chunks)
def query(question:str,top_k:int)->QueryOut:
    trace_id=str(uuid.uuid4());hits=reranker.rank(question,retriever.search(question,top_k))
    words=sum(len(h.chunk.text.split()) for h in hits);usage=estimate_usage(words)
    if usage.estimated_input_tokens>settings.token_budget:hits=hits[:max(1,top_k//2)]
    generated=generator.generate(question,hits,settings.max_context_words)
    citations=[Citation(document_id=h.chunk.document_id,title=h.chunk.title,source=h.chunk.source,chunk_id=h.chunk.id,excerpt=h.chunk.text[:240]) for h in generated.used]
    grounded=citation_coverage(generated.text,[h.chunk.text for h in generated.used])
    logger.info("query_completed",extra={"trace_id":trace_id,"retrieved":len(hits),"citations":len(citations),"grounding_coverage":grounded,"estimated_tokens":usage.estimated_input_tokens})
    return QueryOut(answer=generated.text,citations=citations,trace_id=trace_id,retrieved=len(hits),estimated_input_tokens=usage.estimated_input_tokens)
