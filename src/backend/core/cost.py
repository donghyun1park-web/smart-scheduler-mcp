from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable, Mapping

from core import db
from core.number_utils import percentage, to_float


def calculate_cost_execution_rate(execution_budget: float, invested_cost: float) -> float:
    """Return cost execution rate as a percentage."""
    return round(percentage(invested_cost, execution_budget), 2)


def calculate_billing_rate(contract_amount: float, billing_amount: float) -> float:
    """Return billing rate as a percentage."""
    return round(percentage(billing_amount, contract_amount), 2)


def detect_cost_overrun(
    progress_pct: float,
    cost_execution_rate: float,
    threshold: float = 10.0,
) -> bool:
    """Return true when cost rate is materially ahead of progress."""
    progress = _as_percent(progress_pct)
    cost_rate = _as_percent(cost_execution_rate)
    threshold_pct = threshold * 100 if 0 < threshold <= 1 else threshold
    return (cost_rate - progress) > threshold_pct


def forecast_completion_cost(items: Iterable[Mapping[str, Any]]) -> dict[str, float | bool]:
    execution_budget_total = 0.0
    invested_cost_total = 0.0
    forecast_total = 0.0
    for item in items:
        budget = to_float(item.get("execution_budget"))
        invested = to_float(item.get("invested_cost"))
        progress_pct = _as_percent(to_float(item.get("progress_pct")))
        execution_budget_total += budget
        invested_cost_total += invested
        if progress_pct > 0:
            forecast_total += invested / (progress_pct / 100)
        else:
            forecast_total += budget
    forecast_total = round(forecast_total, 2)
    return {
        "execution_budget_total": round(execution_budget_total, 2),
        "invested_cost_total": round(invested_cost_total, 2),
        "forecast_completion_cost": forecast_total,
        "forecast_over_budget": forecast_total > execution_budget_total,
    }


def _as_percent(value: float) -> float:
    return value * 100 if 0 <= value <= 1 else value


# ---------------------------------------------------------------------------
# Budget variance analysis (DDC-inspired)
# ---------------------------------------------------------------------------

# Variance thresholds: positive means under budget, negative means over
VARIANCE_THRESHOLDS = {
    "절감": 5.0,     # Under budget > +5%
    "정상": -5.0,    # On budget -5% ~ +5%
    "초과": -15.0,   # Over budget -15% ~ -5%
    # Below -15% → "위험" (Critical)
}


def classify_variance_status(variance_pct: float) -> str:
    """Classify budget variance percentage into status label.

    variance_pct is (budget - forecast) / budget * 100.
    Positive = under budget, negative = over budget.
    """
    if variance_pct > VARIANCE_THRESHOLDS["절감"]:
        return "절감"
    if variance_pct >= VARIANCE_THRESHOLDS["정상"]:
        return "정상"
    if variance_pct >= VARIANCE_THRESHOLDS["초과"]:
        return "초과"
    return "위험"


