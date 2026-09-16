# Demo Guide: Invoice / Receipt Field Extractor

## Demo purpose

`demo.py` is the presentation runner for this use case. It executes the
complete workflow in a repeatable order and creates files you can open while
explaining the solution. It does not replace the extractor and it does not
invent metrics. It calls the existing production modules and saves their real
outputs.

The main story to tell is:

> Unstructured invoice text goes in. A versioned prompt guides extraction. A
> strict schema validates the response. A verifier protects against unsupported
> values. Ground truth measures the result. Reports show the evidence.

## What to demonstrate

This project reads invoice text, applies a versioned extraction prompt, validates the JSON schema, verifies unsupported values for v5, compares predictions with ground truth, and produces measured reports.

The extracted fields are:

- `invoice_number`
- `invoice_date`
- `vendor`
- `bill_to`
- `subtotal`
- `tax`
- `total`
- `payment_terms`
- `currency`

Missing or unsupported fields are represented as `null`.

## One-command demo

Open PowerShell in the project root:

```powershell
cd C:\Users\prashanth.shenegaram\Downloads\Use_case-1
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" demo.py
```

The demo processes every invoice in `data/invoices/` with v5, evaluates v5, compares v1 through v5, and generates the reports.

Expected demo output includes:

```text
Invoices: 5
Ground truth files: 5
...
precision=...
recall=...
f1=...
accuracy=...
hallucinations=...
```

The exact metric values come from the files generated during that run.

## Five-minute speaking script

### Opening: business problem

Say:

> Invoices contain the same business information in different text layouts.
> The goal is to convert that text into a consistent JSON contract while
> returning `null` when a value is absent instead of guessing.

### Show the input and contract

Open `data/invoices/invoice_01.txt`, then show the nine required fields in
`src/config.py` and the Pydantic model in `src/schema.py`.

Say:

> The schema is the contract. It controls field names, numeric types, date
> normalization, currency normalization, and the strict response shape.

### Show prompt evolution

Open `prompts/v1.txt` through `prompts/v5.txt`.

Say:

> The prompt versions represent controlled iterations. v1 starts with basic
> extraction. Later versions add abstention rules, schema constraints,
> examples, and finally a verification-oriented v5 process.

### Run one invoice

Run the command in the next section and open
`data/outputs/invoice_01_v5_output.json`.

Say:

> The extractor loads the selected prompt, inserts the document, calls the
> provider adapter, parses JSON, validates it, and writes a traceable output
> named with both the invoice and prompt version.

### Explain safety and null handling

Show an invoice where tax or currency is absent and compare the source text
with its output JSON.

Say:

> The system does not calculate or invent unsupported values. For v5, the
> verifier checks the extracted values against signals in the original text
> and can reset unsupported values to `null`.

### Explain evaluation

Open `data/ground_truth/invoice_01.json` beside the generated output, then
open `results/v5_results.json`.

Say:

> Evaluation is field-level. Every predicted field is compared with the
> corresponding ground-truth field, allowing us to measure matches, misses,
> correct absences, and hallucinations.

### Close with evidence

Open `results/evaluation_report.md` and
`results/what_moved_the_needle.md`.

Say:

> The report is generated from stored results, so the comparison between
> prompt versions is evidence from this dataset rather than a claimed result.

## Presentation workflow

### 1. Show the source invoice

Open one of these files:

```text
data/invoices/invoice_01.txt
data/invoices/invoice_02.txt
data/invoices/invoice_03.txt
data/invoices/invoice_04.txt
data/invoices/invoice_05.txt
```

Explain that these are the input documents. The same extractor can later receive text extracted from PDFs or images.

### 2. Show prompt versioning

Open the files in `prompts/`:

- `v1.txt`: basic extraction prompt
- `v2.txt`: role and abstention instructions
- `v3.txt`: strict schema and normalization
- `v4.txt`: examples for missing values and hallucinations
- `v5.txt`: extraction plus verification instructions

