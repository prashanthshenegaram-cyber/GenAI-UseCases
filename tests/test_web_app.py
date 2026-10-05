from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_quality_gate_scorecard_renders_in_streamlit():
    project_root = Path(__file__).resolve().parents[1]
    app = AppTest.from_file(str(project_root / "web_app.py"), default_timeout=30).run()

    assert not app.exception
    assert "Run Evaluation" in [button.label for button in app.button]
    assert {metric.label for metric in app.metric} >= {
        "Faithfulness",
        "Answer relevance",
        "Context precision",
        "Context recall",
        "Retrieval hit rate",
        "Correct refusal rate",
        "LLM-as-Judge",
    }
    assert "Question scorecard" in [item.value for item in app.subheader]
    assert "Top-5 failures" in [item.value for item in app.subheader]