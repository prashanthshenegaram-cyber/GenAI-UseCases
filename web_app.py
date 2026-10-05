import json
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

import streamlit as st

from app.config import Settings
from app.pipeline import RAGPipeline
from config.evaluation_config import EvaluationConfig
from evaluation.evaluator import evaluate_quality_gate


st.set_page_config(page_title="Chat With Your Document", layout="wide")

st.markdown(
    """
    <style>
    .block-container { max-width: 1180px; padding-top: 2rem; }
    .hero { padding: 1.3rem 1.5rem 1.1rem; border-radius: 14px; background: linear-gradient(115deg, #17324d, #287c7c); color: white; margin-bottom: 1.25rem; }
    .hero h1 { margin: 0; font-size: 2.15rem; }
    .hero p { margin: .35rem 0 0; color: #d8eeee; }
    .answer { padding: 1rem 1.15rem; border-left: 5px solid #2b8a78; background: #f1f8f6; border-radius: 8px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def initialize_workspace() -> Path:
    if "workspace" not in st.session_state:
        st.session_state.workspace = Path(mkdtemp(prefix="rag-upload-"))
    return st.session_state.workspace


def make_pipeline(workspace: Path, chunking: str, serialization: str, top_k: int) -> RAGPipeline:
    settings = Settings(
        documents_dir=workspace / "documents",
        vector_dir=workspace / "vector_store",
        chunking_strategy=chunking,
        serialization=serialization,
        top_k=top_k,
    )
    return RAGPipeline(settings)


def metadata_label(metadata: dict) -> str:
    source = metadata.get("source", "unknown source")
    location = []
    if metadata.get("page") is not None:
        location.append(f"page {metadata['page']}")
    if metadata.get("sheet"):
        location.append(f"sheet {metadata['sheet']}")
    if metadata.get("row") is not None:
        location.append(f"row {metadata['row']}")
    if metadata.get("table_id"):
        location.append(str(metadata["table_id"]))
    return f"{source} ({', '.join(location)})" if location else source


APP_ROOT = Path(__file__).resolve().parent
METRIC_LABELS = {
    "faithfulness": "Faithfulness",
    "answer_relevance": "Answer relevance",
    "context_precision": "Context precision",
    "context_recall": "Context recall",
    "hit_rate": "Retrieval hit rate",
    "correct_refusal_rate": "Correct refusal rate",
    "llm_as_judge_score": "LLM-as-Judge",
}


def load_saved_quality_report() -> dict[str, Any] | None:
    path = APP_ROOT / "results" / "evaluation_results.json"
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def render_quality_report(report: dict[str, Any]) -> None:
    counts = report["question_counts"]
    st.caption(
        f"{report['total_questions']} golden questions · {counts['easy']} easy · "
        f"{counts['table_cell']} table-cell · {counts['unanswerable']} unanswerable"
    )
    if report["gate_status"] == "PASS":
        st.success("RELEASE GATE: PASS")
    else:
        st.error("RELEASE GATE: DO NOT SHIP")
    st.caption(f"{report['failure_count']} question(s) failed. Threshold status is shown with each score.")

    metric_names = list(METRIC_LABELS)
    for start in range(0, len(metric_names), 3):
        columns = st.columns(3)
        for column, name in zip(columns, metric_names[start : start + 3]):
            score = report["metrics"].get(name)
            threshold = report["thresholds"].get(name)
            if score is None:
                value = "N/A"
                delta = "Not configured" if name == "llm_as_judge_score" else "Unavailable"
                delta_color = "off"
            else:
                value = f"{score:.3f}"
                passed = threshold is None or score >= threshold
                delta = f"{'PASS' if passed else 'FAIL'} · threshold {threshold:.2f}" if threshold is not None else "Measured"
                delta_color = "normal" if passed else "inverse"
            column.metric(METRIC_LABELS[name], value, delta=delta, delta_color=delta_color, border=True)

    ragas = report.get("ragas", {})
    st.caption(
        f"LLM-as-Judge: {report.get('judge_status', 'not configured')} · "
        f"RAGAS: {ragas.get('status', 'not run')}"
        + (f" · {ragas['reason']}" if ragas.get("reason") else "")
    )
    if ragas.get("metrics"):
        st.markdown("**RAGAS metrics**")
        st.dataframe(
            [{"Metric": name, "Score": f"{score:.3f}"} for name, score in ragas["metrics"].items()],
            hide_index=True,
        )

    st.subheader("Question scorecard")
    question_rows = [
        {
            "ID": item["id"],
            "Question": item["question"],
            "Type": item["type"],
            "Result": "PASS" if item["passed"] else "FAIL",
            "Failure class": item.get("failure_type") or "-",
            "Faithfulness": item.get("faithfulness"),
            "Relevance": item.get("answer_relevance"),
            "Context recall": item.get("context_recall"),
        }
        for item in report["results"]
    ]
    st.dataframe(question_rows, hide_index=True, height=520)

    st.subheader("Top-5 failures")
    failures = report.get("top_5_failures", [])
    if not failures:
        st.success("No failed questions in this evaluation.")
    for index, item in enumerate(failures, start=1):
        with st.expander(f"{index}. {item['id']} · {item['failure_type']} · {item['question']}"):
            st.markdown(f"**Root cause:** {item['root_cause']}")
            st.markdown(f"**Recommended targeted fix:** {item['recommended_fix']}")
            st.markdown(f"**Bot answer:** {item['answer']}")
            st.markdown("**Retrieved evidence**")
            for context in item.get("contexts", []):
                st.code(context, language="text")

    with st.expander("All question answers and evidence"):
        for item in report["results"]:
            status = "PASS" if item["passed"] else "FAIL"
            with st.expander(f"{item['id']} · {status} · {item['question']}"):
                st.markdown(f"**Answer:** {item['answer']}")
                st.markdown(f"**Failure class:** {item.get('failure_type') or 'None'}")
                if item.get("failure_types"):
                    st.markdown(f"**Failure labels:** {', '.join(item['failure_types'])}")
                st.markdown(f"**Citations:** {', '.join(item.get('citations', [])) or 'None'}")
                for context in item.get("contexts", []):
                    st.code(context, language="text")

    results_dir = APP_ROOT / "results"
    json_path = results_dir / "evaluation_results.json"
    csv_path = results_dir / "evaluation_results.csv"
    download_columns = st.columns(2)
    if json_path.exists():
        download_columns[0].download_button(
            "Download JSON results", json_path.read_bytes(), file_name="evaluation_results.json", mime="application/json"
        )
    if csv_path.exists():
        download_columns[1].download_button(
            "Download CSV results", csv_path.read_bytes(), file_name="evaluation_results.csv", mime="text/csv"
        )


workspace = initialize_workspace()
st.markdown(
    '<div class="hero"><h1>RAG Quality Gate</h1><p>Evaluate retrieval, grounded answers, and refusal behavior before release.</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Document ingestion")
    uploads = st.file_uploader(
        "Upload PDF or Excel files",
        type=["pdf", "xlsx", "xls"],
        accept_multiple_files=True,
        help="You can upload one or more PDF or Excel files.",
    )
    st.divider()
    st.subheader("Retrieval settings")
    serialization = st.selectbox(
        "Excel serialization",
        options=["row_text", "markdown_table", "column_wise"],
        format_func=lambda value: value.replace("_", " ").title(),
    )
    chunking = st.selectbox(
        "PDF chunking strategy",
        options=["recursive", "fixed", "section-aware"],
        format_func=lambda value: value.replace("-", " ").title(),
    )
    top_k = st.slider("Top-k chunks retrieved", min_value=1, max_value=10, value=4)
    ingest_clicked = st.button("Ingest documents", type="primary", width="stretch")

if uploads:
    st.caption(f"{len(uploads)} file(s) selected")
    st.dataframe([{"File": upload.name, "Type": upload.type, "Size": f"{upload.size / 1024:.1f} KB"} for upload in uploads], hide_index=True)

if ingest_clicked:
    if not uploads:
        st.warning("Upload at least one PDF or Excel file first.")
    else:
        documents_dir = workspace / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)
        for existing in documents_dir.iterdir():
            if existing.is_file():
                existing.unlink()
        for upload in uploads:
            (documents_dir / Path(upload.name).name).write_bytes(upload.getvalue())
        try:
            with st.spinner("Reading documents and building the index..."):
                pipeline = make_pipeline(workspace, chunking, serialization, top_k)
                chunk_count = pipeline.ingest(documents_dir)
            st.session_state.pipeline = pipeline
            st.success(f"Indexed {chunk_count} chunks from {len(uploads)} file(s).")
        except Exception as exc:
            st.error(f"Could not ingest the uploaded documents: {exc}")

chat_tab, chunks_tab, quality_tab = st.tabs(["Chat", "Browse Chunks", "Quality Gate"])

with chat_tab:
    st.subheader("Search and generation")
    question = st.text_input("Question", placeholder="What is the operating temperature range?", key="chat_question")
    ask_clicked = st.button("Get answer", type="primary", disabled="pipeline" not in st.session_state)
    if ask_clicked and question.strip():
        try:
            with st.spinner("Searching your documents..."):
                answer = st.session_state.pipeline.query(question.strip())
            st.markdown("### Answer")
            st.info(answer.text)
            st.caption(f"Generation mode: {answer.mode}")
            if answer.citations:
                st.markdown("### Sources")
                for citation in answer.citations:
                    st.write(citation)
            with st.expander(f"Retrieved evidence ({len(answer.retrieved)} chunks)"):
                for index, item in enumerate(answer.retrieved, 1):
                    st.markdown(f"**{index}. {metadata_label(item.chunk.metadata)}** · score {item.score:.3f}")
                    st.code(item.chunk.text, language="text")
        except Exception as exc:
            st.error(f"Could not answer the question: {exc}")
    elif ask_clicked:
        st.warning("Enter a question first.")
    elif "pipeline" not in st.session_state:
        st.info("Upload documents in the sidebar, then click Ingest documents to begin.")

with chunks_tab:
    st.subheader("Indexed document chunks")
    pipeline = st.session_state.get("pipeline")
    if pipeline is None:
        st.info("Ingest documents to browse their chunks and metadata.")
    else:
        pipeline.load()
        chunks = pipeline.store.items
        sources = sorted({item.metadata.get("source", "unknown") for item in chunks})
        selected_source = st.selectbox("Filter by source", ["All sources", *sources])
        visible_chunks = [
            item for item in chunks
            if selected_source == "All sources" or item.metadata.get("source") == selected_source
        ]
        st.caption(f"Showing {len(visible_chunks)} of {len(chunks)} indexed chunks")
        st.dataframe(
            [
                {"Source": metadata_label(item.metadata), "Chunk type": item.metadata.get("chunk_type", "text"), "Content": item.text}
                for item in visible_chunks
            ],
            hide_index=True,
        )

with quality_tab:
    st.subheader("RAG Quality Gate")
    st.caption("Runs the 20-question golden set against the project documents and release thresholds.")
    if st.button("Run Evaluation", type="primary", key="run_quality_gate"):
        try:
            with st.spinner("Running the golden set through the RAG pipeline..."):
                report = evaluate_quality_gate(EvaluationConfig.from_env(APP_ROOT))
            st.session_state.quality_report = report
            st.success("Evaluation complete.")
        except Exception as exc:
            st.error(f"Evaluation could not complete: {exc}")

    report = st.session_state.get("quality_report")
    if report is None:
        report = load_saved_quality_report()
        if report is not None:
            st.session_state.quality_report = report
    if report is None:
        st.info("Run the evaluation to see the release scorecard and failure analysis.")
    else:
        render_quality_report(report)