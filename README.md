# Store Assistant Agent

A small, deterministic Python shopping assistant that turns natural-language order requests into explicit inventory, pricing, and delivery tool calls. It demonstrates a ReAct-style control loop without requiring an LLM account or network access. Conversation/order state is passed from turn to turn, and each run can be inspected as JSON.

## Prerequisites

- Python 3.10 or newer
- `pip` for installing application and test dependencies

The agent and its tools use the Python standard library. Streamlit provides the browser UI, and `pytest` runs the test suite.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

The `.env.example` file documents reserved provider settings for a future LLM-backed parser. This implementation does not load a `.env` file, make API calls, or require an API key; local deterministic behavior is always available.

## Run

Start the browser UI:

```powershell
python -m streamlit run app.py
```

Open [http://localhost:8501](http://localhost:8501). The chat, cart, and conversation state remain available in that browser session. Expand **Tool activity** under an assistant response to inspect tool inputs and outputs, or download that turn's JSON trace.

Process a single request:

```powershell
python -m src.main --request "I want 3 cotton t-shirts, deliver to 700001. Total?"
```

Start an interactive conversation (order state persists between turns):

```powershell
python -m src.main
```

Example:

```text
You: I want 3 cotton t-shirts, deliver to 700001. Total?
Agent: 3 Cotton T-Shirts = ₹1,497. Total = ₹1,497. Delivery to 700001 in approximately 3 days.
You: Add 2 denim jeans.
Agent: Denim Jeans are out of stock. Your order remains at ₹1,497.
```

Create or refresh all five sample traces:

```powershell
python -m src.main --scenarios
```

Each scenario starts with a clean order except `run_03`, which intentionally seeds the three-T-shirt order before asking to add unavailable jeans. The trace records that prior order snapshot.

## Tests

```powershell
python -m pytest -q
```

The tests cover tool validation and failure results, discount thresholds, PIN fallback, multi-item orders, state persistence, malformed tool responses, and the end-to-end execution path.

## Tools and behavior

The three registered core tools are `check_stock`, `price_order`, and `delivery_eta`. Their names, descriptions, and JSON-like input/output schemas are defined as Python `ToolContract` values. Tool results are structured dictionaries, and exceptions or malformed tool outputs are handled at the agent boundary.

Inventory is checked before a new line is committed. If a stock check fails, that line is not added and `price_order` is called only for the already committed order (if any). Discounts are selected from the highest eligible threshold in `data/discounts.json`; whole-rupee discount amounts are rounded to the nearest rupee. Unknown or invalid destination PINs use the configurable default in `data/shipping.json`.

## Example tool trace

`traces/run_01.json` contains a complete example. A shortened sequence is:

```text
request: I want 3 cotton t-shirts, deliver to 700001. Total?
check_stock({product_id: TS-01, quantity: 3}) -> available_quantity 12, in_stock true
price_order({items: [{product_id: TS-01, quantity: 3}]}) -> subtotal 1497, final_total 1497
delivery_eta({destination_pin: 700001}) -> estimated_delivery_days 3
next_action: stop
```

Trace steps contain only the request, selected tool, input, output, concise state update, next action, final response, and stop reason. They do not contain hidden reasoning.

## Project structure

```text
data/                 Editable inventory, discount, and shipping rules
src/tools/            The three business tools and contracts
src/models.py         Dataclasses for tool contracts, order lines, and agent state
src/agent.py          Request parsing, action routing, state updates, and stop condition
src/main.py           Interactive CLI and demo trace generation
tests/                Unit and integration tests
traces/               Five representative JSON execution traces
app.py                Streamlit browser chat, cart, catalog, and tool timeline
.streamlit/           Browser UI theme configuration
DESIGN.md             Architecture and learning-goal walkthrough
requirements.txt      Streamlit UI and pytest dependencies
.env.example          Reserved optional LLM settings (not needed in local mode)
```