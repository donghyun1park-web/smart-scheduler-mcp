"""Cash flow forecasting engine.

Provides:
- Period-by-period cash flow forecast (inflows vs outflows)
- Payment schedule generation with configurable terms and retention
- Funding requirement analysis (peak deficit, cumulative needs)
- Cost distribution methods: linear, front-loaded, back-loaded, s-curve

Uses existing activities + cost_items tables — no new DB tables needed.

Inspired by DDC Cash Flow Forecaster, adapted to function-based pattern.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from core import db
from core.billing import _build_periods
from core.models import Activity


# ---------------------------------------------------------------------------
# Payment terms constants
# ---------------------------------------------------------------------------

PAYMENT_TERMS: dict[str, int] = {
    "NET_30": 30,
    "NET_45": 45,
    "NET_60": 60,
    "NET_90": 90,
    "MILESTONE": 0,
    "IMMEDIATE": 0,
}

DISTRIBUTION_METHODS = ("linear", "front_loaded", "back_loaded", "s_curve")


# ---------------------------------------------------------------------------
# Main entry: forecast_cash_flow
# ---------------------------------------------------------------------------


def forecast_cash_flow(
    db_path: str | Path,
    start_date: str | None = None,
    end_date: str | None = None,
    *,
    payment_terms: str = "NET_30",
    retention_pct: float = 10.0,
    distribution: str = "linear",
    interval: str = "monthly",
    discipline: str | None = None,
) -> dict[str, Any]:
    """Forecast project cash flow with inflows (기성) and outflows (투입).

    Parameters
    ----------
    db_path : path to the .scheduler file
    start_date / end_date : forecast range (YYYY-MM-DD), auto-detected if None
    payment_terms : 'NET_30', 'NET_45', 'NET_60', 'NET_90', 'MILESTONE'
    retention_pct : retention percentage (0-100), released at project end
    distribution : cost distribution method ('linear', 'front_loaded', 'back_loaded', 's_curve')
    interval : 'monthly' or 'quarterly'
    discipline : filter by discipline (optional)

    Returns period-by-period cash flow with inflows, outflows, net, cumulative.
    """
    activities = db.list_activities(db_path)
    if discipline:
        activities = [a for a in activities if a.discipline == discipline]
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}

    if not activities:
        return {"ok": True, "periods": [], "summary": {}, "warnings": ["활동이 없습니다."]}

    # Determine date range
    es_dates = [a.es_date for a in activities if a.es_date]
    ef_dates = [a.ef_date for a in activities if a.ef_date]
    if not es_dates or not ef_dates:
        return {"ok": True, "periods": [], "summary": {}, "warnings": ["날짜가 지정된 활동이 없습니다."]}

    range_start = _parse_date(start_date) or min(es_dates)
    range_end = _parse_date(end_date) or max(ef_dates)

    # Validate
    if distribution not in DISTRIBUTION_METHODS:
        return {"ok": False, "error": f"지원하지 않는 분배 방식: {distribution}. 가능: {DISTRIBUTION_METHODS}"}
    if payment_terms not in PAYMENT_TERMS:
        return {"ok": False, "error": f"지원하지 않는 지불조건: {payment_terms}. 가능: {list(PAYMENT_TERMS.keys())}"}

    payment_delay_days = PAYMENT_TERMS[payment_terms]

    # Build periods
    periods = _build_periods(range_start, range_end, interval)

    # Calculate period-by-period cash flow
    result_periods: list[dict[str, Any]] = []
    cumulative_inflow = 0.0
    cumulative_outflow = 0.0
    cumulative_net = 0.0

    for period_start, period_end, label in periods:
        period_inflow = 0.0
        period_outflow = 0.0

        for act in activities:
            cost = cost_map.get(act.activity_id)
            if not cost:
                continue

            # Outflow: planned cost distribution over activity duration
            raw_outflow = _distributed_cost_in_period(
                act, cost.execution_budget, period_start, period_end, distribution,
            )
            period_outflow += raw_outflow

            # Inflow: billing (contract-based) with payment delay
            inflow = _billing_inflow_in_period(
                act, cost.contract_amount, period_start, period_end,
                payment_delay_days, retention_pct,
            )
            period_inflow += inflow

        period_net = period_inflow - period_outflow
        cumulative_inflow += period_inflow
        cumulative_outflow += period_outflow
        cumulative_net += period_net

        result_periods.append({
            "period": label,
            "period_start": period_start.isoformat(),
            "period_end": period_end.isoformat(),
            "inflow": round(period_inflow, 0),
            "outflow": round(period_outflow, 0),
            "net": round(period_net, 0),
            "cumulative_inflow": round(cumulative_inflow, 0),
            "cumulative_outflow": round(cumulative_outflow, 0),
            "cumulative_net": round(cumulative_net, 0),
        })

    # Retention release (at project end + 60 days)
    total_retention = sum(
        cost_map[a.activity_id].contract_amount * retention_pct / 100
        for a in activities if a.activity_id in cost_map
    )

    # Summary
    min_net = min((p["cumulative_net"] for p in result_periods), default=0)
    peak_deficit_period = ""
    for p in result_periods:
        if p["cumulative_net"] == min_net:
            peak_deficit_period = p["period"]
            break

    if min_net >= 0:
        status = "자금 여유"
        status_level = "green"
    elif min_net >= -cumulative_outflow * 0.1:
        status = "자금 주의"
        status_level = "yellow"
    else:
        status = "자금 부족"
        status_level = "red"

    summary = {
        "total_inflow": round(cumulative_inflow, 0),
        "total_outflow": round(cumulative_outflow, 0),
        "total_net": round(cumulative_net, 0),
        "peak_deficit": round(min(min_net, 0), 0),
        "peak_deficit_period": peak_deficit_period,
        "retention_held": round(total_retention, 0),
        "status": status,
        "status_level": status_level,
        "payment_terms": payment_terms,
        "retention_pct": retention_pct,
        "distribution": distribution,
    }

    return {
        "ok": True,
        "periods": result_periods,
        "summary": summary,
        "warnings": [],
    }


# ---------------------------------------------------------------------------
# Funding requirements
# ---------------------------------------------------------------------------


def calculate_funding_requirements(
    db_path: str | Path,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
    payment_terms: str = "NET_30",
    retention_pct: float = 10.0,
    distribution: str = "linear",
    buffer_pct: float = 10.0,
) -> dict[str, Any]:
    """Calculate funding requirements: peak funding, monthly needs, buffer.

    Parameters
    ----------
    buffer_pct : additional buffer percentage on top of peak funding need
    """
    forecast = forecast_cash_flow(
        db_path, start_date, end_date,
        payment_terms=payment_terms,
        retention_pct=retention_pct,
        distribution=distribution,
    )
    if not forecast["ok"]:
        return forecast

    periods = forecast["periods"]
    if not periods:
        return {
            "ok": True,
            "peak_funding_required": 0,
            "peak_funding_period": "",
            "monthly_needs": [],
            "buffer_pct": buffer_pct,
        }

    # Find peak negative cumulative net
    min_net = 0.0
    peak_period = ""
    for p in periods:
        if p["cumulative_net"] < min_net:
            min_net = p["cumulative_net"]
            peak_period = p["period"]

    peak_funding = abs(min_net)
    required_with_buffer = round(peak_funding * (1 + buffer_pct / 100), 0)

    # Monthly funding needs (periods where net is negative)
    monthly_needs = [
        {"period": p["period"], "funding_needed": round(abs(p["net"]), 0)}
        for p in periods if p["net"] < 0
    ]

    return {
        "ok": True,
        "peak_funding_required": required_with_buffer,
        "peak_funding_period": peak_period,
        "peak_funding_raw": round(peak_funding, 0),
        "buffer_pct": buffer_pct,
        "total_outflow": forecast["summary"]["total_outflow"],
        "total_inflow": forecast["summary"]["total_inflow"],
        "deficit_period_count": len(monthly_needs),
        "monthly_needs": monthly_needs,
    }


# ---------------------------------------------------------------------------
# Retention release schedule
# ---------------------------------------------------------------------------


def get_retention_schedule(
    db_path: str | Path,
    *,
    retention_pct: float = 10.0,
    release_days: int = 60,
    discipline: str | None = None,
) -> dict[str, Any]:
    """Calculate retention amounts held per discipline and release timeline.

    Parameters
    ----------
    retention_pct : retention percentage applied to contract amount
    release_days : days after project completion for retention release
    """
    activities = db.list_activities(db_path)
    if discipline:
        activities = [a for a in activities if a.discipline == discipline]
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}

    disc_retention: dict[str, float] = defaultdict(float)
    total_retention = 0.0

    for act in activities:
        cost = cost_map.get(act.activity_id)
        if not cost:
            continue
        retention = cost.contract_amount * retention_pct / 100
        disc_retention[act.discipline] += retention
        total_retention += retention

    # Determine project end date
    ef_dates = [a.ef_date for a in activities if a.ef_date]
    project_end = max(ef_dates) if ef_dates else None
    release_date = project_end + timedelta(days=release_days) if project_end else None

    rows = [
        {
            "discipline": disc,
            "retention_amount": round(amount, 0),
            "retention_pct": retention_pct,
        }
        for disc, amount in sorted(disc_retention.items())
    ]

    return {
        "ok": True,
        "total_retention": round(total_retention, 0),
        "retention_pct": retention_pct,
        "release_days": release_days,
        "project_end_date": project_end.isoformat() if project_end else None,
        "retention_release_date": release_date.isoformat() if release_date else None,
        "rows": rows,
    }


# ---------------------------------------------------------------------------
# Internal: cost distribution
# ---------------------------------------------------------------------------


def _distribute_amount(total: float, periods: int, method: str) -> list[float]:
    """Distribute a total amount over N periods using the specified method."""
    if periods <= 0:
        return [total]
    if periods == 1:
        return [total]

    weights: list[float]
    if method == "front_loaded":
        weights = [float(periods - i) for i in range(periods)]
    elif method == "back_loaded":
        weights = [float(i + 1) for i in range(periods)]
    elif method == "s_curve":
        # Simple S-curve using cubic approximation (no scipy needed)
        weights = []
        for i in range(periods):
            x = (i + 0.5) / periods  # 0..1 range
            # Bell-shaped derivative of S-curve: 6x(1-x)
            w = 6 * x * (1 - x) + 0.1  # +0.1 to avoid zero
            weights.append(w)
    else:  # linear
        weights = [1.0] * periods

    total_weight = sum(weights)
    return [total * w / total_weight for w in weights]


def _distributed_cost_in_period(
    activity: Activity,
    total_cost: float,
    period_start: date,
    period_end: date,
    distribution: str,
) -> float:
    """Calculate cost distributed into a period for an activity."""
    if activity.es_date is None or activity.ef_date is None:
        return 0.0
    if total_cost == 0:
        return 0.0

    # Overlap between activity span and period
    overlap_start = max(activity.es_date, period_start)
    overlap_end = min(activity.ef_date, period_end)
    if overlap_start > overlap_end:
        return 0.0

    total_days = max((activity.ef_date - activity.es_date).days, 1)
    overlap_days = (overlap_end - overlap_start).days + 1

    if distribution == "linear":
        # Simple proportional
        return total_cost * overlap_days / total_days

    # For non-linear distributions, calculate day-by-day weights
    daily_weights = _distribute_amount(total_cost, total_days, distribution)

    # Sum the weights for days that fall in this period
    start_offset = max((overlap_start - activity.es_date).days, 0)
    end_offset = min(start_offset + overlap_days, total_days)
    return sum(daily_weights[start_offset:end_offset])


def _billing_inflow_in_period(
    activity: Activity,
    contract_amount: float,
    period_start: date,
    period_end: date,
    payment_delay_days: int,
    retention_pct: float,
) -> float:
    """Calculate billing inflow for an activity in a period, with payment delay and retention."""
    if activity.es_date is None or activity.ef_date is None:
        return 0.0
    if contract_amount == 0:
        return 0.0

    # Earned value is generated linearly over activity duration
    # But payment is received after payment_delay_days
    # So the "earned" period is shifted back by payment_delay_days

    # Effective earning period (what was earned that gets paid in this billing period)
    earn_start = period_start - timedelta(days=payment_delay_days)
    earn_end = period_end - timedelta(days=payment_delay_days)

    # Overlap between activity span and earning period
    overlap_start = max(activity.es_date, earn_start)
    overlap_end = min(activity.ef_date, earn_end)
    if overlap_start > overlap_end:
        return 0.0

    total_days = max((activity.ef_date - activity.es_date).days, 1)
    overlap_days = (overlap_end - overlap_start).days + 1

    # Gross billing (proportional)
    gross = contract_amount * overlap_days / total_days

    # Net after retention
    net = gross * (1 - retention_pct / 100)
    return net


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str | None) -> date | None:
    if value and value.strip():
        return date.fromisoformat(value.strip())
    return None
