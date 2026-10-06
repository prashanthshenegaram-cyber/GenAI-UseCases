"""Data structures shared by tools, the agent controller, and the CLI.

These dataclasses define the shape of tool descriptions, order lines, persistent
conversation state, and the result returned after one agent turn.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class ToolContract:
    """Machine-readable name, purpose, and schemas for one callable tool.

    The schemas document the expected input and output fields so callers and
    reviewers can understand the function-calling boundary.
    """

    name: str
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]


@dataclass
class OrderItem:
    """One product line that passed inventory validation and joined the order."""

    product_id: str
    product_name: str
    quantity: int
    unit_price: int

    def to_dict(self) -> dict[str, Any]:
        """Convert this line to a dictionary suitable for a trace or JSON output."""
        return asdict(self)


@dataclass
class AgentState:
    """Mutable conversation and shopping data shared between agent turns.

    Only checked, available items belong in ``order_items``. Totals and delivery
    information are the latest accepted tool results; histories and tool results
    make the execution inspectable.
    """

    conversation_history: list[dict[str, str]] = field(default_factory=list)
    order_items: list[OrderItem] = field(default_factory=list)
    checked_inventory: list[dict[str, Any]] = field(default_factory=list)
    subtotal: int = 0
    discount: int = 0
    final_total: int = 0
    destination_pin: str | None = None
    delivery_eta: dict[str, Any] | None = None
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    completed: bool = False
    stop_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready snapshot without exposing dataclass instances."""
        return {
            "conversation_history": list(self.conversation_history),
            "order_items": [item.to_dict() for item in self.order_items],
            "checked_inventory": list(self.checked_inventory),
            "subtotal": self.subtotal,
            "discount": self.discount,
            "final_total": self.final_total,
            "destination_pin": self.destination_pin,
            "delivery_eta": self.delivery_eta,
            "tool_results": list(self.tool_results),
            "errors": list(self.errors),
            "completed": self.completed,
            "stop_reason": self.stop_reason,
        }


@dataclass
class AgentRun:
    """Bundle the user-facing answer, updated persistent state, and safe trace."""

    response: str
    state: AgentState
    trace: dict[str, Any]
