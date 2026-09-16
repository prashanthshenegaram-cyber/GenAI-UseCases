# Code Description: Invoice / Receipt Field Extractor

## 1. Project Overview

This project converts invoice or receipt text into structured JSON fields:

- `invoice_number`
- `invoice_date`
- `vendor`
- `bill_to`
- `subtotal`
- `tax`
- `total`
- `payment_terms`
- `currency`

The workflow is:

```text
Invoice text
    -> versioned prompt
    -> LLM/provider adapter
    -> JSON parsing
    -> Pydantic schema validation
    -> v5 verification
    -> output JSON
    -> ground-truth evaluation
    -> reports
```

The project also includes a browser preview. The browser page can upload a text invoice and show a local JSON preview, while the Python CLI performs the authoritative prompt-driven extraction and evaluation workflow.

## 2. Root Files

### `README.md`

Main project documentation. It explains the objective, installation, environment variables, project structure, extraction commands, evaluation commands, prompt versions, metrics, and known limitations.

Use this file for general setup instructions.

### `DEMO_GUIDE.md`

Presentation guide for demonstrating the use case. It contains:

- the business problem explanation
- the five-minute speaking script
- commands to run the pipeline
- files to open during the presentation
- the code-to-workflow map
- browser demo instructions

Use this file as the presentation script.

### `CODE_DESCRIPTION.md`

This file. It is the file-by-file technical reference for the whole repository.

### `requirements.txt`

Lists the Python packages required by the project:

- `pydantic`: validates and normalizes extraction responses
- `python-dotenv`: loads environment variables from `.env`
- `pytest`: runs automated tests
- `requests`: available for provider/API integration

Install them with:

```powershell
python -m pip install -r requirements.txt
```

### `.env.example`

Template for environment variables. It documents settings such as the provider API key, model name, temperature, maximum output tokens, and default prompt version.

Copy it to `.env` when configuring a real provider. Do not commit secrets.

### `run_tests.py`

Small convenience wrapper around pytest. It runs:

```text
python -m pytest -q
```

The project can also run pytest directly.

### `demo.py`

Optional presentation runner. It is not required by the core application.

It orchestrates the existing production modules to:

1. Process all invoice files with v5.
2. Evaluate the v5 outputs.
3. Process and evaluate prompt versions v1 through v4.
4. Generate CSV and Markdown reports.

It does not contain a second extraction implementation and does not hard-code metrics. It calls the modules in `src/`.

Run it with:

```powershell
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" demo.py
```

## 3. Python Source Files: `src/`

### `src/__init__.py`

Marks `src` as a Python package so modules can import one another with statements such as:

```python
from src.extractor import extract_file
```

It contains no main business logic.

### `src/config.py`

Central configuration module.

Responsibilities:

- Finds the project root using the source file location.
- Loads `.env` values.
- Defines default model settings.
- Defines paths for invoices, prompts, ground truth, outputs, and results.
- Defines the list of required extraction fields.

Important values include:

- `BASE_DIR`
- `INVOICES_DIR`
- `GROUND_TRUTH_DIR`
- `OUTPUTS_DIR`
- `PROMPTS_DIR`
- `RESULTS_DIR`
- `FIELDS`

This module prevents file paths and field names from being duplicated across the application.

### `src/extractor.py`

Core extraction pipeline.

Main functions:

- `load_prompt(version)`: reads `prompts/v1.txt` through `prompts/v5.txt`.
- `read_invoice(path)`: reads an invoice text file.
- `extract_from_text(text, prompt_version)`: inserts the document into the prompt, calls the LLM adapter, parses the response, and validates it.
- `extract_file(path, prompt_version)`: combines file reading and text extraction.

This is the main path from an invoice document to a validated Python dictionary.

### `src/llm_client.py`

Provider abstraction layer.

Responsibilities:

- Defines the `BaseLLMClient` interface.
- Defines `GeminiCompatibleClient` as the provider adapter.
- Reads `GEMINI_API_KEY` from the environment.
- Uses a deterministic local fallback when no API key is configured.
- Contains `mock_generate_response`, which parses the sample text format for local demonstrations.

This separation allows a real LLM provider to be added without rewriting the extractor, schema, evaluator, or CLI.

When no key is configured, the application logs:

```text
No GEMINI_API_KEY configured. Using mock LLM output.
```

### `src/schema.py`

Pydantic response contract.

Main model:

- `InvoiceExtraction`: defines the allowed fields and their types.

Responsibilities:

- Allows missing values as `None`.
- Rejects unexpected fields with `extra='forbid'`.
- Normalizes currency values to uppercase.
- Accepts the expected ISO date format.
- Supports the legacy `_confidence` input alias while exposing the Pydantic-safe `confidence` field.

Main helper functions:

- `validate_extraction(data)`: validates a dictionary.
- `normalize_model_output(raw)`: confirms that the model response is a dictionary.

This module protects downstream evaluation from malformed model output.

### `src/verifier.py`

v5 verification stage.

Responsibilities:

- Runs only for prompt version v5.
- Checks whether extracted values are supported by the original invoice text.
- Resets unsupported tax values to `None`.
- Resets unsupported currency values to `None`.
- Rejects malformed date strings by setting them to `None`.

This stage implements the requirement that the system must not invent values that the document does not support.

### `src/evaluator.py`

Evaluation and metric calculation.

Main functions:

