"""Write the JSON, CSV, scorecard, and failure-analysis artifacts."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any


def write_reports(report: dict[str, Any], results_dir: Path) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    (results_dir / "evaluation_results.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    with (results_dir / "evaluation_results.csv").open("w", newline="", encoding="utf-8") as stream:
        columns = [
            "id", "type", "question", "answer", "passed", "failure_type", "failure_types",
            "root_cause", "recommended_fix", "context_precision", "context_recall", "hit_rate",
            "faithfulness", "answer_relevance", "judge_score",
        ]
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        for item in report["results"]:
            row = {column: item.get(column) for column in columns}
            row["failure_types"] = ";".join(item.get("failure_types", []))
            writer.writerow(row)
    (results_dir / "scorecard.md").write_text(render_scorecard(report), encoding="utf-8")
    (results_dir / "failure_analysis.md").write_text(render_failure_analysis(report), encoding="utf-8")


def render_scorecard(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# RAG Quality Gate Scorecard", "",
        f"**Overall gate: {report['gate_status']}**", "",
        f"Evaluated {report['total_questions']} golden questions ({report['question_counts']['easy']} easy, "
        f"{report['question_counts']['table_cell']} table-cell, {report['question_counts']['unanswerable']} unanswerable).", "",
        "## Metrics", "", "| Metric | Score | Threshold | Status |", "|---|---:|---:|---|",
    ]
    for name, threshold in report["thresholds"].items():
        score = metrics.get(name)
        status = "PASS" if report["threshold_status"][name] else "FAIL"
        formatted_score = "N/A" if score is None else f"{score:.3f}"
        lines.append(f"| {name} | {formatted_score} | {threshold:.3f} | {status} |")
    judge_score = metrics.get("llm_as_judge_score")
    lines.extend([
        "", f"LLM-as-Judge score: {'N/A (not configured)' if judge_score is None else f'{judge_score:.3f}'}.",
        f"RAGAS: {report['ragas']['status']}" + (f" ({report['ragas']['reason']})" if report['ragas'].get('reason') else ""),
        "", "## Question Results", "", "| ID | Type | Result | Failure | Question |", "|---|---|---|---|---|",
    ])
    lines.extend(
        f"| {item['id']} | {item['type']} | {'PASS' if item['passed'] else 'FAIL'} | "
        f"{item.get('failure_type') or '-'} | {item['question'].replace('|', '\\|')} |"
        for item in report["results"]
    )
    return "\n".join(lines) + "\n"


def render_failure_analysis(report: dict[str, Any]) -> str:
    failures = [item for item in report["results"] if not item["passed"]]
    top_failures = report["top_5_failures"]
    lines = [
        "# Failure Analysis", "",
        f"{len(failures)} of {report['total_questions']} questions failed.", "",
        "Failure classes distinguish source chunking/loading, retrieval, and generation; "
        "answerable refusals also carry the `INCORRECT_REFUSAL` label.", "",
        "## Top-5 Failures", "",
    ]
    if not top_failures:
        lines.append("No failures in this run.")
    for index, item in enumerate(top_failures, start=1):
        lines.extend([
            f"### {index}. {item['id']} - {item['failure_type']}", "",
            f"Question: {item['question']}", "",
            f"Answer: {item['answer']}", "",
            f"Root cause: {item['root_cause']}", "",
            f"Recommended targeted fix: {item['recommended_fix']}", "",
        ])
    return "\n".join(lines).rstrip() + "\n"