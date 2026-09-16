import json
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from .config import FIELDS, GROUND_TRUTH_DIR, OUTPUTS_DIR

logger = logging.getLogger(__name__)


def normalize_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip().lower()


def compare_fields(pred: Dict[str, Any], truth: Dict[str, Any]) -> Dict[str, Any]:
    """Return field-level evaluation summary."""
    report = {}
    for field in FIELDS:
        p = pred.get(field)
        t = truth.get(field)
        if p is None and t is None:
            status = "correct_absence"
        elif p is None and t is not None:
            status = "missed_extraction"
        elif p is not None and t is None:
            status = "hallucination"
        else:
            status = "match"
        report[field] = {
            "status": status,
            "pred": p,
            "truth": t,
        }
    return report


def evaluate_prediction(pred: Dict[str, Any], truth: Dict[str, Any]) -> Dict[str, Any]:
    metrics = {
        "total_fields": len(FIELDS),
        "matches": 0,
        "hallucinations": 0,
        "misses": 0,
        "correct_absence": 0,
        "precision": 0.0,
        "recall": 0.0,
        "f1": 0.0,
        "accuracy": 0.0,
        "tax_absence_accuracy": 0.0,
        "tax_hallucination_count": 0,
        "tax_hallucination_rate": 0.0,
    }

    hallucinations = []
    tax_hallucinations = []
    field_report = compare_fields(pred, truth)
    for field, item in field_report.items():
        if item["status"] == "match":
            metrics["matches"] += 1
        elif item["status"] == "hallucination":
            metrics["hallucinations"] += 1
            hallucinations.append(field)
            if field == "tax":
                tax_hallucinations.append(field)
        elif item["status"] == "missed_extraction":
            metrics["misses"] += 1
        elif item["status"] == "correct_absence":
            metrics["correct_absence"] += 1

    # Tax-specific measure based on ground truth.
    if truth.get("tax") is None:
        # Number of invoices with absent tax in truth, correct prediction is tax null.
        metrics["tax_absence_accuracy"] = 1.0 if pred.get("tax") is None else 0.0
        metrics["tax_hallucination_count"] = 1 if pred.get("tax") is not None else 0
        metrics["tax_hallucination_rate"] = metrics["tax_hallucination_count"] / 1.0 if metrics["tax_hallucination_count"] else 0.0

    denom = metrics["total_fields"]
    metrics["accuracy"] = metrics["matches"] / denom if denom else 0.0

    # Standard binary metrics at field level.
    tp = metrics["matches"]
    fp = metrics["hallucinations"]
    fn = metrics["misses"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    metrics["precision"] = precision
    metrics["recall"] = recall
    metrics["f1"] = f1

    metrics["field_report"] = field_report
    metrics["hallucination_fields"] = hallucinations
    metrics["tax_hallucination_fields"] = tax_hallucinations
    return metrics


def load_ground_truth(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_prediction(path: Path) -> Dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_all(prompt_version: str = "v5") -> Dict[str, Any]:
    """Evaluate all invoice predictions against local ground_truth files."""
    results = {}
    for truth_path in sorted(GROUND_TRUTH_DIR.glob("*.json")):
        invoice_id = truth_path.stem
        pred_path = OUTPUTS_DIR / f"{invoice_id}_{prompt_version}_output.json"
        if not pred_path.exists():
            continue
        pred = load_prediction(pred_path)
        truth = load_ground_truth(truth_path)
        results[invoice_id] = evaluate_prediction(pred, truth)
    return results


def aggregate_metrics(result_set: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    """Aggregate a set of per-invoice metrics into a single metrics object."""
    if not result_set:
        return {
            "precision": 0.0,
            "recall": 0.0,
            "f1": 0.0,
            "accuracy": 0.0,
            "hallucinations": 0,
            "tax_hallucinations": 0,
        }

    total_precision = 0.0
    total_recall = 0.0
    total_f1 = 0.0
    total_accuracy = 0.0
    hallucinations = 0
    tax_hallucinations = 0

    for item in result_set.values():
        total_precision += item.get("precision", 0.0)
        total_recall += item.get("recall", 0.0)
        total_f1 += item.get("f1", 0.0)
        total_accuracy += item.get("accuracy", 0.0)
        hallucinations += len(item.get("hallucination_fields", []))
        tax_hallucinations += len(item.get("tax_hallucination_fields", []))

    n = len(result_set)
    return {
        "precision": total_precision / n,
        "recall": total_recall / n,
        "f1": total_f1 / n,
        "accuracy": total_accuracy / n,
        "hallucinations": hallucinations,
        "tax_hallucinations": tax_hallucinations,
    }