- `compare_fields(pred, truth)`: compares each required field.
- `evaluate_prediction(pred, truth)`: calculates per-invoice metrics.
- `load_ground_truth(path)`: reads a truth JSON file.
- `load_prediction(path)`: reads a generated output JSON file.
- `evaluate_all(prompt_version)`: evaluates all matching invoice outputs.
- `aggregate_metrics(result_set)`: calculates dataset-level summary metrics.

Calculated metrics include:

- precision
- recall
- F1
- accuracy
- misses
- correct absences
- hallucinations
- tax-specific hallucinations

The metrics are calculated from actual output and ground-truth files; they are not hard-coded.

### `src/report.py`

Report generation module.

Main functions:

- `generate_accuracy_csv()`: creates `results/accuracy_report.csv`.
- `generate_evaluation_report()`: creates `results/evaluation_report.md`.
- `generate_what_moved_the_needle()`: creates `results/what_moved_the_needle.md`.

The module reads the stored `v1_results.json` through `v5_results.json` files and formats their measured values for review.

### `src/main.py`

Command-line entry point.

Available commands:

```text
extract       Process one invoice file.
evaluate      Evaluate one prompt version.
evaluate-all Evaluate prompt versions v1 through v5.
report        Generate the Markdown evaluation report.
```

Examples:

```powershell
python -m src.main extract --input data/invoices/invoice_01.txt --prompt-version v5
python -m src.main evaluate --prompt-version v5
python -m src.main evaluate-all
python -m src.main report --prompt-version v5
```

The `extract` command also invokes the v5 verifier when `--prompt-version v5` is selected.

## 4. Prompt Files: `prompts/`

### `prompts/v1.txt`

Basic or zero-shot extraction prompt. It establishes the original extraction behavior.

### `prompts/v2.txt`

Adds role instructions and abstention guidance. It tells the model to avoid unsupported values.

### `prompts/v3.txt`

Adds stricter schema, field, numeric, date, and currency normalization requirements.

### `prompts/v4.txt`

Adds examples showing how to handle missing tax, missing currency, missing payment terms, and other absence cases.

### `prompts/v5.txt`

Final extraction and verification-oriented prompt. It emphasizes checking fields against the source document and returning `null` when evidence is absent.

The prompt files are kept separate so each prompt version can be tested and compared independently.

## 5. Input and Dataset Files: `data/`

### `data/invoices/`

Contains the source invoice text files:

- `invoice_01.txt`
- `invoice_02.txt`
- `invoice_03.txt`
- `invoice_04.txt`
- `invoice_05.txt`

These files are the inputs to the extractor.

### `data/ground_truth/`

Contains the expected structured values for each invoice:

- `invoice_01.json`
- `invoice_02.json`
- `invoice_03.json`
- `invoice_04.json`
- `invoice_05.json`

The evaluator compares generated predictions with these files.

### `data/outputs/`

Contains generated extraction results. File names include both the invoice and prompt version, for example:

```text
data/outputs/invoice_01_v5_output.json
```

This naming makes it possible to compare the same invoice across different prompt versions.

## 6. Test Files: `tests/`

### `tests/test_schema_and_tax.py`

Tests schema and evaluation behavior, including:

- valid schema acceptance
- rejection of unexpected fields
- nullable missing fields
- date handling
- currency normalization
- malformed output rejection
- tax absence remaining `null`
- field-level hallucination detection

### `tests/test_results_from_cli.py`

Tests the CLI extraction path with a temporary invoice file and confirms that the extraction pipeline can create an output containing the expected invoice number.

Run all tests with:

```powershell
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" -m pytest -q
```

## 7. Browser Files

### `index.html`

Static dashboard page.

It contains:

- dashboard layout
- upload area
- invoice file input
- Analyze button
- JSON output preview
- summary cards and navigation elements

The upload control accepts text-like files such as `.txt`, `.csv`, `.json`, and `.md`.

### `script.js`

Browser-side behavior.

Responsibilities:

- Handles navigation link selection.
- Animates summary cards.
- Reads the selected invoice file in the browser.
- Performs a lightweight local preview parse.
- Displays extracted JSON in the output panel.
- Updates the selected file name and status badge.

Important limitation: this browser parser is a static preview and does not call the Python prompt pipeline. The Python CLI remains the authoritative extraction and evaluation path.

### `styles.css`

Visual styling for the browser dashboard.

It defines:

- colors and typography
- sidebar and dashboard layout
- summary cards
- upload/dropzone styling
- JSON output panel
- responsive behavior

## 8. Generated Results Files

### `results/v1_results.json` through `results/v5_results.json`

Store aggregate metrics and per-invoice field-level metrics for each prompt version.

### `results/accuracy_report.csv`

Tabular comparison of precision, recall, F1, accuracy, hallucinations, and tax hallucinations for each prompt version.

### `results/evaluation_report.md`

Readable Markdown summary of the evaluated prompt versions and dataset metrics.

### `results/what_moved_the_needle.md`

Explains the intended changes between prompt versions and displays the measured comparison values from the result files.

## 9. Presentation Summary

Use this short explanation:

> `src/main.py` provides the commands. `src/extractor.py` loads a versioned
> prompt and processes invoice text. `src/llm_client.py` isolates the model
> provider. `src/schema.py` validates the JSON contract. `src/verifier.py`
> protects the v5 result from unsupported values. `src/evaluator.py` compares
> predictions with ground truth. `src/report.py` creates the final evidence.
> The browser files provide a local upload preview, and `demo.py` is an
> optional convenience runner that orchestrates the complete presentation.
