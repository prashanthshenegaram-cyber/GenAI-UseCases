from __future__ import annotations

from typing import Any, Dict, Optional
from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator
from datetime import datetime


class Confidence(BaseModel):
    model_config = ConfigDict(extra='allow')
    currency: Optional[str] = None


class InvoiceExtraction(BaseModel):
    """Strict extraction schema for invoice and receipt fields."""

    model_config = ConfigDict(extra='forbid', populate_by_name=True)

    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None
    vendor: Optional[str] = None
    bill_to: Optional[str] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    payment_terms: Optional[str] = None
    currency: Optional[str] = None
    confidence: Dict[str, Any] = Field(
        default_factory=lambda: {"currency": "absent"},
        validation_alias=AliasChoices("confidence", "_confidence"),
    )

    @field_validator("invoice_date")
    @classmethod
    def validate_invoice_date(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        try:
            parsed = datetime.strptime(value, "%Y-%m-%d")
            return parsed.strftime("%Y-%m-%d")
        except Exception:
            return value

    @field_validator("currency")
    @classmethod
    def normalize_currency(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return value.strip().upper()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "InvoiceExtraction":
        return cls.model_validate(data)

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump(exclude_none=False)


def validate_extraction(data: Dict[str, Any]) -> InvoiceExtraction:
    return InvoiceExtraction.model_validate(data)


def normalize_model_output(raw: Any) -> Dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    raise ValueError("Expected a JSON object")
