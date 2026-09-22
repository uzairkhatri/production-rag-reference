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
        self.last_request=kwargs
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


def test_missing_value_abstains_without_calling_provider():
    client = FakeClient()
    sources = [Hit(Chunk("c1", "d1", "SDK", "synthetic://sdk", "Orion SDK installation notes."), 1)]
    result = OpenAIGenerator(client=client, model="test").generate(
        "Which Orion SDK version is installed?", sources, 100)
    assert not result.used
    assert result.evidence_reason == "missing_value_evidence:version"
    assert client.responses.calls == 0


def test_provider_uses_only_checked_bounded_context():
    client = FakeClient()
    sources = [Hit(Chunk("c1", "d1", "SDK", "synthetic://sdk", "Orion SDK version 2.7.1. EXCLUDED"), 1),
               Hit(Chunk("c2", "d2", "Other", "synthetic://other", "Unrelated source"), 0)]
    result = OpenAIGenerator(client=client, model="test").generate(
        "Which Orion SDK version is installed?", sources, 4)
    assert client.responses.calls == 1
    assert "2.7.1" in client.responses.last_request["input"]
    assert "EXCLUDED" not in client.responses.last_request["input"]
    assert "Unrelated source" not in client.responses.last_request["input"]
    assert [source.chunk.document_id for source in result.used] == ["d1"]


def test_value_after_truncation_cannot_trigger_provider_call():
    client = FakeClient()
    sources = [Hit(Chunk("c1", "d1", "SDK", "synthetic://sdk", "Orion SDK notes. Version 2.7.1 is installed."), 1)]
    result = OpenAIGenerator(client=client, model="test").generate(
        "Which Orion SDK version is installed?", sources, 3)
    assert not result.used and client.responses.calls == 0
