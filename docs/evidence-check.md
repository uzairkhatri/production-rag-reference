# Value evidence guard

This is a narrow, offline check for some English factual questions, **not a semantic answerability model**. It prevents recognizable numeric/version questions from receiving unrelated source text when a matching value is missing. It does not solve the remaining unsupported-name, location, or policy questions.

## How it works

Both generators call `select_evidence` in [app/evidence.py](../app/evidence.py) before answering:

1. Remove non-positive-score chunks and limit source text to the supplied word budget.
2. Recognize fact-seeking forms asking for money, a percentage, a quantity/duration, or a software version. Procedural forms such as "how should" and "what controls" retain lexical behavior.
3. For a recognized form, require a value of that type in a sentence sharing at least 75% of the question's normalized subject terms. Normalization removes a fixed English stop list and simple plurals, not semantic synonyms. Numeric digits and some English number words are recognized; supported value formats are explicit in the code.
4. Ignore sentences explicitly marking values unknown, unspecified, or unavailable. Check only actual budgeted body text, not excluded chunks or their titles. Require all recognized value types in a compound question.
5. If evidence is missing, return the existing abstention message with no citations. The optional OpenAI adapter does not make its provider request. Otherwise, use only the selected, checked passages.

The same truncated passages are checked and used by generation. A value located after the word limit cannot authorize a response. Zero-score hits no longer enter generated text or citations. Word limits are not exact model-token or spending limits and do not include the complete provider prompt.

The internal `Generated.evidence_reason` is recorded in benchmark JSON and application logging calls. Values include `no_positive_context`, `ambiguous_value_request`, `missing_value_evidence:<type>`, `value_evidence_present`, and `lexical_context_only`. The HTTP response shape remains unchanged. A positive reason only means this limited precheck passed.

## Measured results

Before measurements use the actual extractive generator from commit `e3338d1`, with identical corpus, questions, retrieval, reranking, and word budget for each before/after pair. No real model provider was called.

| Measure | Before | After |
| --- | --- | --- |
| Original unsupported questions correctly rejected | 1 / 6 | 5 / 6 |
| Original answerable questions not rejected | 18 / 18 | 18 / 18 |
| Original Recall@5 / MRR | 0.9444 / 0.9167 | 0.9444 / 0.9167 |
| Additional unsupported questions correctly rejected | 0 / 8 | 6 / 8 |
| Additional answerable questions not rejected | 8 / 8 | 8 / 8 |
| Additional Recall@5 / MRR | 1.0000 / 1.0000 | 1.0000 / 1.0000 |

The original corpus and all 24 original questions are unchanged. Only four original baseline flags change from incorrect to correct abstention: SLA percentage, retention duration, price, and SDK version. Retrieval and supported-case floors are not weakened. CI also runs the separate 7-document, 16-question suite with its own per-case baseline.

The additional suite contains numeric facts as positive controls, differently worded questions, a document full of unrelated numbers, and six missing-value questions. It also includes unsupported name/location questions that still fail. These are newly authored regression cases, **not an independently held-out validation set**. A 75% lexical subject threshold is an explicit heuristic, not a calibrated probability.

## Remaining failures and limits

- The original loan-policy question still receives irrelevant text. The additional service-owner and backup-location questions also still receive text because these are not recognized value requests.
- The two original retrieval weaknesses remain: the provider paraphrase ranks second and the budget paraphrase misses its relevant source. Retrieval was not changed.
- Unfamiliar phrasing, synonyms, multilingual questions, cross-sentence evidence, or values in unsupported formats can cause false abstention. For example, a price described only as "free" is not a recognized monetary amount.
- Value shape and lexical subject overlap cannot prove entity attribution, the requested relationship, recency, contract applicability, truth, or lack of contradiction. A nearby number can still be misattributed. The explicit unavailable-word check is not a general negation parser.
- Compound questions can remain incompletely answered. Required value types are checked, but the guard does not decompose every requested fact or verify all generated claims.
- `lexical_context_only` is not an assertion of sufficiency. Non-value requests retain the existing behavior. The optional provider can still produce an unsupported answer after a precheck passes; fake-client tests do not assess model quality.
- This is neither an access-control nor a prompt-injection defense. Do not use it as a sole production safety control.

## Verification and next work

Follow the [two evaluation commands](evaluation-gate.md#run-the-same-gate-as-ci). Both standard gates pass; `--min-abstention 1` still fails, and the remaining cases stay visible. Tests cover supported values, absent values, wrong units, unrelated subjects, title-only matches, multiple requested types, truncated context, API responses, and provider-call suppression with an injected fake client.

Before claiming general answerability, evaluate semantic evidence checks against independently labelled supported and unsupported questions, including entities, relationships, negation, contradictory sources, paraphrases, and multi-hop evidence. Preserve these fixtures as regression tests rather than optimizing only for them.
