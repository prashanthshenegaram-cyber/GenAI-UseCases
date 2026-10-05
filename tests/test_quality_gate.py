import json

import pytest

from config.evaluation_config import DEFAULT_THRESHOLDS
from evaluation.evaluator import load_golden_dataset
from evaluation.failure_classifier import classify_failure
from evaluation.judge import parse_judgement
from evaluation.metrics import answer_relevance, context_precision, correct_refusal, faithfulness, threshold_results


def test_golden_dataset_has_required_mix():
    from pathlib import Path

    project_root = Path(__file__).resolve().parents[1]
    items = load_golden_dataset(project_root / "data" / "golden_dataset.json")
    assert len(items) == 20
    assert sum(item["type"] == "easy" for item in items) == 8
    assert sum(item["type"] == "table_cell" for item in items) == 6
    assert sum(item["type"] == "unanswerable" for item in items) == 6


def test_refusal_passes_only_for_unanswerable_question():
    unanswerable = {"answerable": False, "required_facts": []}
    answerable = {"answerable": True, "required_facts": [["220v"]]}
    refusal = "I couldn't find that information in the provided documents."
    assert answer_relevance(refusal, unanswerable) == 1.0
    assert correct_refusal(refusal, unanswerable) is True
    assert answer_relevance(refusal, answerable) == 0.0
    assert correct_refusal(refusal, answerable) is None
    assert faithfulness(refusal, [], answerable) == 0.0


def test_unanswerable_hallucination_is_generation_failure():
    item = {"answerable": False, "required_facts": []}
    failure = classify_failure(item, "The battery capacity is 5000 mAh.", ["sensor"], ["sensor"])
    assert failure["failure_type"] == "GENERATION_ERROR"


@pytest.mark.parametrize(
    ("corpus", "retrieved", "expected"),
    [
        ([], [], "CHUNKING_ERROR"),
        (["Voltage: 220V"], ["Weight: 4.5 kg"], "RETRIEVAL_MISS"),
        (["Voltage: 220V"], ["Voltage: 220V"], "GENERATION_ERROR"),
    ],
)
def test_answerable_failure_root_cause(corpus, retrieved, expected):
    item = {"answerable": True, "required_facts": [["220v"]]}
    failure = classify_failure(item, "No answer.", retrieved, corpus)
    assert failure["failure_type"] == expected


def test_supporting_context_and_refusal_is_over_refusal():
    item = {"answerable": True, "required_facts": [["220v"]]}
    failure = classify_failure(
        item,
        "I couldn't find that information in the provided documents.",
        ["Voltage: 220V"],
        ["Voltage: 220V"],
    )
    assert failure["failure_type"] == "OVER_REFUSAL"
    assert "INCORRECT_REFUSAL" not in failure["failure_types"]


def test_answerable_refusal_without_retrieved_evidence_is_labeled():
    item = {"answerable": True, "required_facts": [["220v"]]}
    failure = classify_failure(
        item,
        "I couldn't find that information in the provided documents.",
        ["Weight: 4.5 kg"],
        ["Voltage: 220V"],
    )
    assert failure["failure_type"] == "RETRIEVAL_MISS"
    assert "INCORRECT_REFUSAL" in failure["failure_types"]


def test_threshold_equality_passes_and_unavailable_fails():
    values = {name: threshold for name, threshold in DEFAULT_THRESHOLDS.items()}
    assert all(threshold_results(values, DEFAULT_THRESHOLDS).values())
    values["faithfulness"] = None
    assert not threshold_results(values, DEFAULT_THRESHOLDS)["faithfulness"]


def test_empty_retrieval_has_zero_context_precision():
    assert context_precision([], [["220v"]]) == 0.0


def test_judge_structured_json_is_validated_and_normalized():
    result = parse_judgement(json.dumps({
        "score": 4,
        "faithful": True,
        "answers_question": True,
        "correct_refusal": False,
        "reason": "Evidence supports the answer.",
    }))
    assert result["normalized_score"] == 0.75
    with pytest.raises(ValueError):
        parse_judgement('{"score": 7}')