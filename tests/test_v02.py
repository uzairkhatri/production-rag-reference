import pytest
from app.cost import estimate_usage
from app.grounding import citation_coverage
from app.providers import ProviderPolicy,with_retries

def test_retry_recovers_from_transient_failure():
    calls={"n":0}
    def flaky():
        calls["n"]+=1
        if calls["n"]<3:raise ConnectionError("temporary")
        return "ok"
    assert with_retries(flaky,ProviderPolicy(max_retries=2,backoff_seconds=0))=="ok"
    assert calls["n"]==3

def test_retry_does_not_hide_permanent_failure():
    with pytest.raises(TimeoutError):
        with_retries(lambda:(_ for _ in ()).throw(TimeoutError()),ProviderPolicy(max_retries=1,backoff_seconds=0))

def test_usage_estimate_is_explicit():
    usage=estimate_usage(1000,.01)
    assert usage.estimated_input_tokens==1330
    assert usage.estimated_cost_usd>0

def test_grounding_coverage():
    assert citation_coverage("retrieval needs citations",["retrieval produces citations"])>0.5
