# Evaluation strategy

RAG quality should be split into retrieval and answer quality.

## What runs today

`scripts/run_eval.py` measures document-level Recall@5 and reciprocal rank using three labelled questions and one indexed document. Tests also check individual behaviors, including zero-score abstention in the walkthrough. There is no model judge, nDCG, answer-quality benchmark, or load test.

The sections below describe how to extend evaluation for a real deployment, not additional capabilities already implemented here.

## Retrieval

Measure whether relevant evidence reaches the context window. Useful metrics include Recall@K, MRR and nDCG against a labelled query set.

## Generation

Measure groundedness, citation correctness, answer relevance and abstention behavior. Model-based judges can help, but should be calibrated against human-labelled examples.

## Regression gate

Keep a versioned evaluation dataset and compare candidate changes against the current baseline. A retrieval or prompt change should not ship merely because a few hand-tested answers look better.
