"""Price validated order lines using inventory and editable discount rules.

The agent passes only stock-approved lines to ``price_order``. This module
re-reads prices from the catalog and applies the greatest eligible discount in
``data/discounts.json``, returning integer whole-rupee amounts.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models import ToolContract
from src.tools.inventory import DATA_DIR, load_inventory

PRICE_ORDER_CONTRACT = ToolContract(
    name="price_order",
    description="Price committed order items and apply the highest eligible configured discount.",
    input_schema={
        "type": "object",
        "required": ["items"],
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["product_id", "quantity"],
                    "properties": {"product_id": {"type": "string"}, "quantity": {"type": "integer", "minimum": 1}},
                },
            }
        },
    },
    output_schema={
        "type": "object",
        "required": ["items", "subtotal", "discount_percent", "discount_amount", "final_total"],
    },
)


def price_order(
    items: list[dict[str, Any]],
    inventory_path: Path | None = None,
    discounts_path: Path | None = None,
) -> dict[str, Any]:
    """Calculate line totals, subtotal, discount, and final payable amount.

    Args:
        items: Dictionaries containing ``product_id`` and positive ``quantity``.
        inventory_path: Optional inventory JSON override for isolated tests.
        discounts_path: Optional discount-rule JSON override for isolated tests.

    Returns:
        A structured result containing item lines and totals, or an ``error``
        message when inputs or configuration are invalid.
    """
    if not isinstance(items, list) or not items:
        return {"error": "At least one order item is required."}
    try:
        products = load_inventory(inventory_path)
        discount_file = discounts_path or DATA_DIR / "discounts.json"
        with discount_file.open(encoding="utf-8") as rules_file:
            rules_payload = json.load(rules_file)
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as error:
        return {"error": f"Pricing data could not be loaded: {error}"}

    # Build line-level totals while accumulating the pre-discount subtotal.
    lines: list[dict[str, Any]] = []
    subtotal = 0
    for item in items:
        if not isinstance(item, dict):
            return {"error": "Each order item must be an object."}
        product_id = item.get("product_id")
        quantity = item.get("quantity")
        if not isinstance(product_id, str) or not product_id:
            return {"error": "Each order item needs a product_id."}
        if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
            return {"error": f"Quantity for '{product_id}' must be a positive integer."}
        product = products.get(product_id)
        if product is None:
            return {"error": f"Product '{product_id}' was not found."}
        unit_price = product.get("unit_price")
        if isinstance(unit_price, bool) or not isinstance(unit_price, int) or unit_price < 0:
            return {"error": f"Product '{product_id}' has an invalid unit price."}
        line_total = unit_price * quantity
        subtotal += line_total
        lines.append({
            "product_id": product_id,
            "product_name": product["product_name"],
            "quantity": quantity,
            "unit_price": unit_price,
            "line_total": line_total,
        })

    rules = rules_payload.get("rules", [])
    if not isinstance(rules, list):
        return {"error": "Discount data must contain a rules list."}
    # Keep eligible thresholds, then choose the rule with the highest threshold.
    eligible: list[tuple[int, int]] = []
    for rule in rules:
        if not isinstance(rule, dict):
            return {"error": "Each discount rule must be an object."}
        minimum = rule.get("minimum_subtotal")
        percent = rule.get("percent")
        if (
            isinstance(minimum, bool) or not isinstance(minimum, int) or minimum < 0
            or isinstance(percent, bool) or not isinstance(percent, int) or not 0 <= percent <= 100
        ):
            return {"error": "Discount rules contain an invalid threshold or percentage."}
        if subtotal >= minimum:
            eligible.append((minimum, percent))
    discount_percent = max(eligible, default=(0, 0))[1]
    # Round the percentage discount to the nearest whole rupee.
    discount_amount = (subtotal * discount_percent + 50) // 100
    return {
        "items": lines,
        "subtotal": subtotal,
        "discount_percent": discount_percent,
        "discount_amount": discount_amount,
        "final_total": subtotal - discount_amount,
        "currency": rules_payload.get("currency", "INR"),
    }
