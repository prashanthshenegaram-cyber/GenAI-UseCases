import re
from typing import Any
from .models import DocumentChunk


def _parts(text: str, size: int = 700, overlap: int = 100) -> list[str]:
    text = text.strip()
    if not text:
        return []
    result = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        result.append(text[start:end].strip())
        if end == len(text):
            break
        start = max(start + 1, end - overlap)
    return [part for part in result if part]


def chunk_text(text: str, metadata: dict[str, Any], strategy: str = "recursive") -> list[DocumentChunk]:
    if strategy == "fixed":
        pieces = _parts(text, 500, 0)
    elif strategy == "section-aware":
        sections = re.split(r"\n(?=(?:[A-Z][A-Za-z0-9 &/-]{2,60})(?:\n|:))", text)
        pieces = [piece.strip() for section in sections for piece in _parts(section, 900, 100) if piece.strip()]
    else:
        paragraphs = re.split(r"\n\s*\n", text)
        pieces = [piece for paragraph in paragraphs for piece in _parts(paragraph, 700, 100)]
    return [DocumentChunk(piece, {**metadata, "chunk_type": metadata.get("chunk_type", "text")}) for piece in pieces]
