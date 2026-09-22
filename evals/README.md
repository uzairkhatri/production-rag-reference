# Evaluation fixtures

All documents and questions in this directory are authored synthetic examples. They contain no customer data and do not describe capabilities implemented by this repository. Runbook text describes fictional engineering procedures; it is evidence for the test questions, not a claim about the application.

## Corpus and labels

`corpus.json` contains eight topic-specific runbooks and two distractors: a conference program and a launch announcement. The distractors deliberately share engineering vocabulary but do not supply the requested procedures. Ten documents compete for five retrieved chunks, so retrieval can miss a relevant source.

`dataset.json` contains 24 cases:

| Kind | Count | Label rule |
| --- | --- | --- |
| `direct` | 8 | A question using the topic's wording, with its required source |
| `paraphrase` | 8 | The same type of need expressed differently, with its required source |
| `multi_document` | 2 | Both labelled sources are required to address the two-part question |
| `unsupported` | 6 | No document supplies the requested fact; relevance labels must be empty |

A relevant source must contain the requested procedure or fact. Mentioning the topic or offering marketing claims is insufficient. Labels express required evidence, not every loosely related document. The five overlapping unsupported questions ask for exact commitments, retention, prices, installed versions, or loan eligibility absent from the corpus. The sixth uses unrelated astronomy terms as a zero-overlap control.

Labels are transparent and reviewable but not independently annotated. The questions are authored, not sampled from real users; the paraphrases are not a held-out generalization test. Review labels before changing retrieval to optimize these scores.

## Format

Both files have `schema_version: 1`. The corpus has a `documents` array containing `id`, `title`, `source`, and `text`. The dataset has a `cases` array containing `id`, `kind`, `question`, and `relevant_document_ids`.

IDs must be unique within each file. Supported cases need nonempty relevance labels naming existing documents. Multi-document cases need at least two labels. Unsupported cases must have no labels. A dataset must include both supported and unsupported cases; neither category may disappear silently from reporting.

## Baseline

`baseline.json` records per-case metric floors and abstention decisions for these exact fixtures and evaluation settings. A recorded `abstention_correct: false` is a known defect, not a desired answer. Improvements are allowed; previously correct decisions must not regress. See the [baseline review policy](../docs/evaluation-gate.md#review-and-update-a-baseline) before updating it.
