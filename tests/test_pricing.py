"""Tests for order pricing and configured discounts."""

from src.tools.pricing import price_order


def test_price_without_discount() -> None:
    result = price_order([{"product_id": "TS-01", "quantity": 3}])
    assert result["subtotal"] == 1497
    assert result["discount_amount"] == 0
    assert result["final_total"] == 1497


def test_discount_thresholds() -> None:
    five_percent = price_order([{"product_id": "SH-02", "quantity": 2}])
    assert five_percent["subtotal"] == 1798
    assert five_percent["discount_amount"] == 90
    assert five_percent["final_total"] == 1708

    ten_percent = price_order([{"product_id": "SN-03", "quantity": 2}])
    assert ten_percent["discount_percent"] == 10
    assert ten_percent["discount_amount"] == 500


def test_multi_item_order_and_validation() -> None:
    result = price_order([
        {"product_id": "TS-01", "quantity": 1},
        {"product_id": "SH-02", "quantity": 1},
    ])
    assert result["subtotal"] == 1398
    assert "error" in price_order([{"product_id": "UNKNOWN", "quantity": 1}])
    assert "error" in price_order([{"product_id": "TS-01", "quantity": 0}])