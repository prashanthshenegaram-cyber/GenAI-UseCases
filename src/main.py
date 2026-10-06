"""Command-line entry point, interactive loop, and demo trace generation.

The CLI owns user input/output only. It delegates decisions to the agent and
stores completed example traces as JSON beneath the project ``traces`` folder.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.agent import StoreAssistantAgent
from src.models import AgentState

ROOT = Path(__file__).resolve().parents[1]
TRACE_DIR = ROOT / "traces"
# Keep the demo requests in one list so they can be rerun consistently.
SCENARIOS = [
    ("run_01.json", "I want 3 cotton t-shirts, deliver to 700001. Total?"),
    ("run_02.json", "I want 2 casual shirts and 1 pair of sneakers, deliver to 500001."),
    ("run_03.json", "Add 2 denim jeans."),
    ("run_04.json", "I want 2 sneakers and 1 cotton t-shirt. What is my total?"),
    ("run_05.json", "I want 1 mystery widget, deliver to PIN 999999."),
]


def save_trace(trace: dict[str, object], path: Path) -> None:
    """Create the parent folder and write one trace as readable UTF-8 JSON.

    Args:
        trace: Safe execution record returned by ``StoreAssistantAgent``.
        path: Destination JSON file, normally inside ``traces/``.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(trace, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def run_scenarios() -> None:
    """Execute all demo requests and write one trace per scenario.

    Each run starts from a clean state except the out-of-stock follow-up, which
    first adds three shirts so the trace demonstrates order persistence.
    """
    agent = StoreAssistantAgent()
    for filename, request in SCENARIOS:
        state = AgentState()
        if filename == "run_03.json":
            state = agent.process("I want 3 cotton t-shirts, deliver to 700001.", state).state
        run = agent.process(request, state)
        state = run.state
        save_trace(run.trace, TRACE_DIR / filename)
        print(f"{filename}: {run.response}")


def main() -> None:
    """Parse CLI options, then run a single request, demos, or a chat session."""
    parser = argparse.ArgumentParser(description="Run the deterministic Store Assistant Agent.")
    parser.add_argument("--request", help="Process one shopping request and exit.")
    parser.add_argument("--scenarios", action="store_true", help="Run and save the five example traces.")
    args = parser.parse_args()
    if args.scenarios:
        run_scenarios()
        return

    agent = StoreAssistantAgent()
    state = AgentState()
    if args.request:
        # Single-request mode is useful for scripts and quick manual checks.
        run = agent.process(args.request, state)
        print(run.response)
        return
    print("Store Assistant Agent (type 'quit' to exit)")
    # Reuse one state object so additions in one turn remain in later turns.
    while True:
        try:
            request = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if request.lower() in {"quit", "exit"}:
            break
        if request:
            run = agent.process(request, state)
            state = run.state
            print(f"Agent: {run.response}")


if __name__ == "__main__":
    main()