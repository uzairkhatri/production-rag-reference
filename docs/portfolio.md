# Engineering proof

| Concern | Evidence in this repository |
|---|---|
| API boundary | FastAPI ingestion, query and health endpoints |
| Grounding | source metadata preserved into citations |
| Retrieval | deterministic local hybrid retrieval behind a replaceable port |
| Reranking | explicit independently replaceable stage |
| Generation | local mode plus optional OpenAI adapter |
| Evaluation | labelled dataset, Recall@5, MRR and PR regression gate |
| Reliability | bounded transient retries and provider timeout configuration |
| Observability | request trace IDs and structured logging hooks |
| Cost | explicit token/usage accounting boundary |
| CI | Python test matrix plus dedicated RAG evaluation workflow |

This repository is a reference architecture, not a claim that one retrieval strategy, model or evaluation dataset is universally production-ready.
