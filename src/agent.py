"""Route natural-language shopping requests through deterministic business tools.

``StoreAssistantAgent`` implements a small ReAct-style cycle: parse the request,
choose a tool, observe and validate its result, update persistent state, then
continue until the request can be answered. Its trace records actions and
observations only; it does not produce or store private chain-of-thought.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Callable

from src.models import AgentRun, AgentState, OrderItem, ToolContract
from src.tools.inventory import CHECK_STOCK_CONTRACT, check_stock, load_inventory
from src.tools.pricing import PRICE_ORDER_CONTRACT, price_order
from src.tools.shipping import DELIVERY_ETA_CONTRACT, delivery_eta

ToolFunction = Callable[..., dict[str, Any]]
# Tool overrides let tests simulate failures without changing production tools.


class StoreAssistantAgent:
    """Parse simple requests and coordinate inventory, pricing, and shipping.

    Product names and aliases come from the inventory data. The registered tool
    functions may be replaced individually, which is useful for testing tool
    exceptions and malformed responses.
    """

    def __init__(
        self,
        inventory_path: Path | None = None,
        tool_overrides: dict[str, ToolFunction] | None = None,
    ) -> None:
        """Load product aliases and register tool functions and their contracts.

        Args:
            inventory_path: Optional inventory JSON path used by parsing and tools.
            tool_overrides: Optional mapping from tool name to replacement function.
        """
        self.inventory_path = inventory_path
        self.products = load_inventory(inventory_path)
        self.tools: dict[str, ToolFunction] = {
            "check_stock": tool_overrides.get("check_stock", check_stock) if tool_overrides else check_stock,
            "price_order": tool_overrides.get("price_order", price_order) if tool_overrides else price_order,
            "delivery_eta": tool_overrides.get("delivery_eta", delivery_eta) if tool_overrides else delivery_eta,
        }
        self.contracts: dict[str, ToolContract] = {
            contract.name: contract
            for contract in (CHECK_STOCK_CONTRACT, PRICE_ORDER_CONTRACT, DELIVERY_ETA_CONTRACT)
        }

    def process(self, request: str, state: AgentState | None = None) -> AgentRun:
        """Handle one request and return its response, updated state, and trace.

        Each requested line must pass ``check_stock`` before it is committed.
        The committed order is priced once after all stock checks; delivery is
        estimated only when a PIN is available. Errors are retained in the
        response, and the turn always ends with an explicit completed state.

        Args:
            request: One natural-language shopping request from the user.
            state: Existing conversation state, or ``None`` for a new order.
        """
        # Snapshot the old order so the trace can explain what this turn changed.
        current = state or AgentState()
        prior_order = {
            "items": [item.to_dict() for item in current.order_items],
            "subtotal": current.subtotal,
            "discount": current.discount,
            "final_total": current.final_total,
            "destination_pin": current.destination_pin,
        }
        # Reset per-turn completion/error flags while keeping accumulated order data.
        current.completed = False
        current.stop_reason = None
        current.errors = []
        current.conversation_history.append({"role": "user", "content": request})
        trace: dict[str, Any] = {
            "request": request,
            "prior_order_state": prior_order,
            "steps": [],
            "final_response": "",
            "stop_reason": "",
        }
        step_number = 0

        # Extract order candidates and any destination before choosing tool calls.
        parsed_items = self._parse_items(request)
        pin_match = re.search(r"\b(\d{6})\b", request)
        invalid_pin_match = re.search(r"\bPIN\s*(?:code)?\s*[:#-]?\s*(\S+)", request, re.IGNORECASE)
        if pin_match:
            current.destination_pin = pin_match.group(1)
        elif invalid_pin_match and any(char.isdigit() for char in invalid_pin_match.group(1)):
            current.destination_pin = invalid_pin_match.group(1).strip(".,!?;:")

        shopping_intent = bool(re.search(r"\b(want|add|buy|order|purchase|get)\b", request, re.IGNORECASE))
        if shopping_intent and not parsed_items:
            current.errors.append("I couldn't identify a product in that request. Please use a product name or ID.")

        # Stock checks gate all additions; unavailable lines never enter the order.
        for product_id, quantity in parsed_items:
            existing = next((line for line in current.order_items if line.product_id == product_id), None)
            checked_quantity = quantity + (existing.quantity if existing else 0)
            tool_input = {"product_id": product_id, "quantity": checked_quantity}
            result = self._invoke("check_stock", tool_input)
            current.tool_results.append({"tool": "check_stock", "input": tool_input, "output": result})
            step_number += 1
            valid_result = self._valid_stock_result(result, product_id, checked_quantity)
            state_update = ""
            if valid_result is None:
                error = result.get("error", "Stock tool returned a malformed response.") if isinstance(result, dict) else "Stock tool returned a malformed response."
                current.errors.append(str(error))
                current.checked_inventory.append({"product_id": product_id, "error": str(error)})
                next_action = "continue_to_next_item"
            else:
                current.checked_inventory.append(valid_result)
                if valid_result["in_stock"]:
                    if existing:
                        existing.quantity += quantity
                    else:
                        current.order_items.append(
                            OrderItem(product_id, valid_result["product_name"], quantity, valid_result["unit_price"])
                        )
                    state_update = f"Committed {quantity} additional unit(s) of {valid_result['product_name']}."
                else:
                    message = (
                        f"{valid_result['product_name']} are out of stock."
                        if valid_result["available_quantity"] == 0
                        else f"Only {valid_result['available_quantity']} {valid_result['product_name']} available; "
                        f"could not add {checked_quantity}."
                    )
                    current.errors.append(message)
                    state_update = "Order items unchanged because requested stock is unavailable."
                next_action = "check_next_item" if step_number < len(parsed_items) else "recalculate_committed_order"
            trace["steps"].append(self._trace_step(
                step_number, "check_stock", tool_input, result, state_update, next_action
            ))

        # Price only the committed order, including any previous successful turns.
        if current.order_items:
            price_input = {"items": [{"product_id": item.product_id, "quantity": item.quantity} for item in current.order_items]}
            result = self._invoke("price_order", price_input)
            current.tool_results.append({"tool": "price_order", "input": price_input, "output": result})
            step_number += 1
            if self._valid_price_result(result):
                current.subtotal = result["subtotal"]
                current.discount = result["discount_amount"]
                current.final_total = result["final_total"]
                state_update = "Updated subtotal, discount, and total from committed order items."
            else:
                error = result.get("error", "Pricing tool returned a malformed response.") if isinstance(result, dict) else "Pricing tool returned a malformed response."
                current.errors.append(str(error))
                state_update = "Pricing state retained because the tool result was invalid."
            next_action = "estimate_delivery" if current.destination_pin else "finalize_response"
            trace["steps"].append(self._trace_step(
                step_number, "price_order", price_input, result, state_update, next_action
            ))

        # Delivery is an independent optional action and can run without a new item.
        if current.destination_pin:
            tool_input = {"destination_pin": current.destination_pin}
            result = self._invoke("delivery_eta", tool_input)
            current.tool_results.append({"tool": "delivery_eta", "input": tool_input, "output": result})
            step_number += 1
            if self._valid_eta_result(result):
                current.delivery_eta = result
                state_update = f"Saved delivery estimate of {result['estimated_delivery_days']} day(s)."
            else:
                error = result.get("error", "Delivery tool returned a malformed response.") if isinstance(result, dict) else "Delivery tool returned a malformed response."
                current.errors.append(str(error))
                state_update = "Previous delivery estimate retained because the tool result was invalid."
            trace["steps"].append(self._trace_step(
                step_number, "delivery_eta", tool_input, result, state_update, "finalize_response"
            ))

        # Save the user-visible answer and close this turn with a clear stop marker.
        response = self._format_response(current, parsed_items, include_delivery=bool(pin_match or invalid_pin_match))
        current.conversation_history.append({"role": "assistant", "content": response})
        current.completed = True
        current.stop_reason = "request_answered"
        trace["final_response"] = response
        trace["stop_reason"] = current.stop_reason
        trace["steps"].append({
            "step": step_number + 1,
            "selected_tool": None,
            "tool_input": None,
            "tool_output": None,
            "state_update": "Marked this user turn complete.",
            "next_action": "stop",
        })
        return AgentRun(response=response, state=current, trace=trace)

    def _parse_items(self, request: str) -> list[tuple[str, int]]:
        """Find catalog product names/aliases and quantities mentioned nearby.

        Longer aliases are matched first so a full name wins over a shorter
        overlapping alias. The result preserves request order and includes each
        product only once; omitted quantities default to one.
        """
        normalized = request.lower()
        aliases: list[tuple[int, str, str]] = []
        for product_id, product in self.products.items():
            product_aliases = [product["product_name"], product_id, *product.get("aliases", [])]
            for alias in product_aliases:
                aliases.append((len(alias), product_id, alias))
        # Track matched text ranges so one phrase is not mistaken for two products.
        matches: list[tuple[int, int, str, int]] = []
        occupied: list[tuple[int, int]] = []
        for _, product_id, alias in sorted(aliases, reverse=True):
            pattern = rf"(?<![a-z0-9]){re.escape(alias.lower())}(?![a-z0-9])"
            for found in re.finditer(pattern, normalized):
                if any(found.start() < end and found.end() > start for start, end in occupied):
                    continue
                occupied.append((found.start(), found.end()))
                prefix = normalized[max(0, found.start() - 24):found.start()]
                quantity_match = re.search(r"(\d+)\s*(?:x|units?|pieces?)?\s*$", prefix)
                quantity = int(quantity_match.group(1)) if quantity_match else 1
                matches.append((found.start(), found.end(), product_id, quantity))
        matches.sort()
        requested: list[tuple[str, int]] = []
        seen: set[str] = set()
        for _, _, product_id, quantity in matches:
            if product_id not in seen:
                requested.append((product_id, quantity))
                seen.add(product_id)
        return requested

    def _invoke(self, tool_name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a named tool with its arguments and capture raised exceptions.

        Inventory and pricing receive the configured inventory path; shipping
        uses its default dataset. Exceptions are converted to error dictionaries
        so the remaining agent flow can respond safely.
        """
        try:
            function = self.tools[tool_name]
            if tool_name == "check_stock":
                return function(**tool_input, inventory_path=self.inventory_path)
            if tool_name == "price_order":
                return function(**tool_input, inventory_path=self.inventory_path)
            return function(**tool_input)
        except Exception as error:  # Tool boundaries must not crash the conversation.
            return {"error": f"{tool_name} failed: {error}"}

    @staticmethod
    def _valid_stock_result(result: Any, product_id: str, quantity: int) -> dict[str, Any] | None:
        """Check required stock fields and confirm the result matches the request.

        Returning ``None`` marks the observation as malformed and prevents the
        agent from adding the associated product to the order.
        """
        if not isinstance(result, dict):
            return None
        required = ("product_id", "product_name", "requested_quantity", "available_quantity", "in_stock", "unit_price")
        if any(key not in result for key in required):
            return None
        if (
            result["product_id"] != product_id
            or result["requested_quantity"] != quantity
            or not isinstance(result["product_name"], str)
            or isinstance(result["available_quantity"], bool)
            or not isinstance(result["available_quantity"], int)
            or isinstance(result["unit_price"], bool)
            or not isinstance(result["unit_price"], int)
            or not isinstance(result["in_stock"], bool)
        ):
            return None
        return result

    @staticmethod
    def _valid_price_result(result: Any) -> bool:
        """Accept only non-negative integer monetary totals from the price tool."""
        return isinstance(result, dict) and all(
            isinstance(result.get(key), int) and not isinstance(result.get(key), bool)
            for key in ("subtotal", "discount_amount", "final_total")
        ) and result["subtotal"] >= 0 and result["discount_amount"] >= 0 and result["final_total"] >= 0

    @staticmethod
    def _valid_eta_result(result: Any) -> bool:
        """Require a numeric day estimate and readable ETA before saving shipping."""
        return isinstance(result, dict) and isinstance(result.get("estimated_delivery_days"), int) and isinstance(result.get("eta"), str)

    @staticmethod
    def _trace_step(
        step: int,
        tool_name: str,
        tool_input: dict[str, Any],
        tool_output: Any,
        state_update: str,
        next_action: str,
    ) -> dict[str, Any]:
        """Create one safe trace record describing an action and its observation."""
        return {
            "step": step,
            "selected_tool": tool_name,
            "tool_input": tool_input,
            "tool_output": tool_output,
            "state_update": state_update,
            "next_action": next_action,
        }

    @staticmethod
    def _format_response(
        state: AgentState,
        parsed_items: list[tuple[str, int]],
        include_delivery: bool,
    ) -> str:
        """Combine errors, current order totals, and this turn's requested ETA.

        An old delivery estimate remains in state but is not repeated unless the
        current user turn supplied a PIN.
        """
        parts: list[str] = []
        if state.errors:
            parts.extend(state.errors)
        if state.order_items:
            if parsed_items and not state.errors:
                lines = [
                    f"{item.quantity} {item.product_name if item.quantity == 1 or item.product_name.lower().endswith('s') else item.product_name + 's'} = ₹{item.quantity * item.unit_price:,}"
                    for item in state.order_items
                ]
                order_summary = ", ".join(lines)
                if state.discount:
                    order_summary += f". Subtotal ₹{state.subtotal:,}, discount ₹{state.discount:,}"
                parts.append(f"{order_summary}. Total = ₹{state.final_total:,}.")
            elif state.errors:
                parts.append(f"Your order remains at ₹{state.final_total:,}.")
            else:
                parts.append(f"Your current order total is ₹{state.final_total:,}.")
        elif not state.errors:
            parts.append("Tell me which product and quantity you would like to order.")
        if include_delivery and state.delivery_eta:
            parts.append(
                f"Delivery to {state.delivery_eta['destination_pin']} in {state.delivery_eta['eta']}."
            )
        return " ".join(parts)
