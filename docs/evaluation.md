# Evaluation strategy

RAG quality should be split into retrieval and answer quality.

## What runs today

`scripts/run_eval.py` loads a versioned corpus and labelled questions: 10 synthetic documents, 18 answerable questions, and 6 unsupported questions. It reports Recall@5 and reciprocal rank on answerable questions, with separate direct/paraphrase/multi-document slices. Relevance is labelled by document ID; rank positions are the retrieved chunks, including repeated chunks from the same document.

The local extractive generator is exercised separately for its abstention decision. Unsupported questions do not contribute zeroes or automatic successes to retrieval averages. Reports include expected/retrieved IDs, missing evidence, ranks, an answer excerpt, and named failures. A non-abstaining answer on an answerable question is not proof that the answer is correct.

CI combines aggregate thresholds with per-case regression floors. Known failures remain in the report, not excluded from scoring. See [baseline policy](evaluation-gate.md), [fixture labels](../evals/README.md), and [measured results](evaluation-results.md).

The runner is always local, regardless of provider environment variables. It evaluates retrieval, reranking, and extractive generation directly, not the HTTP layer, service-level token trimming, or the optional OpenAI adapter. There is no model judge, nDCG, answer-quality benchmark, or load test.

The sections below describe how to extend evaluation for a real deployment, not additional capabilities already implemented here.

## Retrieval

Measure whether relevant evidence reaches the context window. Useful metrics include Recall@K, MRR and nDCG against a labelled query set.

## Generation

Measure groundedness, citation correctness, answer relevance and abstention behavior. Model-based judges can help, but should be calibrated against human-labelled examples.

## Regression gate

Keep a versioned evaluation dataset and compare candidate changes against the current baseline. A retrieval or prompt change should not ship merely because a few hand-tested answers look better.
