from app.ingestion import chunk_document
from app.models import DocumentIn

def test_chunking_preserves_source_and_overlap():
    doc=DocumentIn(id="d1",title="Doc",source="local://doc",text=" ".join(str(i) for i in range(30)))
    chunks=chunk_document(doc,size=10,overlap=2)
    assert len(chunks)==4
    assert chunks[0].source=="local://doc"
    assert chunks[0].text.split()[-2:]==chunks[1].text.split()[:2]
