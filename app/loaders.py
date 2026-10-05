import logging
from pathlib import Path
from typing import Any
from .chunking import chunk_text
from .excel_serializer import serialize_rows
from .models import DocumentChunk

LOGGER = logging.getLogger(__name__)


def load_pdf(path: Path, strategy: str = "recursive") -> list[DocumentChunk]:
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(path))
        chunks: list[DocumentChunk] = []
        for page_number, page in enumerate(reader.pages, 1):
            text = page.extract_text() or ""
            chunks.extend(chunk_text(text, {"source": path.name, "file_type": "pdf", "page": page_number}, strategy))
        try:
            import pdfplumber
            with pdfplumber.open(path) as pdf:
                for page_number, page in enumerate(pdf.pages, 1):
                    for table_index, table in enumerate(page.extract_tables() or [], 1):
                        rows = [[str(cell or "").strip() for cell in row] for row in table if row]
                        if len(rows) < 2:
                            continue
                        header, body = rows[0], rows[1:]
                        table_text = "Table: " + " | ".join(f"{key} | {value}" for key, value in zip(header, body[0]))
                        table_text += "\n" + "\n".join(" | ".join(row) for row in body)
                        chunks.append(DocumentChunk(table_text, {"source": path.name, "file_type": "pdf", "page": page_number, "table_id": f"table-{table_index}", "chunk_type": "table"}))
        except ImportError:
            LOGGER.info("pdfplumber unavailable; skipping PDF table path")
        return chunks
    except Exception as exc:
        raise ValueError(f"Could not parse PDF {path}: {exc}") from exc


def load_excel(path: Path, strategy: str = "row_text") -> list[DocumentChunk]:
    try:
        import pandas as pd
        workbook = pd.read_excel(path, sheet_name=None)
    except Exception as exc:
        raise ValueError(f"Could not parse Excel workbook {path}: {exc}") from exc
    chunks: list[DocumentChunk] = []
    for sheet, frame in workbook.items():
        frame = frame.fillna("")
        rows = frame.to_dict(orient="records")
        serializations = serialize_rows(rows, strategy)
        for index, text in enumerate(serializations):
            metadata: dict[str, Any] = {"source": path.name, "file_type": "xlsx", "sheet": sheet, "chunk_type": "excel_row", "serialization": strategy}
            if strategy == "row_text":
                metadata["row"] = index + 2
            chunks.append(DocumentChunk(text, metadata))
    return chunks


def load_document(path: Path, chunking_strategy: str = "recursive", serialization: str = "row_text") -> list[DocumentChunk]:
    if path.suffix.lower() == ".pdf":
        return load_pdf(path, chunking_strategy)
    if path.suffix.lower() in {".xlsx", ".xls"}:
        return load_excel(path, serialization)
    raise ValueError(f"Unsupported file type: {path.suffix}")
