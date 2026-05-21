"""Validation helpers for Smart Node-Scheduler v0.1.

Reusable helpers for coercing and validating untrusted inputs
(spreadsheet rows, MCP tool arguments, preset files). Each helper
raises ``ValidationError`` with a precise, human-readable message
so callers can surface row-level failures without losing context.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Iterable

from core.cost import detect_cost_overrun
from core.progress import calculate_quantity_progress


class ValidationError(ValueError):
    """Raised when an input value fails validation.

    Inherits from ``ValueError`` so existing ``except ValueError``
    handlers continue to work.
    """


def require_text(value: Any, field: str, *, max_length: int | None = None) -> str:
    """Return ``value`` as a non-empty stripped string or raise."""
    if value is None:
        raise ValidationError(f"{field} is required")
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field} must not be empty")
    if max_length is not None and len(text) > max_length:
        raise ValidationError(
            f"{field} length {len(text)} exceeds maximum {max_length}"
        )
    return text


def optional_text(value: Any, *, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip() or default


def require_int(
    value: Any,
    field: str,
    *,
    minimum: int | None = None,
    maximum: int | None = None,
) -> int:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValidationError(f"{field} is required")
    try:
        if isinstance(value, bool):  # bool is an int subclass; reject explicitly
            raise TypeError
        if isinstance(value, str):
            number = int(value.strip())
        else:
            number = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be an integer (got {value!r})") from exc
    if minimum is not None and number < minimum:
        raise ValidationError(f"{field} must be >= {minimum} (got {number})")
    if maximum is not None and number > maximum:
        raise ValidationError(f"{field} must be <= {maximum} (got {number})")
    return number


def optional_float(value: Any, field: str, *, default: float = 0.0) -> float:
    if value is None or (isinstance(value, str) and not value.strip()):
        return default
    try:
        if isinstance(value, bool):
            raise TypeError
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError(f"{field} must be a number (got {value!r})") from exc


def require_iso_date(value: Any, field: str) -> date:
    if value is None:
        raise ValidationError(f"{field} is required")
    if isinstance(value, date):
        return value
    text = str(value).strip()
    if not text:
        raise ValidationError(f"{field} is required")
    try:
        return date.fromisoformat(text)
    except ValueError as exc:
        raise ValidationError(
            f"{field} must be ISO date (YYYY-MM-DD), got {value!r}"
        ) from exc


def require_choice(value: Any, field: str, choices: Iterable[str]) -> str:
    text = require_text(value, field)
    allowed = tuple(choices)
    if text not in allowed:
        raise ValidationError(
            f"{field} must be one of {list(allowed)} (got {text!r})"
        )
    return text


def validate_date_order(
    activity_id: str,
    activity_name: str,
    start_date: date,
    finish_date: date,
) -> list[str]:
    if finish_date >= start_date:
        return []
    return [
        (
            f"{activity_name} ({activity_id}) finish date is before start date: "
            f"start={start_date.isoformat()}, finish={finish_date.isoformat()}."
        )
    ]


def validate_progress_quantities(
    activity_id: str,
    activity_name: str,
    planned_qty: float,
    actual_qty: float,
) -> list[str]:
    issues: list[str] = []
    if planned_qty <= 0 and actual_qty > 0:
        issues.append(
            f"{activity_name} ({activity_id}) planned quantity is 0 but actual quantity is {actual_qty}."
        )
    progress_pct = calculate_quantity_progress(planned_qty, actual_qty)
    if progress_pct > 100:
        issues.append(
            (
                f"{activity_name} ({activity_id}) progress exceeds 100%: "
                f"planned={planned_qty}, actual={actual_qty}, calculated={progress_pct:.1f}%."
            )
        )
    return issues


def validate_cost_progress_gap(
    activity_id: str,
    activity_name: str,
    *,
    progress_pct: float,
    cost_execution_rate: float,
    threshold: float = 10.0,
) -> list[str]:
    if not detect_cost_overrun(progress_pct, cost_execution_rate, threshold):
        return []
    gap = cost_execution_rate - progress_pct
    return [
        (
            f"{activity_name} ({activity_id}) cost overrun risk: progress={progress_pct:.1f}%, "
            f"cost_execution={cost_execution_rate:.1f}%, gap={gap:.1f}%."
        )
    ]


def validate_owner_present(
    activity_id: str,
    activity_name: str,
    *,
    discipline: str,
    zone: str,
    owner: str | None,
) -> list[str]:
    if owner and owner.strip():
        return []
    return [
        (
            f"{activity_name} ({activity_id}) owner is missing: "
            f"discipline={discipline}, zone={zone}."
        )
    ]


def validate_change_approval(
    target_table: str,
    target_id: str,
    *,
    changed_at: date,
    approved_by: str | None,
) -> list[str]:
    if approved_by and approved_by.strip():
        return []
    return [
        (
            f"{target_table} change {target_id} has no approval: "
            f"changed_at={changed_at.isoformat()}, approved_by is empty."
        )
    ]
