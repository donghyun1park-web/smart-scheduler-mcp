from __future__ import annotations

from decimal import Decimal
from math import isfinite
from typing import Any


def to_float(value: Any, default: float = 0.0) -> float:
    """Safely convert common field-input values to finite float values."""
    converted = _coerce_float(value)
    return default if converted is None else converted


def safe_divide(numerator: Any, denominator: Any, default: float = 0.0) -> float:
    """Divide two field values while protecting against zero and bad input."""
    left = _coerce_float(numerator)
    right = _coerce_float(denominator)
    if left is None or right is None or right == 0:
        return default
    result = left / right
    return result if isfinite(result) else default


def percentage(numerator: Any, denominator: Any, default: float = 0.0) -> float:
    """Return numerator / denominator * 100 with field-safe conversion."""
    left = _coerce_float(numerator)
    right = _coerce_float(denominator)
    if left is None or right is None or right == 0:
        return default
    result = (left / right) * 100
    return result if isfinite(result) else default


def _coerce_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        if isinstance(value, Decimal | int | float):
            result = float(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            if text.endswith("%"):
                text = text[:-1].strip()
            result = float(text.replace(",", ""))
        else:
            return None
    except (TypeError, ValueError, ArithmeticError):
        return None
    return result if isfinite(result) else None
