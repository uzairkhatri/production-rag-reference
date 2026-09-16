from pydantic import BaseModel, Field

class DocumentIn(BaseModel):
    id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    text: str = Field(min_length=1)
    source: str = Field(min_length=1)

class QueryIn(BaseModel):
    question: str = Field(min_length=1)
    top_k: int = Field(default=4, ge=1, le=20)

class Citation(BaseModel):
    document_id: str
    title: str
    source: str
    chunk_id: str
    excerpt: str

class QueryOut(BaseModel):
    answer: str
    citations: list[Citation]
    trace_id: str
    retrieved: int
    estimated_input_tokens: int
