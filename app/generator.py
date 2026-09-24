import re
from abc import ABC, abstractmethod
from .models import RetrievedChunk

REFUSAL = "I couldn't find that information in the provided documents."


class BaseLLMClient(ABC):
    @abstractmethod
    def generate(self, question: str, context: str, retrieved: list[RetrievedChunk]) -> str:
        raise NotImplementedError


class MockLLMClient(BaseLLMClient):
    """Deterministic extractive generator; this is intentionally not a real LLM."""

    def generate(self, question: str, context: str, retrieved: list[RetrievedChunk]) -> str:
        if not retrieved:
            return REFUSAL
        stop_words = {"what", "which", "where", "when", "does", "did", "have", "the", "for", "are", "was", "were", "how", "much", "that", "this"}
        terms = {word.lower() for word in re.findall(r"[A-Za-z0-9]+", question) if len(word) > 2 and word.lower() not in stop_words}
        candidates = []
        for item in retrieved:
            lines = [line.strip() for line in item.chunk.text.splitlines() if line.strip()]
            matches = [line for line in lines if any(term in line.lower() for term in terms)]
            candidates.extend(matches)
        return " ".join(dict.fromkeys(candidates))[:1000] or REFUSAL


class ConfigurableLLMClient(BaseLLMClient):
    def __init__(self, model: str = "mock", api_key: str | None = None, temperature: float = 0.0, top_p: float = 1.0, top_k: int = 40, max_output_tokens: int = 300) -> None:
        self.mode = "mock"
        self.client: object | None = None
        if api_key and model != "mock":
            try:
                from openai import OpenAI
                self.client = OpenAI(api_key=api_key)
                self.model, self.mode = model, "llm"
                self.temperature, self.top_p, self.top_k, self.max_output_tokens = temperature, top_p, top_k, max_output_tokens
            except ImportError:
                pass
        self.mock = MockLLMClient()

    def generate(self, question: str, context: str, retrieved: list[RetrievedChunk]) -> str:
        if self.mode == "mock":
            return self.mock.generate(question, context, retrieved)
        response = self.client.chat.completions.create(model=self.model, temperature=self.temperature, top_p=self.top_p, max_tokens=self.max_output_tokens, messages=[{"role": "system", "content": context}, {"role": "user", "content": question}])
        return response.choices[0].message.content or REFUSAL
