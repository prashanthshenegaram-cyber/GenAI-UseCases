from pathlib import Path
from tempfile import mkdtemp

import streamlit as st

from app.config import Settings
from app.pipeline import RAGPipeline


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
    return f"{source} ({', '.join(location)})" if location else source


workspace = initialize_workspace()
st.markdown(
    '<div class="hero"><h1>Chat With Your Document</h1><p>Upload a PDF or Excel workbook, index it, and ask grounded questions with source citations.</p></div>',
    unsafe_allow_html=True,
)

with st.sidebar:
    st.header("Documents")
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
    ingest_clicked = st.button("Ingest documents", type="primary", use_container_width=True)

if uploads:
    st.caption(f"{len(uploads)} file(s) selected")
    st.dataframe(
        [{"File": upload.name, "Type": upload.type, "Size": f"{upload.size / 1024:.1f} KB"} for upload in uploads],
        hide_index=True,
        use_container_width=True,
    )

if ingest_clicked:
    if not uploads:
        st.warning("Upload at least one PDF or Excel file first.")
    else:
        documents_dir = workspace / "documents"
        documents_dir.mkdir(parents=True, exist_ok=True)
        for existing in documents_dir.iterdir():
            existing.unlink()
        for upload in uploads:
            (documents_dir / Path(upload.name).name).write_bytes(upload.getvalue())
        try:
            with st.spinner("Reading documents and building the index..."):
                pipeline = make_pipeline(workspace, chunking, serialization, top_k)
                chunk_count = pipeline.ingest(documents_dir)
            st.session_state.pipeline = pipeline
            st.session_state.settings = (chunking, serialization, top_k)
            st.success(f"Indexed {chunk_count} chunks from {len(uploads)} file(s).")
        except Exception as exc:
            st.error(f"Could not ingest the uploaded documents: {exc}")

st.subheader("Ask a question")
question = st.text_input("Question", placeholder="What is the operating temperature range?", label_visibility="collapsed")
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