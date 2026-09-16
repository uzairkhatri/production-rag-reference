from types import SimpleNamespace
import pytest
from app.ingestion import Chunk
from app.openai_adapter import OpenAIGenerator
from app.providers import ProviderPolicy
from app.retrieval import Hit

class FakeResponses:
    def __init__(self,failures=0):
        self.failures=failures;self.calls=0
    def create(self,**kwargs):
        self.calls+=1
        if self.calls<=self.failures:raise ConnectionError("temporary")
        return SimpleNamespace(output_text="Grounded provider answer.")

class FakeClient:
    def __init__(self,failures=0):self.responses=FakeResponses(failures)

def hits():
    return [Hit(Chunk("c1","d1","Doc","https://example.test","Grounded source text."),1.0)]

def test_openai_adapter_uses_injected_client_without_api_key():
    client=FakeClient()
    result=OpenAIGenerator(client=client,model="test").generate("question",hits(),100)
    assert result.text=="Grounded provider answer." and result.used

def test_openai_adapter_retries_transient_failure():
    client=FakeClient(failures=1)
    policy=ProviderPolicy(max_retries=1,backoff_seconds=0)
    result=OpenAIGenerator(client=client,model="test",policy=policy).generate("question",hits(),100)
    assert result.text=="Grounded provider answer." and client.responses.calls==2
