"""Dedicated PDF table extraction helper used by the PDF loader."""

from pathlib import Path
from .models import DocumentChunk


def extract_pdf_tables(path: Path) -> list[DocumentChunk]:
    from .loaders import load_pdf

    return [chunk for chunk in load_pdf(path) if chunk.metadata.get("chunk_type") == "table"]