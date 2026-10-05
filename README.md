# Week 2 Classic RAG: Chat With Your Document

A modular assessment project for classic, text-based retrieval augmented generation over PDF and Excel files.

## What RAG does

RAG retrieves relevant document chunks before generation. This reduces unsupported answers by giving the generator a small evidence set. The flow is:

`loader -> serializer/table extractor -> chunker -> embeddings -> vector store -> retriever -> context -> generator -> citations`

The modules in `app/` keep those responsibilities separate. The vector-store interface is intentionally small so a Chroma or pgvector adapter can be introduced without changing retrieval or generation. The included store persists JSON vectors for deterministic execution; `chromadb` is declared as the production-oriented dependency.

## Setup and run

```powershell
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe -m pip install -r requirements.txt
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe generate_sample_data.py
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe main.py ingest --input data/documents
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe main.py query --question "What is the operating temperature range?"
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe main.py evaluate
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe main.py excel-benchmark
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe -m pytest
C:/Users/prashanth.shenegaram/AppData/Local/Programs/Python/Python313/python.exe -m streamlit run web_app.py
```

The Streamlit browser app opens at `http://localhost:8501`. Upload one or more PDF or Excel files in the sidebar, click **Ingest documents**, and then ask questions to see grounded answers, citations, and the retrieved evidence.

Use `--chunking-strategy fixed|recursive|section-aware`, `--serialization row_text|markdown_table|column_wise`, `--top-k`, and `--similarity-threshold`. Configuration can also come from `.env`/environment variables shown in `.env.example`.

## Retrieval details

PDF pages retain `source`, `file_type`, and `page`; extracted tables additionally retain `table_id` and `chunk_type=table`. Excel chunks retain `source`, `sheet`, `row` where applicable, `serialization`, and `chunk_type=excel_row`. Three chunking modes are implemented: fixed character windows, paragraph-oriented recursive chunks, and section-aware chunks.

The default embedding path uses the local `all-MiniLM-L6-v2` sentence-transformers model. If it cannot be loaded, a deterministic hashing embedding keeps the assessment runnable; set `EMBEDDING_MODEL=hash` for fast fully offline evaluation. Embeddings are vectors representing semantic/token meaning; retrieval compares query and chunk vectors. The fallback store reports Euclidean distance and converts it to `1/(1+distance)` as a score. Cosine similarity is usually preferable for normalized semantic embeddings, while L2 is sensitive to vector magnitude.

## Generation and grounding

`BaseLLMClient` separates the pipeline from providers. `ConfigurableLLMClient` uses OpenAI only when a model and `LLM_API_KEY` are supplied. Otherwise it uses a deterministic extractive mock. CLI answers explicitly show `[mock mode]`; mock mode is not presented as a real LLM. `temperature`, `top_p`, generation `top_k`, and `max_output_tokens` are configurable generation controls. They affect sampling/output behavior, not retrieval quality.

The context prompt says to answer only from supplied context, avoid invention, refuse missing facts, and cite metadata. No retrieved evidence produces the grounded refusal: `I couldn't find that information in the provided documents.` Citations are generated from actual metadata rather than guessed page, row, or sheet values.

## PDF tables and chart limitation

`pdfplumber` extracts tables separately where possible. The sample PDF also includes a chart whose values are drawn into an image. Text extraction can see surrounding prose but not reliably read those pixels, so the image questions are an explicit `image` evaluation category. This project does not use vision or OCR to hide that limitation. Reliable chart answers require OCR, chart-aware parsing, or a vision-capable model.

## Excel bake-off

The exact three serializers are:

- `row_text`: one row such as `Region: West, Q1: 3500, Q2: 3900, Q3: 4200`.
- `markdown_table`: header, alignment row, and table rows.
- `column_wise`: one line per column containing all values.

`excel-benchmark` rebuilds and evaluates each representation and writes measured values to `results/excel_benchmark.json`. It deliberately does not hard-code a winner. The standard evaluation writes `results/classic_evaluation_results.json` and `results/evaluation_report.md`, including category accuracy, retrieval failures, refusal behavior, and chart analysis. The separate release gate writes the requested `results/evaluation_results.json`. Run the commands after installing dependencies to populate actual results.

## RAG Quality Gate

