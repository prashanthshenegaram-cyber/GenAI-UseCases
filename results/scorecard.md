# RAG Quality Gate Scorecard

**Overall gate: FAIL**

Evaluated 20 golden questions (8 easy, 6 table-cell, 6 unanswerable).

## Metrics

| Metric | Score | Threshold | Status |
|---|---:|---:|---|
| faithfulness | 0.700 | 0.800 | FAIL |
| answer_relevance | 0.700 | 0.800 | FAIL |
| context_precision | 0.970 | 0.750 | PASS |
| context_recall | 1.000 | 0.750 | PASS |
| hit_rate | 1.000 | 0.800 | PASS |
| correct_refusal_rate | 0.000 | 0.900 | FAIL |

LLM-as-Judge score: N/A (not configured).
RAGAS: disabled (Set RAG_GATE_USE_RAGAS=true to request optional RAGAS scoring.)

## Question Results

| ID | Type | Result | Failure | Question |
|---|---|---|---|---|
| E01 | easy | PASS | - | What is the Acme Sensor designed for? |
| E02 | easy | PASS | - | Is the Acme Sensor intended for indoor or outdoor use? |
| E03 | easy | PASS | - | What warranty does the device include? |
| E04 | easy | PASS | - | Does the sensor support continuous operation? |
| E05 | easy | PASS | - | Which product category is the Gateway in? |
| E06 | easy | PASS | - | How many Mount units are in stock? |
| E07 | easy | PASS | - | Which region recorded 3,500 in Q3 sales? |
| E08 | easy | PASS | - | What category does the Sensor belong to? |
| T01 | table_cell | PASS | - | What operating temperature range is listed in the PDF specification table? |
| T02 | table_cell | PASS | - | What voltage is listed in the PDF specification table? |
| T03 | table_cell | PASS | - | What weight is listed in the PDF specification table? |
| T04 | table_cell | PASS | - | What were South's Q2 sales in the spreadsheet? |
| T05 | table_cell | PASS | - | What were West's Q1 sales in the spreadsheet? |
| T06 | table_cell | PASS | - | How many Sensors are in stock according to the Products sheet? |
| U01 | unanswerable | FAIL | GENERATION_ERROR | What is the battery capacity of the Acme Sensor? |
| U02 | unanswerable | FAIL | GENERATION_ERROR | What is the device's manufacturing date? |
| U03 | unanswerable | FAIL | GENERATION_ERROR | Who is the chief executive officer of Acme? |
| U04 | unanswerable | FAIL | GENERATION_ERROR | What were North's Q4 sales? |
| U05 | unanswerable | FAIL | GENERATION_ERROR | What is the retail price of the Gateway? |
| U06 | unanswerable | FAIL | GENERATION_ERROR | Which employee approved the Sensor warranty? |
