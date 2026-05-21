from __future__ import annotations

from decimal import Decimal

from core.number_utils import percentage, safe_divide, to_float


def test_to_float_handles_common_field_values():
    assert to_float(None) == 0.0
    assert to_float("") == 0.0
    assert to_float("1,234.5") == 1234.5
    assert to_float(" 12.3 % ") == 12.3
    assert to_float(Decimal("10.5")) == 10.5
    assert to_float("bad", default=-1.0) == -1.0


def test_to_float_rejects_non_finite_values():
    assert to_float(float("nan"), default=-1.0) == -1.0
    assert to_float(float("inf"), default=-1.0) == -1.0


def test_safe_divide_and_percentage_are_zero_safe():
    assert safe_divide(10, 2) == 5.0
    assert safe_divide(10, 0, default=0.0) == 0.0
    assert percentage(25, 100) == 25.0
    assert percentage("bad", 100, default=-1.0) == -1.0
