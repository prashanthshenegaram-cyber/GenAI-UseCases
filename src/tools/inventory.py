"""Read product data and answer stock-availability questions.

This module owns the ``check_stock`` tool contract and implementation. Inventory
is editable in ``data/inventory.json``; failures are returned as structured
results so the agent can reject an item without crashing.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.models import ToolContract

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
CHECK_STOCK_CONTRACT = ToolContract(
    name="check_stock",
    description="Check a product's available inventory for a positive requested quantity.",
    input_schema={
        "type": "object",
        "required": ["product_id", "quantity"],
        "properties": {"product_id": {"type": "string"}, "quantity": {"type": "integer", "minimum": 1}},
    },
    output_schema={
        "type": "object",
        "required": ["product_id", "product_name", "requested_quantity", "available_quantity", "in_stock", "unit_price"],
    },
)


def load_inventory(path: Path | None = None) -> dict[str, dict[str, Any]]:
    """Load product records indexed by ID from the default or supplied file.

    Args:
        path: Optional alternate inventory JSON file, useful for tests.

    Raises:
        OSError: The file cannot be opened.
        json.JSONDecodeError: The file is not valid JSON.
        ValueError: The top-level payload does not include a products list.
    """
    data_path = path or DATA_DIR / "inventory.json"
    with data_path.open(encoding="utf-8") as inventory_file:
        payload = json.load(inventory_file)
    products = payload.get("products")
    if not isinstance(products, list):
        raise ValueError("Inventory data must contain a products list.")
    return {product["product_id"]: product for product in products}


def check_stock(product_id: str, quantity: int, inventory_path: Path | None = None) -> dict[str, Any]:
    """Return product details and whether the requested quantity can be fulfilled.

    Invalid identifiers, non-positive quantities, unknown products, and broken
    data are represented by an ``error`` field and ``in_stock=False``. A normal
    availability result contains all fields listed by ``CHECK_STOCK_CONTRACT``.
    """
    if not isinstance(product_id, str) or not product_id.strip():
        return {"product_id": str(product_id), "error": "Product ID is required.", "in_stock": False}
    if isinstance(quantity, bool) or not isinstance(quantity, int) or quantity <= 0:
        return {
            "product_id": product_id,
            "product_name": "Unknown product",
            "requested_quantity": quantity,
            "available_quantity": 0,
            "in_stock": False,
            "unit_price": 0,
            "error": "Quantity must be a positive integer.",
        }

    # Isolate data-loading failures from callers by returning a tool error.
    try:
        product = load_inventory(inventory_path).get(product_id)
    except (OSError, json.JSONDecodeError, ValueError, KeyError) as error:
        return {"product_id": product_id, "error": f"Inventory could not be loaded: {error}", "in_stock": False}

    if product is None:
        return {
            "product_id": product_id,
            "product_name": "Unknown product",
            "requested_quantity": quantity,
            "available_quantity": 0,
            "in_stock": False,
            "unit_price": 0,
            "error": f"Product '{product_id}' was not found.",
        }

    # Validate configuration values before comparing quantities or returning price.
    available = product.get("stock", 0)
    price = product.get("unit_price", 0)
    if isinstance(available, bool) or not isinstance(available, int) or available < 0:
        return {"product_id": product_id, "error": "Product inventory has an invalid stock value.", "in_stock": False}
    if isinstance(price, bool) or not isinstance(price, int) or price < 0:
        return {"product_id": product_id, "error": "Product inventory has an invalid unit price.", "in_stock": False}

    return {
        "product_id": product_id,
        "product_name": product["product_name"],
        "requested_quantity": quantity,
        "available_quantity": available,
        "in_stock": available >= quantity,
        "unit_price": price,
    }