def analyze_budget_variance(
    db_path: str | Path,
    *,
    discipline: str | None = None,
    as_of_date: date | None = None,
) -> dict[str, Any]:
    """Analyze budget vs actual cost variance per activity and discipline.

    Returns per-item variance with status classification,
    discipline-level rollups, and overall summary.
    """
    today = as_of_date or date.today()
    activities = db.list_activities(db_path)
    if discipline:
        activities = [a for a in activities if a.discipline == discipline]
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}

    items: list[dict[str, Any]] = []
    disc_data: dict[str, dict[str, float]] = defaultdict(
        lambda: {"budget": 0, "invested": 0, "forecast": 0, "count": 0}
    )

    for act in activities:
        cost = cost_map.get(act.activity_id)
        if not cost:
            continue

        budget = cost.execution_budget
        invested = cost.invested_cost

        # Forecast: EAC based on progress
        progress_pct = _get_progress(db_path, act, today)
        if progress_pct > 0:
            forecast = invested / (progress_pct / 100)
        else:
            forecast = budget

        variance_amount = budget - forecast
        variance_pct = (variance_amount / budget * 100) if budget > 0 else 0.0
        status = classify_variance_status(variance_pct)

        items.append({
            "activity_id": act.activity_id,
            "code": act.code,
            "name": act.name,
            "discipline": act.discipline,
            "execution_budget": round(budget, 0),
            "invested_cost": round(invested, 0),
            "forecast_cost": round(forecast, 0),
            "progress_pct": round(progress_pct, 1),
            "variance_amount": round(variance_amount, 0),
            "variance_pct": round(variance_pct, 1),
            "status": status,
        })

        d = disc_data[act.discipline]
        d["budget"] += budget
        d["invested"] += invested
        d["forecast"] += forecast
        d["count"] += 1

    # Discipline rollup
    disc_rows: list[dict[str, Any]] = []
    for disc in sorted(disc_data.keys()):
        d = disc_data[disc]
        b = d["budget"]
        f = d["forecast"]
        v_amt = b - f
        v_pct = (v_amt / b * 100) if b > 0 else 0.0
        disc_rows.append({
            "discipline": disc,
            "activity_count": int(d["count"]),
            "execution_budget": round(b, 0),
            "invested_cost": round(d["invested"], 0),
            "forecast_cost": round(f, 0),
            "variance_amount": round(v_amt, 0),
            "variance_pct": round(v_pct, 1),
            "status": classify_variance_status(v_pct),
        })

    # Overall
    total_budget = sum(d["budget"] for d in disc_data.values())
    total_invested = sum(d["invested"] for d in disc_data.values())
    total_forecast = sum(d["forecast"] for d in disc_data.values())
    overall_variance = total_budget - total_forecast
    overall_variance_pct = (overall_variance / total_budget * 100) if total_budget > 0 else 0.0
    critical_count = sum(1 for i in items if i["status"] == "위험")
    over_count = sum(1 for i in items if i["status"] == "초과")

    return {
        "ok": True,
        "as_of_date": today.isoformat(),
        "filter_discipline": discipline,
        "activity_count": len(items),
        "items": items,
        "discipline_summary": disc_rows,
        "overall": {
            "execution_budget": round(total_budget, 0),
            "invested_cost": round(total_invested, 0),
            "forecast_cost": round(total_forecast, 0),
            "variance_amount": round(overall_variance, 0),
            "variance_pct": round(overall_variance_pct, 1),
            "status": classify_variance_status(overall_variance_pct),
            "critical_count": critical_count,
            "over_budget_count": over_count,
        },
    }


def forecast_scenarios(
    db_path: str | Path,
    *,
    discipline: str | None = None,
    optimistic_factor: float = 0.95,
    pessimistic_factor: float = 1.15,
) -> dict[str, Any]:
    """Generate three EAC forecast scenarios: optimistic, most likely, pessimistic.

    Parameters
    ----------
    optimistic_factor : multiplier for optimistic forecast (< 1.0 = lower cost)
    pessimistic_factor : multiplier for pessimistic forecast (> 1.0 = higher cost)
    """
    variance = analyze_budget_variance(db_path, discipline=discipline)
    if not variance["ok"]:
        return variance

    overall = variance["overall"]
    budget = overall["execution_budget"]
    forecast_base = overall["forecast_cost"]

    scenarios = {
        "낙관": {
            "name": "낙관 (Optimistic)",
            "description": "최선의 경우: 추가 초과 없음, 효율 개선",
            "forecast": round(forecast_base * optimistic_factor, 0),
            "variance_from_budget": round(budget - forecast_base * optimistic_factor, 0),
        },
        "현실": {
            "name": "현실 (Most Likely)",
            "description": "현재 추세 유지",
            "forecast": round(forecast_base, 0),
            "variance_from_budget": round(budget - forecast_base, 0),
        },
        "비관": {
            "name": "비관 (Pessimistic)",
            "description": "추가 비용 증가 예상",
            "forecast": round(forecast_base * pessimistic_factor, 0),
            "variance_from_budget": round(budget - forecast_base * pessimistic_factor, 0),
        },
    }

    return {
        "ok": True,
        "execution_budget": budget,
        "filter_discipline": discipline,
        "scenarios": scenarios,
    }


def _get_progress(db_path: str | Path, activity: Any, as_of: date) -> float:
    """Get actual progress % for an activity from daily records, or time-based fallback."""
    records = db.list_daily_records(db_path, activity_id=activity.activity_id, end_date=as_of)
    if records:
        planned = sum(r.planned_qty for r in records)
        actual = sum(r.actual_qty for r in records)
        if planned > 0:
            return min(percentage(actual, planned), 100.0)
    # Fallback: time-based
    if activity.es_date is None or activity.ef_date is None:
        return 0.0
    if as_of < activity.es_date:
        return 0.0
    if as_of >= activity.ef_date:
        return 100.0
    total = max((activity.ef_date - activity.es_date).days, 1)
    elapsed = (as_of - activity.es_date).days
    return round(elapsed / total * 100, 2)
