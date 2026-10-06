"""Tests for PIN-based delivery estimates."""

from src.tools.shipping import delivery_eta


def test_known_pin_eta() -> None:
    result = delivery_eta("700001")
    assert result["estimated_delivery_days"] == 3
    assert result["used_default"] is False


def test_unknown_and_invalid_pin_use_default() -> None:
    assert delivery_eta("999999")["estimated_delivery_days"] == 5
    invalid = delivery_eta("abc")
    assert invalid["estimated_delivery_days"] == 5
    assert invalid["valid_pin"] is False