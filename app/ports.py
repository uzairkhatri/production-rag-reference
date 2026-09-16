from typing import Protocol
from .ingestion import Chunk
from .retrieval import Hit
from .generation import Generated

class Retriever(Protocol):
    def add(self,chunks:list[Chunk])->None: ...
    def search(self,query:str,top_k:int)->list[Hit]: ...

class Reranker(Protocol):
    def rank(self,question:str,hits:list[Hit])->list[Hit]: ...

class Generator(Protocol):
    def generate(self,question:str,hits:list[Hit],max_words:int)->Generated: ...

class Embedder(Protocol):
    def embed(self,texts:list[str])->list[list[float]]: ...
