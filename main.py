import argparse
import logging
from pathlib import Path
from app.config import Settings
from app.evaluation import evaluate, excel_benchmark
from app.pipeline import RAGPipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Classic RAG - chat with PDF and Excel documents")
    parser.add_argument("command", choices=["ingest", "query", "evaluate", "excel-benchmark", "report"])
    parser.add_argument("--input", type=Path)
    parser.add_argument("--question")
    parser.add_argument("--chunking-strategy", choices=["fixed", "recursive", "section-aware"])
    parser.add_argument("--serialization", choices=["row_text", "markdown_table", "column_wise"])
    parser.add_argument("--top-k", type=int)
    parser.add_argument("--similarity-threshold", type=float)
    parser.add_argument("--embedding-model")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--top-p", type=float)
    parser.add_argument("--top-k-generation", type=int)
    parser.add_argument("--max-output-tokens", type=int)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    overrides = {key: value for key, value in {"chunking_strategy": args.chunking_strategy, "serialization": args.serialization, "top_k": args.top_k, "similarity_threshold": args.similarity_threshold, "embedding_model": args.embedding_model, "temperature": args.temperature, "top_p": args.top_p, "top_k_generation": args.top_k_generation, "max_output_tokens": args.max_output_tokens}.items() if value is not None}
    settings = Settings.from_env(**overrides)
    if args.command == "ingest":
        print(f"Ingested {RAGPipeline(settings).ingest(args.input)} chunks")
    elif args.command == "query":
        if not args.question:
            raise SystemExit("--question is required for query")
        answer = RAGPipeline(settings).query(args.question)
        print(f"[{answer.mode} mode] {answer.text}\nCitations: {'; '.join(answer.citations) or 'none'}")
    elif args.command == "evaluate":
        report = evaluate(settings)
        print(f"Evaluated {report['total_questions']} questions; accuracy={report['overall_accuracy']:.1%}")
    elif args.command == "excel-benchmark":
        print(excel_benchmark(settings))
    else:
        report_path = settings.results_dir / "evaluation_report.md"
        print(report_path.read_text(encoding="utf-8") if report_path.exists() else "No report exists; run evaluate first.")


if __name__ == "__main__":
    main()
