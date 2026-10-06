"""Estimate delivery time using editable destination-PIN shipping rules.

Known six-digit PINs use their configured estimate in ``data/shipping.json``;
unknown and malformed PINs receive the configured default estimate.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from src.models import ToolContract
from src.tools.inventory import DATA_DIR

DELIVERY_ETA_CONTRACT = ToolContract(
    name="delivery_eta",
    description="Estimate delivery days for an Indian six-digit PIN code, using the configured default when unknown.",
    input_schema={
        "type": "object",
        "required": ["destination_pin"],
        "properties": {"destination_pin": {"type": "string", "pattern": "^[0-9]{6}$"}},
    },
    output_schema={
        "type": "object",
        "required": ["destination_pin", "estimated_delivery_days", "eta", "used_default"],
    },
)


def delivery_eta(destination_pin: str, shipping_path: Path | None = None) -> dict[str, Any]:
    """Return an ETA result for a supplied PIN, using the fallback when needed.

    Args:
        destination_pin: Destination PIN as entered by the user.
        shipping_path: Optional alternate shipping JSON file for tests.

    Returns:
        Destination, estimated days, readable ETA, PIN validity, and whether
        the default rule was used; data errors are returned under ``error``.
    """
    try:
        data_path = shipping_path or DATA_DIR / "shipping.json"
        with data_path.open(encoding="utf-8") as shipping_file:
            rules = json.load(shipping_file)
    except (OSError, json.JSONDecodeError) as error:
        return {"error": f"Shipping data could not be loaded: {error}"}

    # Normalize whitespace, but preserve malformed input for a useful response.
    if isinstance(destination_pin, str):
        normalized_pin = destination_pin.strip()
    else:
        normalized_pin = str(destination_pin)
    valid_pin = bool(re.fullmatch(r"\d{6}", normalized_pin))
    pin_days = rules.get("pin_delivery_days", {})
    default_days = rules.get("default_delivery_days")
    if not isinstance(default_days, int) or isinstance(default_days, bool) or default_days <= 0:
        return {"error": "Shipping data has an invalid default delivery estimate."}
    # Only a valid six-digit PIN can select a specific configured route.
    days = pin_days.get(normalized_pin, default_days) if valid_pin and isinstance(pin_days, dict) else default_days
    if not isinstance(days, int) or isinstance(days, bool) or days <= 0:
        return {"error": "Shipping data has an invalid delivery estimate."}
    qualifier = "approximately "
    validity_note = "" if valid_pin else " (invalid PIN; default estimate used)"
    return {
        "destination_pin": normalized_pin,
        "estimated_delivery_days": days,
        "eta": f"{qualifier}{days} days{validity_note}",
        "valid_pin": valid_pin,
        "used_default": (not valid_pin) or normalized_pin not in pin_days,
    }
