import argparse,json
from pathlib import Path
from app.eval_runner import EvalCase,evaluate_cases
from app.ingestion import chunk_document
from app.models import DocumentIn
from app.retrieval import InMemoryHybridRetriever
from app.reranking import LexicalReranker

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--dataset",default="evals/dataset.json")
    p.add_argument("--min-recall",type=float,default=0.8)
    p.add_argument("--min-mrr",type=float,default=0.8)
    args=p.parse_args()
    text=Path("examples/documents/production-rag.txt").read_text()
    doc=DocumentIn(id="production-rag",title="Production RAG",source="local://production-rag",text=text)
    retriever=InMemoryHybridRetriever();retriever.add(chunk_document(doc))
    reranker=LexicalReranker()
    raw=json.loads(Path(args.dataset).read_text())
    cases=[EvalCase(x["question"],tuple(x["relevant_document_ids"])) for x in raw]
    result=evaluate_cases(cases,lambda q:reranker.rank(q,retriever.search(q,5)))
    print(json.dumps({"cases":result.cases,"recall_at_5":round(result.recall_at_k,4),"mrr":round(result.mrr,4)},indent=2))
    return 1 if result.recall_at_k<args.min_recall or result.mrr<args.min_mrr else 0

if __name__=="__main__":raise SystemExit(main())
