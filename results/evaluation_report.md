# Classic RAG evaluation

- Total questions: 15
- Overall accuracy: 46.7%

## Accuracy by category

| Category | Accuracy |
|---|---:|
| table-cell | 66.7% |
| image | 0.0% |
| text | 100.0% |
| excel | 28.6% |

## Observed results

The values below were generated from the current local execution. The image/chart category is expected to expose the limitation of text-only PDF extraction; OCR or a vision-capable model is required for reliable image-only facts.

## Chart/image failure analysis

- Q13: success=False; answer=I couldn't find that information in the provided documents.
- Q15: success=False; answer=Region: North, Q1: 2500, Q2: 2800, Q3: 3100 Region: South, Q1: 3000, Q2: 3400, Q3: 3700 Region: East, Q1: 2900, Q2: 3200, Q3: 3500

## Grounded refusal results

- Q14: success=True; answer=I couldn't find that information in the provided documents.

## Retrieval failures


## Excel serialization comparison

| Representation | Accuracy |
|---|---:|
| row_text | 46.7% |
| markdown_table | 46.7% |
| column_wise | 46.7% |

No winner is hard-coded; the table reflects this execution.
