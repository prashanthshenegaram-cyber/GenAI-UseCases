"""Run the RAG Quality Gate over data/golden_dataset.json."""

from evaluation.evaluator import evaluate_quality_gate


def main() -> int:
    report = evaluate_quality_gate()
    print(f"Evaluated {report['total_questions']} golden questions")
    print(f"RAG Quality Gate: {report['gate_status']}")
    for name, value in report["metrics"].items():
        print(f"{name}: {'N/A' if value is None else f'{value:.3f}'}")
    print("Reports written to results/evaluation_results.json, evaluation_results.csv, scorecard.md, and failure_analysis.md")
    return 0 if report["gate_status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())