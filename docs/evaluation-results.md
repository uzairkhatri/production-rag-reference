# Initial expanded evaluation results

This page preserves the historical, pre-evidence-guard results at commit `e3338d1` (merged PR #7). For current results see the [value evidence comparison](evidence-check.md#measured-results). The original corpus and questions have not been removed or relabelled.

Measured on the then-current local retrieval/reranking/extractive-generation pipeline: 10 documents, 10 chunks, top K of 5, and 24 questions. This is a deterministic regression reference, not a claim about production accuracy or a live model benchmark.

## Results by question type

| Answerable slice | Cases | Recall@5 | MRR |
| --- | --- | --- | --- |
| Direct | 8 | 1.0000 | 1.0000 |
| Paraphrase | 8 | 0.8750 | 0.8125 |
| Multi-document | 2 | 1.0000 | 1.0000 |
| All answerable | 18 | 0.9444 | 0.9167 |

Unsupported questions are excluded from these averages. Only **1 of 6** unsupported questions triggers abstention. All 18 answerable questions receive source text; that measures non-abstention, not answer correctness.

## Failures worth inspecting

| Case | Observation |
| --- | --- |
| `provider-paraphrase` | Required source is ranked second, not first; reciprocal rank is 0.5 |
| `budget-paraphrase` | Required context-budget source is absent from the top five; recall and reciprocal rank are zero |
| `unsupported-sla` | Answers despite the corpus containing no exact uptime commitment |
| `unsupported-retention` | Answers despite no retention duration being specified |
| `unsupported-price` | Answers despite no model token price being specified |
| `unsupported-sdk` | Answers despite no installed SDK version being specified |
| `unsupported-finance` | Answers despite no loan eligibility policy being present |

The unrelated astronomy control correctly abstains. The contrast with the other unsupported questions exposes the limitation of treating word overlap as sufficient evidence. Responses copy source passages, but those passages do not answer the requested facts.

## What the gate does and does not establish

The initial suite passes the existing 0.80 aggregate retrieval thresholds and its reviewed per-case baseline. It **fails** a strict `--min-abstention 1` check. A passing regression gate means no measured case worsened from the recorded state; it does not mean all cases are correct or safe.

Tests deliberately break retrieval and abstention to verify that new regressions are detected, including cases where another score improves. They also reject inconsistent labels, empty datasets, incompatible baselines, and thresholds such as NaN that could otherwise disable comparisons.

## Reproduce and inspect

The generator at commit `e3338d1` reproduces the pre-guard behavior on the original fixtures. The [evaluation command](evaluation-gate.md#run-the-same-gate-as-ci) on the latest code now reports the improved behavior. Reports contain ranked IDs, missing evidence, abstention decisions, and excerpts; known failures remain visible even on passing runs.

Next engineering work should address semantic evidence sufficiency and paraphrase retrieval, then rerun this suite without deleting or relabelling inconvenient questions. Before production conclusions, add realistic multi-chunk corpora, independently labelled queries, answer/citation correctness checks, and application-specific security tests.
