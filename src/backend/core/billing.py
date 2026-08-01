"""Billing (기성고) calculation engine.

Provides monthly billing computation, billing summary by discipline,
and billing S-curve data for planned/actual/billed comparisons.

Billing workflow:
1. Progress → Earned Value (EV) per activity
2. EV → Monthly billing amount per discipline
3. Cumulative billing → S-curve (contract plan vs execution vs billed)
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from core import db
from core.models import Activity, CostItem
from core.number_utils import percentage


# ---------------------------------------------------------------------------
# Monthly billing calculation
# ---------------------------------------------------------------------------


def calculate_monthly_billing(
    db_path: str | Path,
    year_month: str,
    *,
    discipline: str | None = None,
) -> dict[str, Any]:
    """Calculate earned-value-based billing for a given month (YYYY-MM).

    For each activity, billing = execution_budget * progress_pct_this_month.
    Progress is derived from daily records if available, otherwise from
    time-based linear interpolation.

    Returns per-activity billing rows and discipline-level totals.
    """
    year, month = _parse_year_month(year_month)
    month_start = date(year, month, 1)
    month_end = _month_end(year, month)

    activities = db.list_activities(db_path)
    if discipline:
        activities = [a for a in activities if a.discipline == discipline]
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}

    rows: list[dict[str, Any]] = []
    warnings: list[str] = []

    for act in activities:
        cost = cost_map.get(act.activity_id)
        if not cost:
            continue

        # Progress at month end vs month start
        progress_end = _progress_at(db_path, act, cost, month_end)
        progress_start = _progress_at(db_path, act, cost, month_start - timedelta(days=1))
        month_progress = max(progress_end - progress_start, 0.0)

        contract_billing = round(cost.contract_amount * month_progress / 100, 0)
        execution_billing = round(cost.execution_budget * month_progress / 100, 0)

        if contract_billing == 0 and execution_billing == 0:
            continue

        rows.append({
            "activity_id": act.activity_id,
            "code": act.code,
            "name": act.name,
            "discipline": act.discipline,
            "contract_amount": cost.contract_amount,
            "execution_budget": cost.execution_budget,
            "progress_start_pct": round(progress_start, 2),
            "progress_end_pct": round(progress_end, 2),
            "month_progress_pct": round(month_progress, 2),
            "contract_billing": contract_billing,
            "execution_billing": execution_billing,
        })

    # Discipline totals
    disc_totals = _discipline_totals(rows)

    # Grand totals
    total_contract_billing = sum(r["contract_billing"] for r in rows)
    total_execution_billing = sum(r["execution_billing"] for r in rows)

    return {
        "ok": True,
        "year_month": year_month,
        "filter_discipline": discipline,
        "activity_count": len(rows),
        "rows": rows,
        "discipline_totals": disc_totals,
        "total_contract_billing": total_contract_billing,
        "total_execution_billing": total_execution_billing,
        "warnings": warnings,
    }


def update_billing_amounts(
    db_path: str | Path,
    year_month: str,
    *,
    discipline: str | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Calculate monthly billing and optionally update cost_items.billing_amount.

    When dry_run=False, adds the month's billing to each cost_item's
    cumulative billing_amount.
    """
    result = calculate_monthly_billing(db_path, year_month, discipline=discipline)
    if not result["ok"]:
        return result

    updated = 0
    if not dry_run:
        cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}
        for row in result["rows"]:
            cost = cost_map.get(row["activity_id"])
            if not cost:
                continue
            new_billing = cost.billing_amount + row["contract_billing"]
            db.upsert_cost_item(
                db_path,
                CostItem(
                    cost_item_id=cost.cost_item_id,
                    activity_id=cost.activity_id,
                    contract_amount=cost.contract_amount,
                    execution_budget=cost.execution_budget,
                    invested_cost=cost.invested_cost,
                    billing_amount=new_billing,
                ),
            )
            updated += 1

    return {
        **result,
        "dry_run": dry_run,
        "updated_count": updated,
    }


