from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    chunk_words: int = 120
    chunk_overlap: int = 20
    max_context_words: int = 700
    request_timeout_seconds: float = 15.0
    max_retries: int = 2
    token_budget: int = 4000

settings = Settings()
