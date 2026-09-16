# Retrieval evaluation gate

The repository includes a small labelled evaluation dataset and a deterministic regression runner.

```bash
python scripts/run_eval.py --min-recall 0.80 --min-mrr 0.80
```

The runner reports Recall@5 and Mean Reciprocal Rank and exits non-zero when either configured threshold is missed. GitHub Actions runs the same check on pull requests.

The bundled dataset is intentionally tiny: it demonstrates the architecture of an evaluation gate, not statistically meaningful production quality. A real deployment should maintain a representative, versioned dataset built from its own user intents and failure cases.
