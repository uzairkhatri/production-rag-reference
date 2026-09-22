# Retrieval evaluation gate

The repository includes a small labelled evaluation dataset and a deterministic regression runner.

```bash
python scripts/run_eval.py --min-recall 0.80 --min-mrr 0.80
```

The runner reports Recall@5 and Mean Reciprocal Rank and exits non-zero when either configured threshold is missed. GitHub Actions runs the same check on pull requests.

Run from the repository root after installation. No server or API key is needed.

The dataset contains three questions, all pointing to `production-rag`, the only indexed document. Expected output:

```json
{"cases": 3, "recall_at_5": 1.0, "mrr": 1.0}
```

This demonstrates gate mechanics, not statistically meaningful production quality. The retriever retains zero-score hits, so a one-document corpus cannot meaningfully test ranking discrimination. These scores say nothing about answer correctness, model safety, latency, or operating cost.

For a real evaluation, expand both the indexed corpus in the runner and the labelled dataset. Include distractors, paraphrases, multi-document answers, and separately assessed unanswerable questions. A new `--dataset` changes labels and questions, not the indexed corpus. The runner does not measure abstention.

To inspect failure, use a temporary dataset whose `relevant_document_ids` names an absent document and pass its path with `--dataset`. Recall and MRR should be zero, and the process should exit with code 1 at the default thresholds. Do not replace real labels merely to obtain a passing score.
