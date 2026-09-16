# Evaluation strategy

RAG quality should be split into retrieval and answer quality.

## Retrieval

Measure whether relevant evidence reaches the context window. Useful metrics include Recall@K, MRR and nDCG against a labelled query set.

## Generation

Measure groundedness, citation correctness, answer relevance and abstention behavior. Model-based judges can help, but should be calibrated against human-labelled examples.

## Regression gate

Keep a versioned evaluation dataset and compare candidate changes against the current baseline. A retrieval or prompt change should not ship merely because a few hand-tested answers look better.
