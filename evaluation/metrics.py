"""Evidence-based metric calculations for individual RAG responses."""

from __future__ import annotations

import re
from typing import Any

from app.generator import REFUSAL


def normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.lower().replace("−", "-")).strip()


def is_refusal(answer: str) -> bool:
    normalized = normalize_text(answer)
    return any(
        phrase in normalized
        for phrase in (
            normalize_text(REFUSAL),
            "i cannot answer",
            "i can't answer",
            "not available in the provided documents",
            "the provided documents do not state",
        )
    )


def fact_is_present(text: str, aliases: list[str]) -> bool:
    normalized = normalize_text(text)
    return any(normalize_text(alias) in normalized for alias in aliases)


def evidence_recall(contexts: list[str], required_facts: list[list[str]]) -> float | None:
    if not required_facts:
        return None
    context = "\n".join(contexts)
    return sum(fact_is_present(context, aliases) for aliases in required_facts) / len(required_facts)


def context_precision(contexts: list[str], required_facts: list[list[str]]) -> float | None:
    if not required_facts:
        return None
    if not contexts:
        return 0.0
    relevant_ranks = [
        index
        for index, context in enumerate(contexts, start=1)
        if any(fact_is_present(context, aliases) for aliases in required_facts)
    ]
    if not relevant_ranks:
        return 0.0
    return sum(rank / index for rank, index in enumerate(relevant_ranks, start=1)) / len(relevant_ranks)


def answer_relevance(answer: str, item: dict[str, Any]) -> float:
    if not item["answerable"]:
        return 1.0 if is_refusal(answer) else 0.0
    facts = item["required_facts"]
    if not facts or is_refusal(answer):
        return 0.0
    return sum(fact_is_present(answer, aliases) for aliases in facts) / len(facts)


def faithfulness(answer: str, contexts: list[str], item: dict[str, Any]) -> float:
    if is_refusal(answer):
        return 1.0 if not item["answerable"] else 0.0
    if not item["answerable"]:
        return 0.0
    facts_in_answer = [
        aliases for aliases in item["required_facts"] if fact_is_present(answer, aliases)
    ]
    if not facts_in_answer:
        return 0.0
    context = "\n".join(contexts)
    return sum(fact_is_present(context, aliases) for aliases in facts_in_answer) / len(facts_in_answer)


def correct_refusal(answer: str, item: dict[str, Any]) -> bool | None:
    if item["answerable"]:
        return None
    return is_refusal(answer)


def threshold_results(metrics: dict[str, float | None], thresholds: dict[str, float]) -> dict[str, bool]:
    return {
        name: metrics.get(name) is not None and metrics[name] >= threshold
        for name, threshold in thresholds.items()
    }