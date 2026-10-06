"""Tests for the inventory tool contract."""

from src.tools.inventory import check_stock


def test_stock_available() -> None:
    result = check_stock("TS-01", 3)
    assert result["in_stock"] is True
    assert result["available_quantity"] == 12
    assert result["unit_price"] == 499


def test_stock_unavailable_and_zero_stock() -> None:
    result = check_stock("JN-04", 1)
    assert result["in_stock"] is False
    assert result["available_quantity"] == 0


def test_insufficient_stock() -> None:
    result = check_stock("SN-03", 6)
    assert result["in_stock"] is False
    assert result["available_quantity"] == 5


def test_unknown_product_and_invalid_quantity() -> None:
    assert "error" in check_stock("NO-00", 1)
    assert check_stock("TS-01", 0)["in_stock"] is False
    assert check_stock("TS-01", -1)["in_stock"] is False