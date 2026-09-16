from fastapi import FastAPI
from .models import DocumentIn, QueryIn, QueryOut
from .service import ingest, query

app=FastAPI(title="Production RAG Reference",version="0.1.0")

@app.get("/health")
def health() -> dict[str,str]:
    return {"status":"ok"}

@app.post("/documents",status_code=201)
def add_document(document: DocumentIn) -> dict[str,int|str]:
    return {"document_id":document.id,"chunks":ingest(document)}

@app.post("/query",response_model=QueryOut)
def ask(payload: QueryIn) -> QueryOut:
    return query(payload.question,payload.top_k)
