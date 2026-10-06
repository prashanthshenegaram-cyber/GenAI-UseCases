"""Headless integration tests for the Streamlit interface."""

from pathlib import Path

from streamlit.testing.v1 import AppTest


APP_PATH = Path(__file__).resolve().parents[1] / "app.py"


def test_chat_ui_processes_order_and_renders_trace() -> None:
    app = AppTest.from_file(str(APP_PATH)).run()
    assert not app.exception
    assert app.chat_input

    app.chat_input[0].set_value("I want 3 cotton t-shirts, deliver to 700001. Total?").run()

    assert not app.exception
    assert app.session_state["agent_state"].final_total == 1497
    assert len(app.session_state["ui_messages"]) == 2
    rendered_text = " ".join(element.value for element in app.markdown)
    assert "₹1,497" in rendered_text