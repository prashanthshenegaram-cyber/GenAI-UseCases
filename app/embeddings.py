import hashlib
import logging
import math
from typing import Sequence

LOGGER = logging.getLogger(__name__)


class EmbeddingService:
    """Local sentence-transformers embeddings with a deterministic fallback."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", dimensions: int = 384) -> None:
        self.dimensions = dimensions
        self._model = None
        if model_name.lower() in {"hash", "mock", "local-hash"}:
            LOGGER.info("Using deterministic hashing embeddings")
            return
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(model_name)
            self.dimensions = self._model.get_sentence_embedding_dimension()
            LOGGER.info("Using embedding model %s", model_name)
        except Exception as exc:
            LOGGER.warning("Local embedding model unavailable; using hashing fallback: %s", exc)

    def embed(self, texts: Sequence[str]) -> list[list[float]]:
        if self._model:
            return [list(map(float, vector)) for vector in self._model.encode(list(texts), normalize_embeddings=True)]
        return [self._hash_embedding(text) for text in texts]

    def _hash_embedding(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        for token in text.lower().split():
            digest = hashlib.sha256(token.encode()).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimensions
            vector[index] += 1.0 if digest[4] % 2 else -1.0
        norm = math.sqrt(sum(value * value for value in vector)) or 1.0
        return [value / norm for value in vector]