# ---------------------------------------------------------------------------
# Billing summary by discipline
# ---------------------------------------------------------------------------


def get_billing_summary(
    db_path: str | Path,
) -> dict[str, Any]:
    """Return cumulative billing summary grouped by discipline.

    Shows contract_amount, execution_budget, billing_amount, and rates.
    """
    activities = db.list_activities(db_path)
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}

    disc_data: dict[str, dict[str, float]] = defaultdict(
        lambda: {"contract": 0, "execution": 0, "billing": 0, "invested": 0, "count": 0}
    )

    for act in activities:
        cost = cost_map.get(act.activity_id)
        if not cost:
            continue
        d = disc_data[act.discipline]
        d["contract"] += cost.contract_amount
        d["execution"] += cost.execution_budget
        d["billing"] += cost.billing_amount
        d["invested"] += cost.invested_cost
        d["count"] += 1

    rows: list[dict[str, Any]] = []
    for disc in sorted(disc_data.keys()):
        d = disc_data[disc]
        billing_rate = percentage(d["billing"], d["contract"])
        execution_rate = percentage(d["invested"], d["execution"])
        rows.append({
            "discipline": disc,
            "activity_count": int(d["count"]),
            "contract_amount": round(d["contract"], 0),
            "execution_budget": round(d["execution"], 0),
            "billing_amount": round(d["billing"], 0),
            "invested_cost": round(d["invested"], 0),
            "billing_rate_pct": round(billing_rate, 2),
            "execution_rate_pct": round(execution_rate, 2),
        })

    total_contract = sum(r["contract_amount"] for r in rows)
    total_execution = sum(r["execution_budget"] for r in rows)
    total_billing = sum(r["billing_amount"] for r in rows)

    return {
        "ok": True,
        "rows": rows,
        "total_contract": total_contract,
        "total_execution": total_execution,
        "total_billing": total_billing,
        "overall_billing_rate_pct": round(percentage(total_billing, total_contract), 2),
    }


# ---------------------------------------------------------------------------
# Billing S-curve
# ---------------------------------------------------------------------------


def get_billing_s_curve(
    db_path: str | Path,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    interval: str = "monthly",
) -> dict[str, Any]:
    """Return billing S-curve data: planned vs actual cumulative billing by period.

    interval: 'monthly' or 'quarterly'
    """
    activities = db.list_activities(db_path)
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}

    # Determine date range from activities
    es_dates = [a.es_date for a in activities if a.es_date]
    ef_dates = [a.ef_date for a in activities if a.ef_date]
    if not es_dates or not ef_dates:
        return {"ok": True, "series": [], "warnings": ["No activities with dates"]}

    range_start = _parse_date_or(start_date, min(es_dates))
    range_end = _parse_date_or(end_date, max(ef_dates))

    # Build period list
    periods = _build_periods(range_start, range_end, interval)

    series: list[dict[str, Any]] = []
    cum_planned = 0.0
    cum_actual = 0.0

    for period_start, period_end, label in periods:
        planned_this = 0.0
        actual_this = 0.0

        for act in activities:
            cost = cost_map.get(act.activity_id)
            if not cost:
                continue
            # Planned: linear spread of contract over activity duration
            p_this = _planned_billing_in_period(act, cost, period_start, period_end)
            planned_this += p_this
            # Actual: progress-based earned value in period
            a_end = _progress_at(db_path, act, cost, period_end)
            a_start = _progress_at(db_path, act, cost, period_start - timedelta(days=1))
            actual_this += max(cost.contract_amount * (a_end - a_start) / 100, 0)

        cum_planned += planned_this
        cum_actual += actual_this

        series.append({
            "period": label,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "planned_this_period": round(planned_this, 0),
            "actual_this_period": round(actual_this, 0),
            "cumulative_planned": round(cum_planned, 0),
            "cumulative_actual": round(cum_actual, 0),
        })

    return {"ok": True, "series": series, "interval": interval, "warnings": []}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _progress_at(
    db_path: str | Path,
    activity: Activity,
    cost: CostItem,
    as_of: date,
) -> float:
    """Return progress percentage at a given date.

    Uses daily records if available, otherwise linear time-based estimate.
    """
    records = db.list_daily_records(db_path, activity_id=activity.activity_id, end_date=as_of)
    if records:
        planned = sum(r.planned_qty for r in records)
        actual = sum(r.actual_qty for r in records)
        if planned > 0:
            return min(percentage(actual, planned), 100.0)

    # Fallback: time-based linear
    if activity.es_date is None or activity.ef_date is None:
        return 0.0
    if as_of < activity.es_date:
        return 0.0
    if as_of >= activity.ef_date:
        return 100.0
    total = max((activity.ef_date - activity.es_date).days, 1)
    elapsed = (as_of - activity.es_date).days
    return round(elapsed / total * 100, 2)