The release gate evaluates the existing `RAGPipeline` in `app/pipeline.py`; it does not create a second loader, retriever, or generator. It rebuilds an isolated index under `data/vector_store/quality_gate/` from the same PDF and Excel documents, and runs every item in `data/golden_dataset.json` (8 easy, 6 PDF/Excel table-cell, and 6 deliberately unanswerable questions).

Run it from the project root after installing the normal requirements:

```powershell
python evaluate.py
python -m pytest
```

Each run writes `results/evaluation_results.json`, `results/evaluation_results.csv`, `results/scorecard.md`, and `results/failure_analysis.md`. The console exits with status 1 when the release thresholds fail, making the gate suitable for CI. The scorecard includes PASS/FAIL for every golden question and the overall gate; failure analysis ranks up to five failed questions and gives a root cause plus a targeted fix.

The deterministic metrics use the answer and retrieved chunk text returned by the existing pipeline, compared with the golden evidence:

- **Context Precision**: rank-weighted precision of retrieved chunks containing expected evidence.
- **Context Recall**: fraction of required evidence facts present in the retrieved chunks.
- **Retrieval Hit Rate** (`hit_rate`): fraction of answerable questions retrieving at least one expected source document.
- **Faithfulness**: fraction of answer claims represented in retrieved evidence; a correct refusal on an unanswerable item scores 1, while an answerable refusal scores 0.
- **Answer Relevance**: required answer facts present in the answer; an unanswerable item scores 1 only for a refusal. Refusing an answerable question is not rewarded.
- **Correct Refusal Rate**: fraction of the six unanswerable questions that receive a refusal.
- **LLM-as-Judge**: optional structured JSON judgment on a 1-5 scale, normalized to 0-1. It is reported as N/A unless `LLM_API_KEY` is configured; no proxy score is fabricated.

Default release thresholds are faithfulness >= 0.80, answer relevance >= 0.80, context precision >= 0.75, context recall >= 0.75, hit rate >= 0.80, and correct refusal rate >= 0.90. Override them with `RAG_GATE_FAITHFULNESS_THRESHOLD`, `RAG_GATE_ANSWER_RELEVANCE_THRESHOLD`, `RAG_GATE_CONTEXT_PRECISION_THRESHOLD`, `RAG_GATE_CONTEXT_RECALL_THRESHOLD`, `RAG_GATE_HIT_RATE_THRESHOLD`, and `RAG_GATE_CORRECT_REFUSAL_RATE_THRESHOLD`.

Failure classification checks the actual loaded corpus, retrieved contexts, and answer in order: missing source evidence is `CHUNKING_ERROR`; evidence in the corpus but not the retrieved context is `RETRIEVAL_MISS`; retrieved evidence followed by a wrong or incomplete answer is `GENERATION_ERROR`; refusal despite retrieved evidence is `OVER_REFUSAL`. Answerable refusals without retrieved evidence also carry the `INCORRECT_REFUSAL` label while retaining the retrieval/chunking root cause.

For optional RAGAS scoring and model-based judging, configure `LLM_API_KEY` and set `RAG_GATE_USE_RAGAS=true`. Install the optional packages with `python -m pip install ragas datasets langchain-openai`. RAGAS scores are reported separately from the evidence-based release metrics; if the optional dependencies or provider call are unavailable, the report explains why and retains the local calculated scores.

### Demo

1. Start the existing document-chat UI with `python -m streamlit run web_app.py` and open `http://localhost:8501`.
2. Ingest `data/documents/spec.pdf` and `data/documents/sales.xlsx`, then ask a supported PDF or spreadsheet question and inspect its citations/evidence.
3. In a project-root terminal, run `python evaluate.py` to see the 20-question release gate and open `results/scorecard.md` and `results/failure_analysis.md`.

The demo uses the existing local mock generator by default. It remains labeled mock mode; configure a supported OpenAI model and key only when a real model-backed demo is needed.

## Limitations

This is a classic text-RAG assessment, not a production security boundary. PDF extraction varies by layout, the fallback embeddings are lexical rather than semantic, the JSON vector store is a portable reference implementation rather than a distributed database, and the mock generator is extractive. Chroma, a stronger embedding model, OCR/vision, and a hosted LLM are natural next steps for production workloads.
