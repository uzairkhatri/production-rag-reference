from urllib.error import URLError

import pytest
from fastapi.testclient import TestClient

from app import service
from app.generation import ExtractiveGenerator
from app.main import app
from app.retrieval import InMemoryHybridRetriever
from scripts import demo


def test_walkthrough_against_api(monkeypatch):
    monkeypatch.setattr(service, "retriever", InMemoryHybridRetriever())
    monkeypatch.setattr(service, "generator", ExtractiveGenerator())
    with TestClient(app) as client:
        def request(base_url, path, payload=None):
            response = client.get(path) if payload is None else client.post(path, json=payload)
            response.raise_for_status()
            return response.json()

        monkeypatch.setattr(demo, "request", request)
        result = demo.run_demo("http://127.0.0.1:8000")
        assert result["ingestion"]["chunks"] == 1
        assert result["answer"]["citations"][0]["source"].startswith("local://")
        assert result["no_evidence"]["citations"] == []


def test_cli_reports_connection_failure(monkeypatch, capsys):
    def unavailable(base_url):
        raise URLError("Connection refused")

    monkeypatch.setattr(demo, "run_demo", unavailable)
    assert demo.main([]) == 1
    assert "Start a fresh local-mode API" in capsys.readouterr().err


def test_cli_rejects_invalid_port():
    with pytest.raises(SystemExit) as error:
        demo.main(["--port", "0"])
    assert error.value.code == 2


def test_failed_check_is_not_silently_accepted():
    with pytest.raises(ValueError, match="Missing citation"):
        demo.require(False, "Missing citation")
