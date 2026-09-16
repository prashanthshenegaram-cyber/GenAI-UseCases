"""End-to-end demo runner for the Invoice / Receipt Field Extractor.

Run from the repository root with:
    python demo.py

The demo uses the real project modules. It does not hard-code evaluation
metrics; metrics are calculated from the generated outputs and local truth.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.config import BASE_DIR, GROUND_TRUTH_DIR, INVOICES_DIR, OUTPUTS_DIR, RESULTS_DIR
from src.evaluator import aggregate_metrics, evaluate_all
from src.extractor import extract_file
from src.report import generate_accuracy_csv, generate_evaluation_report, generate_what_moved_the_needle
from src.verifier import verify_extraction

# These are the prompt versions shown in the assessment comparison.
PROMPT_VERSIONS = ["v1", "v2", "v3", "v4", "v5"]


def write_json(path: Path, payload: dict) -> None:
    """Persist a Python dictionary as readable JSON for the presentation."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def run_extraction(prompt_version: str) -> list[Path]:
    """Run the production extractor for every local invoice.

    v5 receives one additional verification pass because that is the prompt
    version designed to remove unsupported values before writing the result.
    """
    output_paths = []
    # Sorting makes the demo output deterministic and easy to follow live.
    invoice_paths = sorted(INVOICES_DIR.glob("*.txt"))
    if not invoice_paths:
        raise FileNotFoundError(f"No invoice files found in {INVOICES_DIR}")

    print(f"\n[1] Extracting {len(invoice_paths)} invoice(s) with {prompt_version}")
    for invoice_path in invoice_paths:
        # extract_file loads the selected prompt, calls the LLM adapter, and
        # validates the returned JSON through the Pydantic schema.
        result = extract_file(invoice_path, prompt_version=prompt_version)
        if prompt_version == "v5":
            # The v5 verifier checks the source text before final persistence.
            invoice_text = invoice_path.read_text(encoding="utf-8")
            result = verify_extraction(invoice_text, result, prompt_version=prompt_version)

        # Each output keeps the invoice name and prompt version for traceability.
        output_path = OUTPUTS_DIR / f"{invoice_path.stem}_{prompt_version}_output.json"
        write_json(output_path, result)
        output_paths.append(output_path)
        print(f"    {invoice_path.name} -> {output_path.relative_to(BASE_DIR)}")
    return output_paths


def run_evaluation(prompt_version: str) -> dict:
    """Compare generated outputs with ground truth and save measured metrics."""
    print(f"\n[2] Evaluating {prompt_version} against ground truth")
    # evaluate_all performs field-level comparisons for every matching invoice.
    invoice_metrics = evaluate_all(prompt_version)
    # Aggregation creates the summary values used in the presentation reports.
    metrics = aggregate_metrics(invoice_metrics)
    result_path = RESULTS_DIR / f"{prompt_version}_results.json"
    write_json(result_path, {"metrics": metrics, "invoice_metrics": invoice_metrics})
    print(f"    precision={metrics['precision']:.3f}")
    print(f"    recall={metrics['recall']:.3f}")
    print(f"    f1={metrics['f1']:.3f}")
    print(f"    accuracy={metrics['accuracy']:.3f}")
    print(f"    hallucinations={metrics['hallucinations']}")
    print(f"    saved={result_path.relative_to(BASE_DIR)}")
    return metrics


def main() -> None:
    """Run the complete demo in the order used during the presentation."""
    print("Invoice / Receipt Field Extractor Demo")
    # Display the dataset scope before processing so the audience knows what
    # is being measured and can reproduce the run.
    print(f"Workspace: {BASE_DIR}")
    print(f"Invoices: {len(list(INVOICES_DIR.glob('*.txt')))}")
    print(f"Ground truth files: {len(list(GROUND_TRUTH_DIR.glob('*.json')))}")

    # Demonstrate the final prompt first, then compare all prompt versions.
    # This gives the audience one concrete end-to-end result before showing
    # how prompt changes affect the measured metrics.
    run_extraction("v5")
    run_evaluation("v5")

    print("\n[3] Comparing all prompt versions")
    for prompt_version in PROMPT_VERSIONS:
        # v5 was already generated above; the other versions need outputs now.
        if prompt_version != "v5":
            run_extraction(prompt_version)
        run_evaluation(prompt_version)

    print("\n[4] Generating reports")
    # These functions read the result JSON files and create presentation-ready
    # CSV and Markdown artifacts from measured values.
    report_paths = [
        generate_accuracy_csv(),
        generate_evaluation_report(),
        generate_what_moved_the_needle(),
    ]
    for path in report_paths:
        print(f"    {path.relative_to(BASE_DIR)}")

    print("\nDemo complete. Open results/evaluation_report.md to present the summary.")
    print("Open data/outputs/ to present the per-invoice JSON extraction.")


if __name__ == "__main__":
    main()
