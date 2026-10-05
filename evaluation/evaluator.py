"""Run the golden set against the existing Week-2 RAG pipeline."""

from __future__ import annotations

import json
import os
from collections import Counter
from dataclasses import replace
from pathlib import Path
from statistics import mean
from typing import Any

from app.config import Settings
from app.loaders import load_document
from app.pipeline import RAGPipeline
from config.evaluation_config import EvaluationConfig

from .failure_classifier import classify_failure
from .judge import LLMJudge
from .metrics import (
    answer_relevance,
    context_precision,
    correct_refusal,
    evidence_recall,
    faithfulness,
    threshold_results,
)
from .ragas_evaluator import evaluate_with_ragas
from .report_generator import write_reports


def load_golden_dataset(path: Path) -> list[dict[str, Any]]:
    items = json.loads(path.read_text(encoding="utf-8"))
    expected_counts = Counter(item["type"] for item in items)
    if len(items) != 20 or expected_counts != {"easy": 8, "table_cell": 6, "unanswerable": 6}:
        raise ValueError("Golden dataset must contain 8 easy, 6 table_cell, and 6 unanswerable questions.")
    identifiers = [item["id"] for item in items]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Golden dataset question IDs must be unique.")
    return items


def _corpus_contexts(settings: Settings) -> list[str]:
    contexts: list[str] = []
    for path in sorted(settings.documents_dir.iterdir()):
        if path.is_file() and path.suffix.lower() in {".pdf", ".xlsx", ".xls"}:
            contexts.extend(chunk.text for chunk in load_document(path, settings.chunking_strategy, settings.serialization))
    return contexts


def _average(values: list[float | None]) -> float | None:
    available = [value for value in values if value is not None]
    return mean(available) if available else None


def evaluate_quality_gate(
    evaluation_config: EvaluationConfig | None = None,
    rag_settings: Settings | None = None,
) -> dict[str, Any]:
    gate_config = evaluation_config or EvaluationConfig.from_env()
    settings = rag_settings or Settings.from_env()
    settings = replace(settings, vector_dir=gate_config.vector_dir)
    dataset = load_golden_dataset(gate_config.dataset_path)

    pipeline = RAGPipeline(settings)
    pipeline.ingest()
    corpus_contexts = _corpus_contexts(settings)
    api_key = settings.llm_api_key or os.getenv("LLM_API_KEY")
    judge = LLMJudge(api_key, gate_config.judge_model) if api_key and gate_config.judge_enabled else None

    results: list[dict[str, Any]] = []
    for item in dataset:
        answer = pipeline.query(item["question"])
        contexts = [retrieved.chunk.text for retrieved in answer.retrieved]
        retrieved_sources = [retrieved.chunk.metadata.get("source") for retrieved in answer.retrieved]
        expected_sources = item["expected_sources"]
        hit_rate = (
            float(not expected_sources or any(source in retrieved_sources for source in expected_sources))
            if item["answerable"] else None
        )
        precision = context_precision(contexts, item["required_facts"])
        recall = evidence_recall(contexts, item["required_facts"])
        faithfulness_score = faithfulness(answer.text, contexts, item)
        relevance_score = answer_relevance(answer.text, item)
        refusal_score = correct_refusal(answer.text, item)
        passed = relevance_score == 1.0 and faithfulness_score == 1.0 and (refusal_score is not False)
        failure = None if passed else classify_failure(item, answer.text, contexts, corpus_contexts)
        judge_result = None
        if judge:
            try:
                judge_result = judge.score(item, answer.text, contexts)
            except Exception as exc:
                judge_result = {"error": str(exc), "normalized_score": None}
        result = {
            **item,
            "answer": answer.text,
            "mode": answer.mode,
            "citations": answer.citations,
            "contexts": contexts,
            "retrieved": [
                {"metadata": retrieved.chunk.metadata, "score": retrieved.score, "distance": retrieved.distance}
                for retrieved in answer.retrieved
            ],
            "passed": passed,
            "context_precision": precision,
            "context_recall": recall,
            "hit_rate": hit_rate,
            "faithfulness": faithfulness_score,
            "answer_relevance": relevance_score,
            "correct_refusal": refusal_score,
            "judge_score": judge_result.get("normalized_score") if judge_result else None,
            "judge": judge_result,
        }
        if failure:
            result.update(failure)
        else:
            result.update({"failure_type": None, "failure_types": [], "root_cause": None, "recommended_fix": None})
        results.append(result)

    metrics: dict[str, float | None] = {
        "context_precision": _average([item["context_precision"] for item in results if item["answerable"]]),
        "context_recall": _average([item["context_recall"] for item in results if item["answerable"]]),
        "hit_rate": _average([item["hit_rate"] for item in results if item["answerable"]]),
        "faithfulness": _average([item["faithfulness"] for item in results]),
        "answer_relevance": _average([item["answer_relevance"] for item in results]),
        "correct_refusal_rate": _average([float(item["correct_refusal"]) for item in results if item["correct_refusal"] is not None]),
        "llm_as_judge_score": _average([item["judge_score"] for item in results]),
    }
    if judge is None:
        judge_status = "disabled" if not gate_config.judge_enabled else "not_configured"
    elif metrics["llm_as_judge_score"] is None:
        judge_status = "unavailable"
    else:
        judge_status = "complete"
    gate_metrics = {name: metrics[name] for name in gate_config.thresholds}
    threshold_status = threshold_results(gate_metrics, gate_config.thresholds)
    ragas = evaluate_with_ragas(results, api_key, gate_config.judge_model) if gate_config.use_ragas else {
        "status": "disabled", "reason": "Set RAG_GATE_USE_RAGAS=true to request optional RAGAS scoring."
    }
    failures = [item for item in results if not item["passed"]]
    failure_rank = lambda item: sum(
        item[name] if item[name] is not None else 0.0
        for name in ("faithfulness", "answer_relevance", "context_precision", "context_recall", "hit_rate")
    )
    top_5_failures = sorted(failures, key=failure_rank)[:5]
    question_counts = Counter(item["type"] for item in dataset)
    report = {
        "gate_status": "PASS" if all(threshold_status.values()) else "FAIL",
        "total_questions": len(results),
        "question_counts": dict(question_counts),
        "metrics": metrics,
        "thresholds": gate_config.thresholds,
        "threshold_status": threshold_status,
        "judge_status": judge_status,
        "ragas": ragas,
        "failure_count": len(failures),
        "top_5_failures": top_5_failures,
        "results": results,
    }
    write_reports(report, gate_config.results_dir)
    return report