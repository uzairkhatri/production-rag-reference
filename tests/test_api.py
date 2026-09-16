from fastapi.testclient import TestClient
from app.main import app

client=TestClient(app)

def test_health():
    assert client.get("/health").json()=={"status":"ok"}

def test_ingest_then_query_returns_citation():
    response=client.post("/documents",json={"id":"api-doc","title":"Production RAG","source":"https://example.test/rag","text":"Production RAG uses retrieval evaluation citations observability retries and cost controls."})
    assert response.status_code==201
    result=client.post("/query",json={"question":"What does production RAG use?","top_k":3})
    assert result.status_code==200
    body=result.json()
    assert body["citations"]
    assert body["citations"][0]["document_id"]=="api-doc"
