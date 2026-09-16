import argparse
import json
import logging
import os
import sys
from pathlib import Path

from .config import BASE_DIR, DEFAULT_PROMPT_VERSION, OUTPUTS_DIR, GROUND_TRUTH_DIR
from .extractor import extract_file
from .evaluator import evaluate_all, aggregate_metrics
from .verifier import verify_extraction

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger(__name__)


def extract_command(args):
    invoice_path = Path(args.input)
    result = extract_file(invoice_path, prompt_version=args.prompt_version)
    # run verifier for v5
    invoice_text = invoice_path.read_text(encoding="utf-8")
    if args.prompt_version == "v5":
        result = verify_extraction(invoice_text, result, prompt_version=args.prompt_version)
    out_path = OUTPUTS_DIR / f"{invoice_path.stem}_{args.prompt_version}_output.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Extraction written to {out_path}")


def evaluate_command(args):
    # Evaluate predictions for a given version.
    result = evaluate_all(args.prompt_version)
    # Aggregate metrics for a reportable table.
    agg = aggregate_metrics(result)
    # Write vN_results.json in results folder.
    results_dir = BASE_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path = results_dir / f"{args.prompt_version}_results.json"
    out_path.write_text(json.dumps({"metrics": agg, "invoice_metrics": result}, indent=2), encoding="utf-8")
    print(f"Evaluation written to {out_path}")


def evaluate_all_command(args):
    for version in ["v1", "v2", "v3", "v4", "v5"]:
        result = evaluate_all(version)
        agg = aggregate_metrics(result)
        results_dir = BASE_DIR / "results"
        results_dir.mkdir(parents=True, exist_ok=True)
        out_path = results_dir / f"{version}_results.json"
        out_path.write_text(json.dumps({"metrics": agg, "invoice_metrics": result}, indent=2), encoding="utf-8")
        print(f"Wrote {out_path}")


def report_command(args):
    # Create a simple markdown report based on available results.
    # Keep a version argument for compatibility with the CLI invocation pattern.
    _ = args.prompt_version
    results_dir = BASE_DIR / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Evaluation Report",
        "",
        f"Dataset size: {len(list(GROUND_TRUTH_DIR.glob('*.json')))} invoices",
        "",
        "## Metrics",
        "",
    ]
    for version in ["v1", "v2", "v3", "v4", "v5"]:
        result_path = results_dir / f"{version}_results.json"
        if result_path.exists():
            payload = json.loads(result_path.read_text(encoding="utf-8"))
            metrics = payload.get("metrics", {})
            lines.append(f"- {version}: precision={metrics.get('precision', 0):.3f}, recall={metrics.get('recall', 0):.3f}, f1={metrics.get('f1', 0):.3f}, accuracy={metrics.get('accuracy', 0):.3f}, hallucinations={metrics.get('hallucinations', 0)}, tax_hallucinations={metrics.get('tax_hallucinations', 0)}")
    lines += [
        "",
        "## Notes",
        "",
        "This assessment project separates prompt versions and uses deterministic JSON extraction and evaluation from local files.",
    ]
    report_path = results_dir / "evaluation_report.md"
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report_path}")


def build_parser():
    parser = argparse.ArgumentParser(description="Invoice / Receipt Field Extractor")
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract = subparsers.add_parser("extract", help="Extract fields from an input invoice text file")
    extract.add_argument("--input", required=True)
    extract.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    extract.set_defaults(func=extract_command)

    evaluate = subparsers.add_parser("evaluate", help="Evaluate all predicted outputs for one prompt version")
    evaluate.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    evaluate.set_defaults(func=evaluate_command)

    evaluate_all_parser = subparsers.add_parser("evaluate-all", help="Run the same dataset across all versions")
    evaluate_all_parser.set_defaults(func=evaluate_all_command)

    report = subparsers.add_parser("report", help="Generate the markdown evaluation report")
    report.add_argument("--prompt-version", default=DEFAULT_PROMPT_VERSION)
    report.set_defaults(func=report_command)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logger.error(str(exc))
        raise SystemExit(1)
