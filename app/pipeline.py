import logging
from pathlib import Path
from .citations import citations_for
from .config import Settings
from .context import assemble_context
from .embeddings import EmbeddingService
from .generator import ConfigurableLLMClient
from .loaders import load_document
from .models import Answer
from .retrieval import Retriever
from .vector_store import VectorStore

LOGGER = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.embeddings = EmbeddingService(settings.embedding_model)
        self.store = VectorStore(settings.vector_dir / "chunks.json")
        self.retriever = Retriever(self.store, self.embeddings, settings.top_k, settings.similarity_threshold)
        self.generator = ConfigurableLLMClient(settings.llm_model, settings.llm_api_key, settings.temperature, settings.top_p, settings.generation_top_k, settings.max_output_tokens)

    def ingest(self, input_dir: Path | None = None) -> int:
        directory = input_dir or self.settings.documents_dir
        chunks = []
        for path in sorted(directory.iterdir() if directory.exists() else []):
            if path.is_file() and path.suffix.lower() in {".pdf", ".xlsx", ".xls"}:
                chunks.extend(load_document(path, self.settings.chunking_strategy, self.settings.serialization))
        if not chunks:
            raise FileNotFoundError(f"No supported PDF/XLSX documents found in {directory}")
        self.store.items = []
        for start in range(0, len(chunks), 64):
            batch = chunks[start:start + 64]
            self.store.add(batch, self.embeddings.embed([chunk.text for chunk in batch]))
        self.store.persist()
        LOGGER.info("Ingested %d chunks", len(chunks))
        return len(chunks)

    def load(self) -> None:
        self.store.load()

    def query(self, question: str) -> Answer:
        self.load()
        retrieved = self.retriever.retrieve(question)
        context = assemble_context(question, retrieved)
        text = self.generator.generate(question, context, retrieved)
        return Answer(text=text, citations=citations_for(retrieved), retrieved=retrieved, mode=self.generator.mode)
