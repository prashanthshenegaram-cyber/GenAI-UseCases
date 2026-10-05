import json
import math
from pathlib import Path
from .models import DocumentChunk, RetrievedChunk


class VectorStore:
    """Small vector-store interface; Chroma can replace this implementation later."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self.items: list[DocumentChunk] = []

    def add(self, chunks: list[DocumentChunk], embeddings: list[list[float]]) -> None:
        self.items.extend(DocumentChunk(c.text, c.metadata, vector) for c, vector in zip(chunks, embeddings))

    def persist(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([{"text": c.text, "metadata": c.metadata, "embedding": c.embedding} for c in self.items], ensure_ascii=False, indent=2), encoding="utf-8")

    def load(self) -> None:
        if self.path.exists():
            self.items = [DocumentChunk(x["text"], x["metadata"], x["embedding"]) for x in json.loads(self.path.read_text(encoding="utf-8"))]

    def search(self, query_vector: list[float], top_k: int = 4, threshold: float | None = None) -> list[RetrievedChunk]:
        results = []
        for chunk in self.items:
            vector = chunk.embedding or []
            distance = math.sqrt(sum((a - b) ** 2 for a, b in zip(query_vector, vector)))
            score = 1 / (1 + distance)
            if threshold is None or score >= threshold:
                results.append(RetrievedChunk(chunk, distance, score))
        return sorted(results, key=lambda item: item.distance)[:top_k]
