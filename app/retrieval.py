import logging
from .embeddings import EmbeddingService
from .models import RetrievedChunk
from .vector_store import VectorStore

LOGGER = logging.getLogger(__name__)


class Retriever:
    def __init__(self, store: VectorStore, embeddings: EmbeddingService, top_k: int = 4, threshold: float | None = None) -> None:
        self.store, self.embeddings, self.top_k, self.threshold = store, embeddings, top_k, threshold

    def retrieve(self, question: str) -> list[RetrievedChunk]:
        results = self.store.search(self.embeddings.embed([question])[0], self.top_k, self.threshold)
        LOGGER.info("Retrieved %d chunks for query", len(results))
        return results
