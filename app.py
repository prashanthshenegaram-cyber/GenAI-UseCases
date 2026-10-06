"""Browser interface for the Store Assistant Agent."""

from __future__ import annotations

import json
from typing import Any

import streamlit as st

from src.agent import StoreAssistantAgent
from src.models import AgentState

SUGGESTIONS = {
    "3 cotton t-shirts · delivery to 700001": "I want 3 cotton t-shirts, deliver to 700001. Total?",
    "2 casual shirts · delivery to 500001": "I want 2 casual shirts, deliver to 500001.",
    "Add 2 denim jeans": "Add 2 denim jeans.",
}

st.set_page_config(
    page_title="Store Assistant",
    page_icon=":material/storefront:",
    layout="wide",
)


def initialize_session() -> None:
    """Create one agent and one persistent order state for this browser session."""
    if "agent" not in st.session_state:
        st.session_state.agent = StoreAssistantAgent()
    if "agent_state" not in st.session_state:
        st.session_state.agent_state = AgentState()
    if "ui_messages" not in st.session_state:
        st.session_state.ui_messages = []


def submit_request(request: str) -> None:
    """Run a user turn and save the response and safe trace for display."""
    run = st.session_state.agent.process(request, st.session_state.agent_state)
    st.session_state.agent_state = run.state
    st.session_state.ui_messages.append({"role": "user", "content": request})
    st.session_state.ui_messages.append({
        "role": "assistant",
        "content": run.response,
        "trace": run.trace,
    })


def render_trace(trace: dict[str, Any], message_index: int) -> None:
    """Show tool calls and observations without displaying private reasoning."""
    tool_steps = [step for step in trace["steps"] if step["selected_tool"]]
    with st.expander(f"Tool activity · {len(tool_steps)} calls", icon=":material/route:"):
        for step in tool_steps:
            with st.status(
                f"Step {step['step']} · {step['selected_tool']}",
                state="complete",
                expanded=False,
                type="step",
            ):
                st.caption(f"Next action: {step['next_action']}")
                st.caption(step["state_update"] or "No state change.")
                st.json(
                    {"input": step["tool_input"], "output": step["tool_output"]},
                    expanded=False,
                )
        st.caption(f"Stopped: {trace['stop_reason']}")
        st.download_button(
            "Download trace",
            data=json.dumps(trace, indent=2, ensure_ascii=False),
            file_name=f"store-assistant-turn-{message_index}.json",
            mime="application/json",
            icon=":material/download:",
            key=f"trace-download-{message_index}",
        )


def render_sidebar() -> None:
    """Display the current cart and a compact view of the editable catalog."""
    state = st.session_state.agent_state
    with st.sidebar:
        st.title("Your order", anchor=False)
        if st.button("Start new order", icon=":material/add:", width="stretch"):
            st.session_state.agent_state = AgentState()
            st.session_state.ui_messages = []
            st.rerun()

        st.metric("Current total", f"₹{state.final_total:,}")
        if state.order_items:
            for item in state.order_items:
                st.write(f"**{item.quantity} × {item.product_name}**")
                st.caption(f"₹{item.quantity * item.unit_price:,}")
            if state.discount:
                st.caption(f"Discount applied · −₹{state.discount:,}")
        else:
            st.caption("Your cart is empty")

        if state.delivery_eta:
            st.write("Delivery")
            st.caption(
                f"{state.delivery_eta['destination_pin']} · "
                f"{state.delivery_eta['estimated_delivery_days']} days"
            )

        with st.expander("Browse products", icon=":material/inventory_2:"):
            for product in st.session_state.agent.products.values():
                st.write(f"**{product['product_name']}** · ₹{product['unit_price']:,}")
                stock = product["stock"]
                st.caption(f"{stock} in stock" if stock else "Out of stock")


def render_conversation() -> None:
    """Render saved chat turns and their associated execution traces."""
    messages = st.session_state.ui_messages
    if not messages:
        with st.chat_message("assistant", avatar=":material/storefront:"):
            st.write("Welcome. What would you like to order today?")
        selected = st.pills(
            "Suggested requests",
            options=list(SUGGESTIONS),
            label_visibility="collapsed",
            key="suggested_request",
        )
        if selected:
            submit_request(SUGGESTIONS[selected])

    for index, message in enumerate(st.session_state.ui_messages):
        avatar = ":material/storefront:" if message["role"] == "assistant" else None
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            if "trace" in message:
                render_trace(message["trace"], index)


initialize_session()
st.title("Store Assistant", icon=":material/storefront:")
st.caption("Local shopping assistant · ready")
render_sidebar()
render_conversation()

request = st.chat_input("Ask for a product, quantity, or delivery estimate", key="order_request")
if request and request.strip():
    submit_request(request.strip())
    st.rerun()