The selected prompt is loaded by `src/extractor.py`; prompts are not hard-coded into the evaluator.

### 3. Run one extraction

```powershell
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" -m src.main extract --input data/invoices/invoice_01.txt --prompt-version v5
```

Open the generated file:

```text
data/outputs/invoice_01_v5_output.json
```

Explain the flow:

1. `src/extractor.py` loads `prompts/v5.txt`.
2. The invoice text is inserted into the prompt.
3. `src/llm_client.py` returns the provider response or the local fallback when no API key is configured.
4. `src/schema.py` validates the JSON with Pydantic.
5. `src/verifier.py` checks supported fields for v5.
6. The final JSON is written to `data/outputs/`.

### 4. Show evaluation

```powershell
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" -m src.main evaluate --prompt-version v5
```

Open:

```text
results/v5_results.json
```

Explain that precision, recall, F1, accuracy, misses, and hallucinations are calculated from the prediction files and `data/ground_truth/`. They are not hard-coded.

### 5. Show prompt comparison and reports

```powershell
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" -m src.main evaluate-all
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" -m src.main report --prompt-version v5
```

Present these files:

- `results/evaluation_report.md`
- `results/accuracy_report.csv`
- `results/what_moved_the_needle.md`
- `results/v1_results.json` through `results/v5_results.json`

### 6. Show the browser demo

Start the static dashboard:

```powershell
cmd /c "C:\Users\prashanth.shenegaram\AppData\Local\Programs\Python\Python313\python.exe" -m http.server 8000
```

Open:

```text
http://localhost:8000/
```

Choose an invoice `.txt` file from `data/invoices/`, click **Analyze**, and show the JSON preview.

The current browser page is a static preview UI. It demonstrates upload and JSON display locally; the authoritative prompt-driven extraction and evaluation flow is the Python CLI described above.

## Code-to-workflow map

Use this table when someone asks which file owns each responsibility:

| Code | Responsibility | What to say |
|---|---|---|
| `src/config.py` | Paths, settings, and required fields | Central project configuration and schema field list. |
| `src/extractor.py` | Prompt loading and extraction pipeline | Reads the document, calls the adapter, parses JSON, and validates it. |
| `src/llm_client.py` | Provider boundary | Keeps real provider integration separate from extraction logic; local runs use a deterministic fallback without a key. |
| `src/schema.py` | Pydantic response contract | Rejects unknown fields and normalizes supported values. |
| `src/verifier.py` | v5 support checks | Prevents unsupported tax, currency, or date values from surviving. |
| `src/evaluator.py` | Ground-truth comparison | Calculates field-level metrics and hallucination counts. |
| `src/report.py` | Presentation artifacts | Creates CSV and Markdown reports from saved results. |
| `src/main.py` | CLI entry point | Exposes extract, evaluate, evaluate-all, and report commands. |
| `demo.py` | End-to-end orchestration | Runs the above components in a repeatable presentation sequence. |
| `index.html`, `script.js`, `styles.css` | Browser preview | Lets a presenter upload text and view a local JSON preview. |

## Code comments in `demo.py`

The comments in `demo.py` are intentionally placed at the logical boundaries
of the workflow:

- Imports identify which production modules the demo reuses.
- `PROMPT_VERSIONS` identifies the controlled comparison set.
- `write_json` centralizes readable artifact writing.
- `run_extraction` discovers invoices, invokes extraction, applies v5
	verification, and writes per-invoice JSON.
- `run_evaluation` compares outputs with ground truth and saves aggregate
	metrics.
- `main` orders the end-to-end run and generates final reports.

This makes the demo easy to explain without turning the business logic into a
second implementation.

## Important demo note

If `GEMINI_API_KEY` is not configured, the project prints:

```text
No GEMINI_API_KEY configured. Using mock LLM output.
```

That is expected for the local demo. To use a real provider, configure the secret in `.env` using `.env.example` and implement/enable the provider adapter in `src/llm_client.py`.
