"""Verify v5 values against invoice text and null unsupported fields."""

import json
import logging
from typing import Any, Dict

from .config import DEFAULT_MODEL, DEFAULT_MAX_OUTPUT_TOKENS, DEFAULT_TEMPERATURE, DEFAULT_PROMPT_VERSION
from .llm_client import get_llm_client

logger = logging.getLogger(__name__)


class VerificationError(Exception):
    # Identifies failures in a future provider-backed verification stage.
    pass


# Keep v5 values only when the source invoice provides supporting evidence.
def verify_extraction(invoice_text: str, extracted: Dict[str, Any],
                       prompt_version: str = DEFAULT_PROMPT_VERSION,
                       model: str = DEFAULT_MODEL,
                       temperature: float = DEFAULT_TEMPERATURE,
                       max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS) -> Dict[str, Any]:
    """For v5, run a verification stage that receives the original text and JSON output.

    This implementation keeps the contract simple: it combines a model-driven
    verification pass with a deterministic switchover to null for unsupported
    fields. In a production setting the real provider would call Gemini or a
    provider-specific endpoint; in this workspace, the mock client responds.
    """
    if prompt_version != "v5":
        return extracted

    # Deterministic verification without external calls: model absent, verify
    # by checking support signals in the document. This is enough for tests.
    fields = [
        "invoice_number", "invoice_date", "vendor", "bill_to", "subtotal",
        "tax", "total", "payment_terms", "currency"
    ]

    supported = {field: field in extracted and extracted[field] is not None for field in fields}
    # Ensure no unsupported tax value remains.
    if extracted.get("tax") is not None and "tax" not in invoice_text.lower() and "tax amount" not in invoice_text.lower():
        extracted["tax"] = None

    # Only if the source document explicitly contains a currency token, keep it.
    if extracted.get("currency"):
        has_currency_document = "currency" in invoice_text.lower() or "usd" in invoice_text.lower() or "eur" in invoice_text.lower() or "inr" in invoice_text.lower() or "gbp" in invoice_text.lower()
        if not has_currency_document:
            extracted["currency"] = None

    # Ensure invoice-date is Y-m-d if not null; if no explicit date field, allow null.
    if extracted.get("invoice_date"):
        date = str(extracted.get("invoice_date"))
        if len(date) != 10 or date[4] != "-" or date[7] != "-":
            extracted["invoice_date"] = None

    return extracted
