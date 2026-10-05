"""Configuration for the release-quality evaluation gate."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


DEFAULT_THRESHOLDS = {
    "faithfulness": 0.80,
    "answer_relevance": 0.80,
    "context_precision": 0.75,
    "context_recall": 0.75,
    "hit_rate": 0.80,
    "correct_refusal_rate": 0.90,
}


@dataclass(frozen=True)
class EvaluationConfig:
    root: Path
    dataset_path: Path
    results_dir: Path
    vector_dir: Path
    thresholds: dict[str, float] = field(default_factory=lambda: DEFAULT_THRESHOLDS.copy())
    use_ragas: bool = False
    judge_enabled: bool = True
    judge_model: str = "gpt-4o-mini"

    @classmethod
    def from_env(cls, root: Path | None = None) -> "EvaluationConfig":
        project_root = (root or Path(__file__).resolve().parents[1]).resolve()
        load_dotenv(project_root / ".env")
        thresholds = DEFAULT_THRESHOLDS.copy()
        for metric in thresholds:
            environment_name = f"RAG_GATE_{metric.upper()}_THRESHOLD"
            if value := os.getenv(environment_name):
                thresholds[metric] = float(value)
        return cls(
            root=project_root,
            dataset_path=project_root / "data" / "golden_dataset.json",
            results_dir=project_root / "results",
            vector_dir=project_root / "data" / "vector_store" / "quality_gate",
            thresholds=thresholds,
            use_ragas=os.getenv("RAG_GATE_USE_RAGAS", "false").lower() in {"1", "true", "yes"},
            judge_enabled=os.getenv("RAG_GATE_JUDGE_ENABLED", "true").lower() in {"1", "true", "yes"},
            judge_model=os.getenv("RAG_GATE_JUDGE_MODEL", "gpt-4o-mini"),
        )