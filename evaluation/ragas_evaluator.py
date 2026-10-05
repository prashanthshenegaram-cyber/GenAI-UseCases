"""Optional RAGAS integration; local evidence metrics remain available offline."""

from __future__ import annotations

from typing import Any


def evaluate_with_ragas(
    results: list[dict[str, Any]], api_key: str | None, model: str
) -> dict[str, Any]:
    if not api_key:
        return {"status": "skipped", "reason": "LLM_API_KEY is not configured."}
    try:
        from datasets import Dataset
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings
        from ragas import evaluate
        from ragas.metrics import answer_relevancy, context_precision, context_recall, faithfulness

        answerable = [item for item in results if item["answerable"]]
        dataset = Dataset.from_list(
            [
                {
                    "question": item["question"],
                    "answer": item["answer"],
                    "contexts": item["contexts"],
                    "ground_truth": item["reference_answer"],
                }
                for item in answerable
            ]
        )
        scores = evaluate(
            dataset,
            metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
            llm=ChatOpenAI(model=model, api_key=api_key, temperature=0),
            embeddings=OpenAIEmbeddings(api_key=api_key),
        )
        return {"status": "complete", "metrics": {key: float(value) for key, value in scores.items()}}
    except Exception as exc:
        return {"status": "unavailable", "reason": f"RAGAS could not run: {exc}"}