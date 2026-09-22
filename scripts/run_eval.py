"""Run the offline benchmark; exit 1 for regressions, 2 for invalid inputs."""

import argparse
import json
import math
from pathlib import Path

from app.benchmark import (
    Baseline, Corpus, Dataset, baseline_from_report, baseline_regressions, evaluate_benchmark,
)


def rate(value: str) -> float:
    number = float(value)
    if not math.isfinite(number) or not 0 <= number <= 1:
        raise argparse.ArgumentTypeError("threshold must be a finite number between 0 and 1")
    return number


def markdown_summary(report: dict) -> str:
    summary = report["summary"]
    lines = ["# Offline RAG Evaluation", "",
             f"Regression gate: **{'PASS' if report['gate']['passed'] else 'FAIL'}**. "
             "This is not a production-readiness assessment.", "",
             f"Corpus: {report['corpus']['documents']} synthetic documents; "
             f"{summary['answerable_cases']} answerable and {summary['unsupported_cases']} unsupported questions.",
             "", "| Measure | Result |", "| --- | --- |",
             f"| Recall@{report['configuration']['top_k']} | {summary['recall_at_k']:.4f} |",
             f"| MRR | {summary['mrr']:.4f} |",
             f"| Unsupported-question abstention | {summary['unsupported_abstention_rate']:.4f} |",
             "", "## Cases With Failures", "",
             "Known failures remain visible even when the regression gate passes.", "",
             "| Case | Failure |", "| --- | --- |"]
    for row in report["cases"]:
        if row["failures"]:
            case_id = row["id"].replace("|", "\\|").replace("\n", " ")
            lines.append(f"| {case_id} | {', '.join(row['failures'])} |")
    if not summary["failed_case_ids"]:
        lines.append("| None | No measured failures |")
    if report["gate"]["failures"]:
        lines.extend(["", "## Gate Failures", ""])
        lines.extend(f"- {failure}" for failure in report["gate"]["failures"])
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", type=Path, default=Path("evals/corpus.json"))
    parser.add_argument("--dataset", type=Path, default=Path("evals/dataset.json"))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--min-recall", type=rate, default=0.8)
    parser.add_argument("--min-mrr", type=rate, default=0.8)
    parser.add_argument("--min-abstention", type=rate,
                        help="Optional minimum abstention rate on unsupported questions")
    baseline_options = parser.add_mutually_exclusive_group()
    baseline_options.add_argument("--baseline", type=Path, help="Reviewed per-case regression floors")
    baseline_options.add_argument("--write-baseline", type=Path,
                                  help="Explicitly write a candidate baseline for human review")
    parser.add_argument("--output", type=Path, help="Write the full per-case JSON report")
    parser.add_argument("--summary-output", type=Path, help="Write a readable Markdown summary")
    args = parser.parse_args(argv)
    try:
        inputs = [args.corpus, args.dataset] + ([args.baseline] if args.baseline else [])
        outputs = [path for path in (args.output, args.summary_output, args.write_baseline) if path is not None]
        resolved_outputs = [path.resolve() for path in outputs]
        if len(resolved_outputs) != len(set(resolved_outputs)) or any(
            path in resolved_outputs for path in (item.resolve() for item in inputs)
        ):
            raise ValueError("Output paths must be distinct and must not overwrite input files")
        corpus = Corpus.model_validate_json(args.corpus.read_text(encoding="utf-8"))
        dataset = Dataset.model_validate_json(args.dataset.read_text(encoding="utf-8"))
        report = evaluate_benchmark(corpus, dataset, args.top_k)
        failures = []
        summary = report["summary"]
        for metric, threshold in (("recall_at_k", args.min_recall), ("mrr", args.min_mrr),
                                  ("unsupported_abstention_rate", args.min_abstention)):
            if threshold is not None and summary[metric] < threshold:
                failures.append(f"{metric}: {summary[metric]:.4f} < {threshold:.4f}")
        if args.baseline:
            baseline = Baseline.model_validate_json(args.baseline.read_text(encoding="utf-8"))
            failures.extend(baseline_regressions(report, baseline))
        report["gate"] = {
            "passed": not failures,
            "baseline_checked": args.baseline is not None,
            "thresholds": {"min_recall": args.min_recall, "min_mrr": args.min_mrr,
                           "min_abstention": args.min_abstention},
            "failures": failures,
            "note": "Gate success does not mean every case passed; inspect failed_case_ids and cases.",
        }
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        if args.summary_output:
            args.summary_output.parent.mkdir(parents=True, exist_ok=True)
            args.summary_output.write_text(markdown_summary(report), encoding="utf-8")
        if args.write_baseline:
            args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
            args.write_baseline.write_text(
                baseline_from_report(report).model_dump_json(indent=2) + "\n", encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 1 if failures else 0
    except (OSError, ValueError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    raise SystemExit(main())
