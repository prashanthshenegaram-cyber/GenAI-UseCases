"""Integration coverage for the multi-step agent and persistent state."""

from src.agent import StoreAssistantAgent
from src.models import AgentState


def test_complete_order_workflow() -> None:
    run = StoreAssistantAgent().process("I want 3 cotton t-shirts, deliver to 700001. Total?")
    assert run.state.final_total == 1497
    assert run.state.delivery_eta["estimated_delivery_days"] == 3
    assert [step["selected_tool"] for step in run.trace["steps"]] == [
        "check_stock", "price_order", "delivery_eta", None
    ]
    assert run.state.completed is True


def test_multi_item_order_and_discount() -> None:
    run = StoreAssistantAgent().process("I want 2 sneakers and 1 cotton t-shirt.")
    assert len(run.state.order_items) == 2
    assert run.state.subtotal == 5497
    assert run.state.discount == 550
    assert run.state.final_total == 4947


def test_out_of_stock_does_not_change_persisted_order() -> None:
    agent = StoreAssistantAgent()
    state = agent.process("I want 3 cotton t-shirts.").state
    run = agent.process("Add 2 denim jeans.", state)
    assert [(item.product_id, item.quantity) for item in run.state.order_items] == [("TS-01", 3)]
    assert run.state.final_total == 1497
    assert "out of stock" in run.response
    assert run.trace["steps"][0]["selected_tool"] == "check_stock"


def test_tool_failure_and_malformed_output_are_safe() -> None:
    def fail_stock(**_kwargs: object) -> dict[str, object]:
        raise RuntimeError("inventory service offline")

    failed = StoreAssistantAgent(tool_overrides={"check_stock": fail_stock}).process("Add 1 t-shirt.")
    assert not failed.state.order_items
    assert "offline" in failed.response
    assert all(step["selected_tool"] != "price_order" for step in failed.trace["steps"])

    malformed = StoreAssistantAgent(tool_overrides={"check_stock": lambda **_kwargs: {"unexpected": True}})
    malformed_run = malformed.process("Add 1 t-shirt.")
    assert not malformed_run.state.order_items
    assert "malformed" in malformed_run.response


def test_unknown_product_and_invalid_pin_fallback() -> None:
    run = StoreAssistantAgent().process("I want 1 mystery widget, deliver to PIN 12AB.")
    assert not run.state.order_items
    assert run.state.delivery_eta["estimated_delivery_days"] == 5
    assert "couldn't identify" in run.response


def test_state_persists_between_turns_and_stops() -> None:
    agent = StoreAssistantAgent()
    first = agent.process("Add 1 t-shirt.")
    second = agent.process("Add 1 casual shirt.", first.state)
    assert second.state.completed is True
    assert len(second.state.conversation_history) == 4
    assert second.state.final_total == 1398
    assert second.trace["stop_reason"] == "request_answered"


def test_empty_state_prompt_requests_missing_information() -> None:
    run = StoreAssistantAgent().process("What is the total?")
    assert run.response == "Tell me which product and quantity you would like to order."
