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

`excel-benchmark` rebuilds and evaluates each representation and writes measured values to `results/excel_benchmark.json`. It deliberately does not hard-code a winner. The standard evaluation writes `results/evaluation_results.json` and `results/evaluation_report.md`, including category accuracy, retrieval failures, refusal behavior, and chart analysis. Run the commands after installing dependencies to populate actual results.

## Limitations

This is a classic text-RAG assessment, not a production security boundary. PDF extraction varies by layout, the fallback embeddings are lexical rather than semantic, the JSON vector store is a portable reference implementation rather than a distributed database, and the mock generator is extractive. Chroma, a stronger embedding model, OCR/vision, and a hosted LLM are natural next steps for production workloads.
