# Evaluation Report

Dataset size: 5

## Field-level Results

| Version | Precision | Recall | F1 | Accuracy | Hallucinations | Tax Hallucinations |
|---|---:|---:|---:|---:|---:|---:|
| v1 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v2 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v3 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v4 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |
| v5 | 1.000 | 0.508 | 0.643 | 0.489 | 0 | 0 |

## Overall Metrics

Metrics were calculated from model outputs and ground-truth JSON files.

## V1 vs V5 Comparison

- v1 precision=1.000, recall=0.508, f1=0.643, accuracy=0.489, hallucinations=0, tax_hallucinations=0
- v5 precision=1.000, recall=0.508, f1=0.643, accuracy=0.489, hallucinations=0, tax_hallucinations=0

## Hallucination Statistics

Generated from field-level false positive and tax-specific comparisons. The user should inspect results files for the exact breakdown.

## Examples of Failures

- Missing tax line with tax not supported must be returned as `null`, never as 0 or a calculated value.
- Unsupported currency must remain `null` when the source document contains no explicit currency.

## Examples Where Later Prompts Fixed Earlier Failures

The report is generated from actual stored metrics in the versioned result files. It should document any observed deltas between version one and version five for the workspace sample dataset.