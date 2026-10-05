"""Classify failed answers by checking source, retrieved evidence, and output."""

from __future__ import annotations

from typing import Any

from .metrics import fact_is_present, is_refusal


FAILURE_FIXES = {
    "RETRIEVAL_MISS": (
        "Tune the existing retriever: inspect query-to-chunk scores, top-k and similarity threshold, "
        "then compare embedding models against this missed evidence."
    ),
    "GENERATION_ERROR": (
        "Keep the retrieved evidence fixed and tighten the existing grounded-answer prompt or output "
        "validation so the response returns the supported facts without invention."
    ),
    "CHUNKING_ERROR": (
        "Inspect the existing PDF/Excel loader and chunk output for this source; preserve table headers "
        "and row/cell relationships before changing retrieval."
    ),
    "INCORRECT_REFUSAL": (
        "The answerable item was refused; inspect evidence availability and refusal behavior before "
        "loosening the refusal prompt."
    ),
    "OVER_REFUSAL": (
        "Supporting evidence reached the generator but it refused; adjust the refusal condition to "
        "answer when retrieved context contains the required facts."
    ),
}


def classify_failure(
    item: dict[str, Any],
    answer: str,
    retrieved_contexts: list[str],
    corpus_contexts: list[str],
) -> dict[str, Any] | None:
    refusal = is_refusal(answer)
    required_facts = item["required_facts"]
    if not item["answerable"]:
        if refusal:
            return None
        return {
            "failure_type": "GENERATION_ERROR",
            "failure_types": ["GENERATION_ERROR"],
            "root_cause": "The question is deliberately unanswerable, but the pipeline returned a substantive answer.",
            "recommended_fix": FAILURE_FIXES["GENERATION_ERROR"],
        }

    corpus_has_evidence = all(
        fact_is_present("\n".join(corpus_contexts), aliases) for aliases in required_facts
    )
    retrieval_has_evidence = all(
        fact_is_present("\n".join(retrieved_contexts), aliases) for aliases in required_facts
    )
    if not corpus_has_evidence:
        primary = "CHUNKING_ERROR"
        cause = "Expected evidence is absent from chunks produced by the existing document loaders."
    elif not retrieval_has_evidence:
        primary = "RETRIEVAL_MISS"
        cause = "Expected evidence exists in the loaded corpus but is absent from retrieved context."
    elif refusal:
        primary = "OVER_REFUSAL"
        cause = "Retrieved context contains expected evidence, but the generator refused to answer."
    else:
        primary = "GENERATION_ERROR"
        cause = "Retrieved context contains expected evidence, but the answer omitted or misstated it."

    failure_types = [primary]
    if refusal and primary != "OVER_REFUSAL":
        failure_types.append("INCORRECT_REFUSAL")
    return {
        "failure_type": primary,
        "failure_types": failure_types,
        "root_cause": cause,
        "recommended_fix": FAILURE_FIXES[primary],
    }