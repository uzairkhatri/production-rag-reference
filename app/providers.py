import time
from dataclasses import dataclass
from typing import Callable,TypeVar
T=TypeVar("T")

@dataclass(frozen=True)
class ProviderPolicy:
    timeout_seconds:float=15.0
    max_retries:int=2
    backoff_seconds:float=0.05

def with_retries(call:Callable[[],T],policy:ProviderPolicy)->T:
    last=None
    for attempt in range(policy.max_retries+1):
        try:return call()
        except (TimeoutError,ConnectionError) as exc:
            last=exc
            if attempt==policy.max_retries:raise
            time.sleep(policy.backoff_seconds*(2**attempt))
    raise last  # pragma: no cover
