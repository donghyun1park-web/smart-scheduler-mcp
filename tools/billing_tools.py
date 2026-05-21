"""MCP tools for billing (기성고) workflow."""
from __future__ import annotations

from typing import Any

from core.billing import (
    calculate_monthly_billing,
    get_billing_s_curve,
    get_billing_summary,
    update_billing_amounts,
)


def calculate_billing(
    db_path: str,
    year_month: str,
    *,
    discipline: str | None = None,
) -> dict[str, Any]:
    """Calculate earned-value-based monthly billing for a .scheduler DB.

    Parameters
    ----------
    db_path : path to the .scheduler file
    year_month : target month in YYYY-MM format (e.g. '2028-06')
    discipline : optional filter by discipline (e.g. '기계설비')

    Returns activity-level billing rows, discipline totals, and grand totals.
    """
    return calculate_monthly_billing(db_path, year_month, discipline=discipline)


def apply_billing(
    db_path: str,
    year_month: str,
    *,
    discipline: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Calculate and optionally apply monthly billing to the DB.

    Set dry_run=False to actually update cost_items.billing_amount.
    Default is dry_run=True (preview only).
    """
    return update_billing_amounts(
        db_path, year_month, discipline=discipline, dry_run=dry_run,
    )


def billing_summary(
    db_path: str,
) -> dict[str, Any]:
    """Return cumulative billing summary grouped by discipline.

    Shows contract, execution, billing amounts and rates for each discipline.
    """
    return get_billing_summary(db_path)


def billing_s_curve(
    db_path: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    interval: str = "monthly",
) -> dict[str, Any]:
    """Return billing S-curve data for chart rendering.

    Returns cumulative planned vs actual billing by period.
    interval: 'monthly' (default) or 'quarterly'
    """
    return get_billing_s_curve(
        db_path, start_date=start_date, end_date=end_date, interval=interval,
    )
