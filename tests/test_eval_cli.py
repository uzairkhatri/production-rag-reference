import json
from pathlib import Path
import subprocess
import sys

import pytest

from scripts.run_eval import main

ROOT = Path(__file__).resolve().parents[1]


def arguments():
    return ["--corpus", str(ROOT / "evals/corpus.json"),
            "--dataset", str(ROOT / "evals/dataset.json")]


def test_cli_writes_report_and_reviewable_baseline(tmp_path, capsys):
    baseline = tmp_path / "candidate.json"
    report = tmp_path / "report.json"
    summary = tmp_path / "summary.md"
    assert main(arguments() + ["--write-baseline", str(baseline), "--output", str(report),
                               "--summary-output", str(summary)]) == 0
    body = json.loads(report.read_text())
    assert json.loads(capsys.readouterr().out) == body
    assert body["gate"]["passed"]
    assert body["summary"]["failed_case_ids"]
    assert "Known failures remain visible" in summary.read_text()
    assert main(arguments() + ["--baseline", str(baseline)]) == 0


def test_strict_abstention_fails_and_preserves_report(tmp_path, capsys):
    output = tmp_path / "failed.json"
    assert main(arguments() + ["--min-abstention", "1", "--output", str(output)]) == 1
    report = json.loads(output.read_text())
    assert not report["gate"]["passed"]
    assert report["summary"]["unsupported_abstention_rate"] < 1
    assert "unsupported_abstention_rate" in report["gate"]["failures"][0]


def test_strict_retrieval_threshold_fails(tmp_path, capsys):
    assert main(arguments() + ["--min-recall", "1"]) == 1
    assert "recall_at_k" in json.loads(capsys.readouterr().out)["gate"]["failures"][0]


def test_case_regression_fails_cli_despite_passing_aggregate(tmp_path, capsys):
    baseline = json.loads((ROOT / "evals/baseline.json").read_text())
    baseline["cases"]["provider-paraphrase"]["reciprocal_rank"] = 1.0
    path = tmp_path / "stronger-baseline.json"
    path.write_text(json.dumps(baseline))
    assert main(arguments() + ["--baseline", str(path)]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["summary"]["recall_at_k"] >= 0.8
    assert report["summary"]["mrr"] >= 0.8
    assert report["gate"]["failures"] == [
        "provider-paraphrase: reciprocal_rank decreased from 1.0 to 0.5"]


def test_nonfinite_baseline_is_rejected(tmp_path):
    baseline = json.loads((ROOT / "evals/baseline.json").read_text())
    baseline["cases"]["retrieval-direct"]["recall_at_k"] = float("nan")
    path = tmp_path / "invalid-baseline.json"
    path.write_text(json.dumps(baseline))
    with pytest.raises(SystemExit) as error:
        main(arguments() + ["--baseline", str(path)])
    assert error.value.code == 2


@pytest.mark.parametrize("value", ["nan", "inf", "-0.1", "1.1"])
def test_invalid_threshold_cannot_disable_gate(value):
    with pytest.raises(SystemExit) as error:
        main(arguments() + ["--min-recall", value])
    assert error.value.code == 2


@pytest.mark.parametrize("value", ["0", "21"])
def test_invalid_top_k_rejected(value):
    with pytest.raises(SystemExit) as error:
        main(arguments() + ["--top-k", value])
    assert error.value.code == 2


def test_output_cannot_overwrite_input(tmp_path):
    corpus = tmp_path / "corpus.json"
    original = (ROOT / "evals/corpus.json").read_text()
    corpus.write_text(original)
    with pytest.raises(SystemExit) as error:
        main(["--corpus", str(corpus), "--output", str(corpus)])
    assert error.value.code == 2
    assert corpus.read_text() == original


def test_output_paths_must_differ(tmp_path):
    path = str(tmp_path / "same.json")
    with pytest.raises(SystemExit) as error:
        main(arguments() + ["--output", path, "--write-baseline", path])
    assert error.value.code == 2


def test_malformed_json_has_clear_nonzero_exit(tmp_path, capsys):
    path = tmp_path / "broken.json"
    path.write_text("{not-json")
    with pytest.raises(SystemExit) as error:
        main(["--corpus", str(path)])
    assert error.value.code == 2
    assert "Invalid JSON" in capsys.readouterr().err


def test_real_cli_exit_codes(tmp_path):
    command = [sys.executable, str(ROOT / "scripts/run_eval.py"), *arguments(),
               "--baseline", str(ROOT / "evals/baseline.json")]
    passing = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True, timeout=20)
    assert passing.returncode == 0, passing.stderr
    assert json.loads(passing.stdout)["gate"]["baseline_checked"]
    failing = subprocess.run(command + ["--min-abstention", "1"], cwd=tmp_path,
                             capture_output=True, text=True, timeout=20)
    assert failing.returncode == 1, failing.stderr
