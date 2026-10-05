# Failure Analysis

6 of 20 questions failed.

Failure classes distinguish source chunking/loading, retrieval, and generation; answerable refusals also carry the `INCORRECT_REFUSAL` label.

## Top-5 Failures

### 1. U01 - GENERATION_ERROR

Question: What is the battery capacity of the Acme Sensor?

Answer: The Acme Sensor is designed for indoor industrial monitoring. It supports continuous operation and a Product: Sensor, Category: Monitoring, Stock: 120

Root cause: The question is deliberately unanswerable, but the pipeline returned a substantive answer.

Recommended targeted fix: Keep the retrieved evidence fixed and tighten the existing grounded-answer prompt or output validation so the response returns the supported facts without invention.

### 2. U02 - GENERATION_ERROR

Question: What is the device's manufacturing date?

Answer: Device Specification

Root cause: The question is deliberately unanswerable, but the pipeline returned a substantive answer.

Recommended targeted fix: Keep the retrieved evidence fixed and tighten the existing grounded-answer prompt or output validation so the response returns the supported facts without invention.

### 3. U03 - GENERATION_ERROR

Question: Who is the chief executive officer of Acme?

Answer: The Acme Sensor is designed for indoor industrial monitoring. It supports continuous operation and a

Root cause: The question is deliberately unanswerable, but the pipeline returned a substantive answer.

Recommended targeted fix: Keep the retrieved evidence fixed and tighten the existing grounded-answer prompt or output validation so the response returns the supported facts without invention.

### 4. U04 - GENERATION_ERROR

Question: What were North's Q4 sales?

Answer: Region: North, Q1: 2500, Q2: 2800, Q3: 3100

Root cause: The question is deliberately unanswerable, but the pipeline returned a substantive answer.

Recommended targeted fix: Keep the retrieved evidence fixed and tighten the existing grounded-answer prompt or output validation so the response returns the supported facts without invention.

### 5. U05 - GENERATION_ERROR

Question: What is the retail price of the Gateway?

Answer: Product: Gateway, Category: Networking, Stock: 55

Root cause: The question is deliberately unanswerable, but the pipeline returned a substantive answer.

Recommended targeted fix: Keep the retrieved evidence fixed and tighten the existing grounded-answer prompt or output validation so the response returns the supported facts without invention.
