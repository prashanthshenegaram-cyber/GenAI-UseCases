from typing import Any
from pydantic import BaseModel, Field


class DocumentChunk(BaseModel):
    text: str
    metadata: dict[str, Any]
    embedding: list[float] | None = None

    def __init__(self, text: str, metadata: dict[str, Any], embedding: list[float] | None = None, **data: Any) -> None:
        super().__init__(text=text, metadata=metadata, embedding=embedding, **data)


class RetrievedChunk(BaseModel):
    chunk: DocumentChunk
    distance: float
    score: float

    def __init__(self, chunk: DocumentChunk, distance: float, score: float, **data: Any) -> None:
        super().__init__(chunk=chunk, distance=distance, score=score, **data)


class Answer(BaseModel):
    text: str
    citations: list[str] = Field(default_factory=list)
    retrieved: list[RetrievedChunk] = Field(default_factory=list)
    mode: str = "mock"

    @property
    def grounded(self) -> bool:
        return bool(self.citations) and "could not find" not in self.text.lower()
