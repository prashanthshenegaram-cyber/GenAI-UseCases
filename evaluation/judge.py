"""Optional OpenAI LLM-as-a-judge using strict structured JSON output."""

from __future__ import annotations

import json
from typing import Any


JUDGE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "integer"},
        "faithful": {"type": "boolean"},
        "answers_question": {"type": "boolean"},
        "correct_refusal": {"type": "boolean"},
        "reason": {"type": "string"},
    },
    "required": ["score", "faithful", "answers_question", "correct_refusal", "reason"],
    "additionalProperties": False,
}


def parse_judgement(content: str) -> dict[str, Any]:
    payload = json.loads(content)
    if not isinstance(payload, dict):
        raise ValueError("Judge response must be a JSON object")
    if not isinstance(payload.get("score"), int) or not 1 <= payload["score"] <= 5:
        raise ValueError("Judge score must be an integer from 1 to 5")
    for key in ("faithful", "answers_question", "correct_refusal"):
        if not isinstance(payload.get(key), bool):
            raise ValueError(f"Judge field {key!r} must be boolean")
    if not isinstance(payload.get("reason"), str):
        raise ValueError("Judge reason must be a string")
    payload["normalized_score"] = (payload["score"] - 1) / 4
    return payload


class LLMJudge:
    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key)
        self.model = model

    def score(self, item: dict[str, Any], answer: str, contexts: list[str]) -> dict[str, Any]:
        request = {
            "question": item["question"],
            "reference_answer": item.get("reference_answer"),
            "answerable": item["answerable"],
            "answer": answer,
            "retrieved_contexts": contexts,
        }
        response = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Evaluate a RAG response. Score correctness, relevance, and grounding from 1 (poor) "
                        "to 5 (excellent). An unanswerable question is correct only when the answer refuses; "
                        "an answerable question must not receive credit for refusal. Use only the supplied context."
                    ),
                },
                {"role": "user", "content": json.dumps(request, ensure_ascii=False)},
            ],
            response_format={
                "type": "json_schema",
                "json_schema": {"name": "rag_quality_judgement", "strict": True, "schema": JUDGE_SCHEMA},
            },
        )
        content = response.choices[0].message.content or "{}"
        return parse_judgement(content)