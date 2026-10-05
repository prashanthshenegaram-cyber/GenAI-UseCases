import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Settings:
    root: Path = Path(__file__).resolve().parent.parent
    documents_dir: Path = Path("data/documents")
    vector_dir: Path = Path("data/vector_store")
    results_dir: Path = Path("results")
    chunking_strategy: str = "recursive"
    serialization: str = "row_text"
    top_k: int = 4
    similarity_threshold: float | None = None
    embedding_model: str = "all-MiniLM-L6-v2"
    llm_model: str = "mock"
    temperature: float = 0.0
    top_p: float = 1.0
    generation_top_k: int = 40
    max_output_tokens: int = 300
    llm_api_key: str | None = None

    def __post_init__(self) -> None:
        self.documents_dir = self._resolve(self.documents_dir)
        self.vector_dir = self._resolve(self.vector_dir)
        self.results_dir = self._resolve(self.results_dir)
        for name in ("chunking_strategy", "serialization"):
            value = getattr(self, name).lower()
            if name == "chunking_strategy" and value not in {"fixed", "recursive", "section-aware"}:
                raise ValueError("chunking_strategy must be fixed, recursive, or section-aware")
            if name == "serialization" and value not in {"row_text", "markdown_table", "column_wise"}:
                raise ValueError("serialization must be row_text, markdown_table, or column_wise")
            setattr(self, name, value)
        if self.top_k < 1:
            raise ValueError("top_k must be at least 1")

    def _resolve(self, value: Path) -> Path:
        return value if value.is_absolute() else self.root / value

    @classmethod
    def from_env(cls, **overrides: object) -> "Settings":
        def value(name: str, default: object) -> object:
            return overrides.get(name, os.getenv(name.upper(), default))

        threshold = value("similarity_threshold", None)
        return cls(
            chunking_strategy=str(value("chunking_strategy", "recursive")),
            serialization=str(value("serialization", "row_text")),
            top_k=int(value("top_k", 4)),
            similarity_threshold=None if threshold in (None, "", "none") else float(threshold),
            embedding_model=str(value("embedding_model", "all-MiniLM-L6-v2")),
            llm_model=str(value("llm_model", "mock")),
            temperature=float(value("temperature", 0.0)),
            top_p=float(value("top_p", 1.0)),
            generation_top_k=int(value("top_k_generation", 40)),
            max_output_tokens=int(value("max_output_tokens", 300)),
            llm_api_key=os.getenv("LLM_API_KEY"),
        )
