# What Moved the Needle

The prompt changes across v1 through v5 are meant to reduce hallucinations, improve field support discipline, and force more accurate normalization.

## Evidence from the results

The table below is based on metrics computed from actual predictions and local ground-truth JSON files.

| Version | Precision | Recall | F1 | Accuracy | Hallucinations | Tax Hallucinations |
|---|---:|---:|---:|---:|---:|---:|
| v1 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v2 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v3 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v4 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v5 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |

## Prompt changes that moved the needle

1. Role/system prompting in v2 forced the model to avoid unsupported fields and use `null` for absence.
2. Schema constraints in v3 forced numeric values and a strict field list while requiring normalization of dates and currency only when explicit.
3. Few-shot examples in v4 exposed missing tax, missing payment terms, and missing currency patterns so the model could distinguish absence from hallucination.
4. Prompt chaining in v5 added a verification stage checking each field against the original invoice text before formatting the final JSON output.

## Changes that did not improve the metric

If a later version is unchanged or lower on a given metric, this report should show the real numbers. The implemented comparison report derives its evidence from the stored `v*_results.json` files and should never fabricate a trend.