def _planned_billing_in_period(
    activity: Activity,
    cost: CostItem,
    period_start: date,
    period_end: date,
) -> float:
    """Calculate planned billing for an activity in a given period (linear spread)."""
    if activity.es_date is None or activity.ef_date is None:
        return 0.0
    if cost.contract_amount == 0:
        return 0.0

    # Overlap between activity span and period
    overlap_start = max(activity.es_date, period_start)
    overlap_end = min(activity.ef_date, period_end)
    if overlap_start > overlap_end:
        return 0.0

    total_days = max((activity.ef_date - activity.es_date).days, 1)
    overlap_days = (overlap_end - overlap_start).days + 1
    return cost.contract_amount * overlap_days / total_days


def _discipline_totals(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Aggregate billing rows by discipline."""
    groups: dict[str, dict[str, float]] = defaultdict(
        lambda: {"contract_billing": 0, "execution_billing": 0, "count": 0}
    )
    for r in rows:
        g = groups[r["discipline"]]
        g["contract_billing"] += r["contract_billing"]
        g["execution_billing"] += r["execution_billing"]
        g["count"] += 1

    return [
        {
            "discipline": disc,
            "activity_count": int(g["count"]),
            "contract_billing": round(g["contract_billing"], 0),
            "execution_billing": round(g["execution_billing"], 0),
        }
        for disc, g in sorted(groups.items())
    ]


def _parse_year_month(ym: str) -> tuple[int, int]:
    """Parse 'YYYY-MM' string."""
    parts = ym.strip().split("-")
    if len(parts) != 2:
        raise ValueError(f"Expected YYYY-MM format, got: {ym}")
    return int(parts[0]), int(parts[1])


def _month_end(year: int, month: int) -> date:
    """Return the last day of the given month."""
    if month == 12:
        return date(year + 1, 1, 1) - timedelta(days=1)
    return date(year, month + 1, 1) - timedelta(days=1)


def _parse_date_or(value: str | None, fallback: date) -> date:
    if value and value.strip():
        return date.fromisoformat(value.strip())
    return fallback


def _build_periods(
    start: date,
    end: date,
    interval: str,
) -> list[tuple[date, date, str]]:
    """Build list of (period_start, period_end, label) tuples."""
    periods: list[tuple[date, date, str]] = []
    current = date(start.year, start.month, 1)

    while current <= end:
        if interval == "quarterly":
            q_month = current.month
            q_end_month = q_month + 2
            q_end_year = current.year
            if q_end_month > 12:
                q_end_month -= 12
                q_end_year += 1
            p_end = _month_end(q_end_year, q_end_month)
            label = f"{current.year}Q{(current.month - 1) // 3 + 1}"
            periods.append((current, min(p_end, end), label))
            # Advance 3 months
            m = current.month + 3
            y = current.year
            if m > 12:
                m -= 12
                y += 1
            current = date(y, m, 1)
        else:
            p_end = _month_end(current.year, current.month)
            label = f"{current.year}-{current.month:02d}"
            periods.append((current, min(p_end, end), label))
            m = current.month + 1
            y = current.year
            if m > 12:
                m = 1
                y += 1
            current = date(y, m, 1)

    return periods
