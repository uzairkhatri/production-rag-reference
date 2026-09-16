import os
from .generation import ExtractiveGenerator

def build_generator():
    provider=os.getenv("RAG_GENERATOR_PROVIDER","local").lower()
    if provider=="local":
        return ExtractiveGenerator()
    if provider=="openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise RuntimeError("OPENAI_API_KEY is required when RAG_GENERATOR_PROVIDER=openai")
        from .openai_adapter import OpenAIGenerator
        return OpenAIGenerator()
    raise ValueError(f"Unsupported RAG_GENERATOR_PROVIDER: {provider}")
