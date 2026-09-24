from .models import RetrievedChunk


def format_citation(metadata: dict) -> str:
    pieces = [str(metadata.get("source", "unknown source"))]
    if metadata.get("page") is not None:
        pieces.append(f"page {metadata['page']}")
    if metadata.get("sheet"):
        pieces.append(f"{metadata['sheet']} sheet")
    if metadata.get("row") is not None:
        pieces.append(f"row {metadata['row']}")
    if metadata.get("table_id"):
        pieces.append(f"{metadata['table_id']}")
    return "[" + ", ".join(pieces) + "]"


def citations_for(chunks: list[RetrievedChunk]) -> list[str]:
    return list(dict.fromkeys(format_citation(item.chunk.metadata) for item in chunks))
