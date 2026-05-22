from __future__ import annotations

from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from core import db
from core.cost import analyze_budget_variance as _analyze_budget_variance
from core.cost import forecast_scenarios as _forecast_scenarios
from core.evm import calculate_evm_totals
from core.models import Activity, CostItem
from core.number_utils import percentage, to_float


def analyze_evm_from_db(
    db_path: str,
    *,
    project_id: str | None = None,
    as_of_date: str | None = None,
    discipline: str | None = None,
    zone: str | None = None,
) -> dict[str, object]:
    """Return an EVM snapshot from activity, cost, and daily-record DB data."""
    target_date = _parse_date(as_of_date) or date.today()
    rows, warnings = _activity_cost_rows(
        db_path,
        as_of=target_date,
        project_id=project_id,
        discipline=discipline,
        zone=zone,
    )
    totals = _evm_totals(rows)
    return {
        "ok": True,
        "as_of_date": target_date.isoformat(),
        "filters": {"project_id": project_id, "discipline": discipline, "zone": zone},
        "activity_count": len(rows),
        "totals": totals,
        "warnings": warnings,
    }


def get_evm_s_curve_data(
    db_path: str,
    *,
    project_id: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    discipline: str | None = None,
) -> dict[str, object]:
    """Return chart-ready cumulative PV/EV/AC rows by date."""
    activities = _filtered_activities(db_path, project_id=project_id, discipline=discipline, zone=None)
    inferred_start, inferred_end = _activity_date_bounds(activities)
    start = _parse_date(start_date) or inferred_start or date.today()
    end = _parse_date(end_date) or inferred_end or start
    if end < start:
        return {
            "ok": False,
            "series": [],
            "warnings": [f"end_date must be on or after start_date: start={start}, end={end}"],
        }

    series: list[dict[str, object]] = []
    warning_set: set[str] = set()
    for current in _date_range(start, end):
        rows, warnings = _activity_cost_rows(
            db_path,
            as_of=current,
            project_id=project_id,
            discipline=discipline,
            zone=None,
        )
        warning_set.update(warnings)
        totals = _evm_totals(rows)
        series.append(
            {
                "date": current.isoformat(),
                "pv": totals["pv"],
                "ev": totals["ev"],
                "ac": totals["ac"],
            }
        )
    return {"ok": True, "series": series, "warnings": sorted(warning_set)}


def summarize_cost_by_discipline(
    db_path: str,
    *,
    project_id: str | None = None,
) -> dict[str, object]:
    """Summarize contract, budget, actual cost, earned value, and billing by discipline."""
    rows, warnings = _activity_cost_rows(
        db_path,
        as_of=date.today(),
        project_id=project_id,
        discipline=None,
        zone=None,
    )
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["discipline"])].append(row)

    output_rows: list[dict[str, object]] = []
    for discipline, items in sorted(grouped.items()):
        contract_amount = sum(to_float(item["contract_amount"]) for item in items)
        execution_budget = sum(to_float(item["execution_budget"]) for item in items)
        actual_cost = sum(to_float(item["invested_cost"]) for item in items)
        billing_amount = sum(to_float(item["billing_amount"]) for item in items)
        earned_value = sum(
            to_float(item["execution_budget"]) * to_float(item["actual_progress_pct"]) / 100
            for item in items
        )
        actual_progress = percentage(earned_value, execution_budget)
        cost_execution_rate = percentage(actual_cost, execution_budget)
        billing_rate = percentage(billing_amount, contract_amount)
        evm_totals = _evm_totals(items)
        output_rows.append(
            {
                "discipline": discipline,
                "activity_count": len(items),
                "contract_amount": round(contract_amount, 2),
                "execution_budget": round(execution_budget, 2),
                "actual_cost": round(actual_cost, 2),
                "earned_value": round(earned_value, 2),
                "billing_amount": round(billing_amount, 2),
                "cost_execution_rate": round(cost_execution_rate, 2),
                "billing_rate": round(billing_rate, 2),
                "cost_vs_progress_gap": round(cost_execution_rate - actual_progress, 2),
                "status": evm_totals["status"],
            }
        )

    return {"ok": True, "rows": output_rows, "warnings": warnings}


