# Offline evaluation gate

The runner loads [corpus.json](../evals/corpus.json) and [dataset.json](../evals/dataset.json), indexes all documents, and evaluates each labelled question. It is deterministic and always uses the local extractive generator, even if `RAG_GENERATOR_PROVIDER=openai` is set. No server, credentials, model download, or paid call is needed.

## Run the same gate as CI

After [installation](../README.md#try-it-locally), run from the repository root:

```powershell
.\.venv\Scripts\python.exe scripts/run_eval.py --baseline evals/baseline.json --min-abstention 0.80 --output reports/evaluation.json --summary-output reports/evaluation.md
.\.venv\Scripts\python.exe scripts/run_eval.py --corpus evals/evidence-corpus.json --dataset evals/evidence-dataset.json --baseline evals/evidence-baseline.json --min-abstention 0.75 --output reports/evidence.json --summary-output reports/evidence.md
```

On macOS / Linux replace `.\.venv\Scripts\python.exe` with `.venv/bin/python`. Output files are generated and ignored by Git. The complete report is also printed as JSON.

The default thresholds remain Recall@5 >= 0.80 and MRR >= 0.80. Supplying `--baseline` also checks every case against its approved recall, reciprocal rank, and abstention decision. An improvement elsewhere cannot cancel a per-case regression. Without `--baseline`, only the requested aggregate thresholds are gated.

Exit codes: **0** for satisfied gates, **1** for measured threshold failures or regressions, **2** for invalid inputs or file errors. JSON and Markdown reports are still written when a measured gate fails. Invalid inputs are rejected before reporting scores.

GitHub Actions runs both suites on pull requests and main, publishes summaries, and uploads `rag-evaluation-original` and `rag-evaluation-value-evidence` artifacts even on gate failure when reports exist. Its minimum unsupported-abstention rates are 0.80 and 0.75 respectively. Both suites retain per-case checks, including supported questions, to prevent an always-abstain strategy from passing.

## Read the metrics correctly

- **Recall@K:** fraction of required document IDs present in the top K retrieved chunks after reranking; averaged over answerable cases. Duplicate chunks cannot increase recall.
- **MRR:** mean reciprocal position of the first relevant chunk, also over answerable cases. Repeated chunks still occupy rank positions. It does not measure whether all evidence is present; multi-document recall does that.
- **Unsupported abstention rate:** fraction of unsupported questions for which the local generator returns no used evidence. These cases have `null` retrieval metrics and are excluded from retrieval averages.
- **Answerable non-abstention rate:** checks that the generator does not reject supported questions. It does not validate the content of an answer.
- **Case failures:** missing required documents, a non-relevant first result, an unsupported question answered, or an answerable question rejected. They remain listed even when accepted by the regression baseline.

The report includes category-level retrieval scores, ranked document/chunk IDs, missing IDs, expected/observed abstention, evidence-check reasons, and a short answer excerpt. Retrieval retains zero-score hits for scoring, but generation now excludes them. Retrieval presence alone is not evidence sufficiency.

## Known gaps are not hidden

The historical [results](evaluation-results.md) included two paraphrase failures and five unsupported questions answered. The [value evidence guard](evidence-check.md) fixes four of those unsupported cases; the loan-policy question and retrieval weaknesses remain. The additional suite retains unsupported owner-name and backup-location failures. Baselines record current behavior, not deployment approval. Only four abstention flags in the original baseline were strengthened; no fixture labels or retrieval floors were weakened.

For a strict unsupported-question gate:

```powershell
.\.venv\Scripts\python.exe scripts/run_eval.py --baseline evals/baseline.json --min-abstention 1 --output reports/strict.json
```

This still exits **1**, because 5 of 6 unsupported questions are rejected, not all six. A future fix should improve the remaining decision without breaking supported cases. Never remove difficult questions merely to obtain a green check.

## Review and update a baseline

The baseline includes a SHA-256 fingerprint of the complete corpus, labels/questions, and evaluation configuration. Changed fixtures, top K, chunking settings, or local word budget require explicit review rather than silent comparison against unrelated results. Case IDs and metric applicability must also match.

To propose a new baseline after an intentional change:

```powershell
.\.venv\Scripts\python.exe scripts/run_eval.py --write-baseline reports/candidate-baseline.json --output reports/candidate-report.json --summary-output reports/candidate-summary.md
```

This writes measured floors, **not an approval**. It can record failures. Inspect every changed label, metric, and failure, explain the reason in the PR, and only then replace `evals/baseline.json` with the reviewed candidate. Prefer recording improvements as stronger floors. Do not regenerate baselines automatically in CI or weaken floors simply because a test failed.

## Custom fixtures

Use `--corpus path/to/corpus.json --dataset path/to/dataset.json`. The versioned schema and [labelling policy](../evals/README.md) require unique IDs, nonblank fields, and both answerable and unsupported cases. Answerable labels must name documents in the corpus; unsupported cases must have no relevance labels. Empty or inconsistent data, invalid top K, and non-finite/out-of-range thresholds are errors, not passing evaluations.

The original three-case list format is replaced by the versioned object format; custom datasets must migrate. A missing labelled document is now an input error, not a valid negative test. To test a retrieval regression, leave the relevant document in the corpus and change which chunks retrieval returns; automated tests exercise that failure path.

## Scope

These are authored synthetic fixtures, not customer traffic or a held-out production benchmark. They do not establish factual accuracy, citation correctness, prompt-injection resistance, access control, latency, provider reliability, or cost. The runner exercises retrieval/reranking/local generation directly, not HTTP or service-level budget trimming. All bundled documents fit in one chunk; tests additionally cover duplicate-chunk metric behavior. Expand to realistic multi-chunk documents and independently labelled queries before drawing deployment conclusions.
