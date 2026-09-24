import json
from pathlib import Path
from .config import Settings
from .pipeline import RAGPipeline


def _hit(answer: str, expected: str) -> bool:
    return all(part.lower() in answer.lower() for part in expected.split("|"))


def evaluate(settings: Settings, questions_path: Path | None = None) -> dict:
    path = questions_path or settings.root / "data/ground_truth/questions.json"
    questions = json.loads(path.read_text(encoding="utf-8"))
    pipeline = RAGPipeline(settings)
    if not pipeline.store.path.exists():
        pipeline.ingest()
    pipeline.load()
    results = []
    for question in questions:
        answer = pipeline.query(question["question"])
        source_match = any(item.chunk.metadata.get("source") == question.get("source") for item in answer.retrieved)
        success = _hit(answer.text, question["expected"]) and (question.get("source") in {None, "none"} or source_match)
        if question.get("source") == "none":
            success = "couldn't find" in answer.text.lower()
        results.append({**question, "answer": answer.text, "citations": answer.citations, "retrieved": [item.chunk.metadata for item in answer.retrieved], "success": success})
    categories = {}
    for category in {item["category"] for item in results}:
        group = [item for item in results if item["category"] == category]
        categories[category] = sum(item["success"] for item in group) / len(group) if group else 0
    report = {"total_questions": len(results), "overall_accuracy": sum(item["success"] for item in results) / len(results) if results else 0, "accuracy_by_category": categories, "results": results}
    settings.results_dir.mkdir(parents=True, exist_ok=True)
    (settings.results_dir / "evaluation_results.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    (settings.results_dir / "evaluation_report.md").write_text(render_report(report), encoding="utf-8")
    return report


def render_report(report: dict) -> str:
    lines = ["# Classic RAG evaluation", "", f"- Total questions: {report['total_questions']}", f"- Overall accuracy: {report['overall_accuracy']:.1%}", "", "## Accuracy by category", "", "| Category | Accuracy |", "|---|---:|"]
    lines.extend(f"| {key} | {value:.1%} |" for key, value in report["accuracy_by_category"].items())
    image_results = [item for item in report["results"] if item["category"] == "image"]
    refusal_results = [item for item in report["results"] if item.get("source") == "none"]
    lines.extend(["", "## Observed results", "", "The values below were generated from the current local execution. The image/chart category is expected to expose the limitation of text-only PDF extraction; OCR or a vision-capable model is required for reliable image-only facts.", "", "## Chart/image failure analysis", ""])
    lines.extend(f"- {item['id']}: success={item['success']}; answer={item['answer']}" for item in image_results)
    lines.extend(["", "## Grounded refusal results", ""])
    lines.extend(f"- {item['id']}: success={item['success']}; answer={item['answer']}" for item in refusal_results)
    lines.extend(["", "## Retrieval failures", ""])
    lines.extend(f"- {item['id']}: {item['question']}" for item in report["results"] if not item["retrieved"])
    return "\n".join(lines) + "\n"


def excel_benchmark(settings: Settings) -> dict:
    comparison = {}
    for serialization in ("row_text", "markdown_table", "column_wise"):
        trial = Settings(root=settings.root, serialization=serialization, chunking_strategy=settings.chunking_strategy, top_k=settings.top_k, embedding_model=settings.embedding_model, similarity_threshold=settings.similarity_threshold)
        comparison[serialization] = evaluate(trial)["overall_accuracy"]
    result = {"serialization_accuracy": comparison}
    (settings.results_dir / "excel_benchmark.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    report_path = settings.results_dir / "evaluation_report.md"
    with report_path.open("a", encoding="utf-8") as report:
        report.write("\n## Excel serialization comparison\n\n| Representation | Accuracy |\n|---|---:|\n")
        report.writelines(f"| {name} | {accuracy:.1%} |\n" for name, accuracy in comparison.items())
        report.write("\nNo winner is hard-coded; the table reflects this execution.\n")
    return result