def _activity_cost_rows(
    path: str | Path,
    *,
    as_of: date,
    project_id: str | None,
    discipline: str | None,
    zone: str | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    activities = _filtered_activities(path, project_id=project_id, discipline=discipline, zone=zone)
    cost_by_activity = {item.activity_id: item for item in db.list_cost_items(path)}
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    used_progress_proxy = False
    for activity in activities:
        cost_item = cost_by_activity.get(activity.activity_id, CostItem(f"missing-{activity.activity_id}", activity.activity_id))
        actual_progress, has_actual = _actual_progress_pct(path, activity.activity_id, as_of)
        if not has_actual:
            actual_progress = _planned_progress_pct(activity, as_of)
            used_progress_proxy = True
        rows.append(
            {
                "activity_id": activity.activity_id,
                "code": activity.code,
                "name": activity.name,
                "discipline": activity.discipline,
                "zone": activity.zone,
                "planned_progress_pct": _planned_progress_pct(activity, as_of),
                "actual_progress_pct": actual_progress,
                "contract_amount": cost_item.contract_amount,
                "execution_budget": cost_item.execution_budget,
                "invested_cost": cost_item.invested_cost,
                "billing_amount": cost_item.billing_amount,
            }
        )
    if used_progress_proxy:
        warnings.append("실적 공정률 자료가 없는 작업은 계획공정률을 임시 기준으로 사용했습니다. 검토 필요.")
    return rows, warnings


def _filtered_activities(
    path: str | Path,
    *,
    project_id: str | None,
    discipline: str | None,
    zone: str | None,
) -> list[Activity]:
    summary = db.load_project_summary(path)
    project = summary.get("project")
    if project_id and getattr(project, "project_id", None) != project_id:
        return []
    activities = db.list_activities(path)
    if discipline:
        activities = [activity for activity in activities if activity.discipline == discipline]
    if zone:
        activities = [activity for activity in activities if activity.zone == zone]
    return activities


def _actual_progress_pct(path: str | Path, activity_id: str, as_of: date) -> tuple[float, bool]:
    records = db.list_daily_records(path, activity_id=activity_id, end_date=as_of)
    if not records:
        return 0.0, False
    planned = sum(record.planned_qty for record in records)
    actual = sum(record.actual_qty for record in records)
    if planned <= 0:
        return 0.0, False
    return percentage(actual, planned), True


def _planned_progress_pct(activity: Activity, as_of: date) -> float:
    if activity.es_date is None or activity.ef_date is None:
        return 0.0
    if as_of < activity.es_date:
        return 0.0
    if as_of >= activity.ef_date:
        return 100.0
    total_days = max((activity.ef_date - activity.es_date).days, 1)
    elapsed_days = max((as_of - activity.es_date).days, 0)
    return round((elapsed_days / total_days) * 100, 2)


def _evm_totals(rows: list[dict[str, Any]]) -> dict[str, object]:
    totals = calculate_evm_totals(rows)
    return {
        "pv": totals["planned_value"],
        "ev": totals["earned_value"],
        "ac": totals["actual_cost"],
        "sv": totals["schedule_variance"],
        "cv": totals["cost_variance"],
        "spi": totals["spi"],
        "cpi": totals["cpi"],
        "status": totals["status"],
    }


def _activity_date_bounds(activities: list[Activity]) -> tuple[date | None, date | None]:
    starts = [activity.es_date for activity in activities if activity.es_date is not None]
    finishes = [activity.ef_date for activity in activities if activity.ef_date is not None]
    return (min(starts) if starts else None, max(finishes) if finishes else None)


def _date_range(start: date, end: date):
    current = start
    while current <= end:
        yield current
        current += timedelta(days=1)


def _parse_date(value: str | None) -> date | None:
    if value is None or not str(value).strip():
        return None
    return date.fromisoformat(str(value))


# ---------------------------------------------------------------------------
# Budget variance tools (v2.6)
# ---------------------------------------------------------------------------


def analyze_budget_variance(
    db_path: str,
    *,
    discipline: str | None = None,
    as_of_date: str | None = None,
) -> dict[str, object]:
    """Analyze budget vs actual cost variance with status classification.

    Parameters
    ----------
    db_path : path to the .scheduler file
    discipline : 공종 필터 (optional)
    as_of_date : 기준일 (YYYY-MM-DD), 미지정 시 오늘

    Returns per-activity variance (절감/정상/초과/위험), discipline rollup, overall summary.
    Status thresholds: 절감(>+5%), 정상(±5%), 초과(-5%~-15%), 위험(<-15%)
    """
    parsed_date = _parse_date(as_of_date)
    return _analyze_budget_variance(
        db_path,
        discipline=discipline,
        as_of_date=parsed_date,
    )


def forecast_cost_scenarios(
    db_path: str,
    *,
    discipline: str | None = None,
    optimistic_factor: float = 0.95,
    pessimistic_factor: float = 1.15,
) -> dict[str, object]:
    """Generate three EAC (Estimate At Completion) forecast scenarios.

    Parameters
    ----------
    db_path : path to the .scheduler file
    discipline : 공종 필터 (optional)
    optimistic_factor : 낙관 시나리오 배율 (기본 0.95 = 5% 절감)
    pessimistic_factor : 비관 시나리오 배율 (기본 1.15 = 15% 증가)

    Returns 낙관/현실/비관 3개 시나리오의 예상 준공원가.
    """
    return _forecast_scenarios(
        db_path,
        discipline=discipline,
        optimistic_factor=optimistic_factor,
        pessimistic_factor=pessimistic_factor,
    )
