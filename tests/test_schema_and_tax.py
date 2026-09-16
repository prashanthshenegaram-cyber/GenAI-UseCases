import json
from pathlib import Path

import pytest

from src.schema import validate_extraction
from src.evaluator import evaluate_prediction


def test_schema_validation_accepts_strict_shape():
    data = {
        "invoice_number": "INV-2024-1",
        "invoice_date": "2024-03-15",
        "vendor": "ACME",
        "bill_to": "Zenith",
        "subtotal": 61.0,
        "tax": 10.98,
        "total": 71.98,
        "payment_terms": "Net 30",
        "currency": "USD",
        "confidence": {"currency": "explicit"},
    }
    model = validate_extraction(data)
    assert model.invoice_number == "INV-2024-1"
    assert model.currency == "USD"


def test_cannot_accept_extra_field_in_schema():
    data = {
        "invoice_number": "INV-1",
        "invoice_date": "2024-03-15",
        "vendor": "ACME",
        "bill_to": "Zenith",
        "subtotal": 61.0,
        "tax": 10.98,
        "total": 71.98,
        "payment_terms": "Net 30",
        "currency": "USD",
        "confidence": {"currency": "explicit"},
        "unexpected": True,
    }
    with pytest.raises(Exception):
        validate_extraction(data)


def test_missing_field_must_be_nullable():
    data = {
        "invoice_number": None,
        "invoice_date": None,
        "vendor": "ACME",
        "bill_to": None,
        "subtotal": 50.0,
        "tax": None,
        "total": 50.0,
        "payment_terms": None,
        "currency": None,
        "confidence": {"currency": "absent"},
    }
    model = validate_extraction(data)
    assert model.tax is None
    assert model.currency is None


def test_date_normalization_accepts_and_stores_date_string():
    data = {
        "invoice_date": "2024-03-15",
    }
    model = validate_extraction({
        "invoice_number": None,
        "invoice_date": "2024-03-15",
        "vendor": "ACME",
        "bill_to": None,
        "subtotal": None,
        "tax": None,
        "total": None,
        "payment_terms": None,
        "currency": None,
        "confidence": {"currency": "absent"},
    })
    assert model.invoice_date == "2024-03-15"


def test_numeric_and_currency_normalization():
    model = validate_extraction({
        "invoice_number": "INV-1",
        "invoice_date": "2024-03-15",
        "vendor": "ACME",
        "bill_to": "Zenith",
        "subtotal": 10.0,
        "tax": None,
        "total": 10.0,
        "payment_terms": None,
        "currency": "usd",
        "confidence": {"currency": "explicit"},
    })
    assert model.currency == "USD"
    assert model.subtotal == 10.0


def test_malformed_llm_output_is_rejected_by_schema_and_parser():
    with pytest.raises(Exception):
        validate_extraction({"invoice_number": 123})


def test_tax_absence_remains_null():
    truth = {
        "invoice_number": "INV-1",
        "invoice_date": "2024-03-15",
        "vendor": "ACME",
        "bill_to": "Zenith",
        "subtotal": 100.0,
        "tax": None,
        "total": 100.0,
        "payment_terms": None,
        "currency": None,
    }
    pred = truth.copy()
    pred["tax"] = None
    metrics = evaluate_prediction(pred, truth)
    assert metrics["tax_hallucination_count"] == 0


def test_hallucination_detection_works_at_field_level():
    truth = {
        "invoice_number": None,
        "invoice_date": None,
        "vendor": None,
        "bill_to": None,
        "subtotal": None,
        "tax": None,
        "total": None,
        "payment_terms": None,
        "currency": None,
    }
    pred = {
        "invoice_number": "INV-1",
        "invoice_date": None,
        "vendor": None,
        "bill_to": None,
        "subtotal": None,
        "tax": None,
        "total": None,
        "payment_terms": None,
        "currency": None,
    }
    metrics = evaluate_prediction(pred, truth)
    assert metrics["hallucinations"] == 1
