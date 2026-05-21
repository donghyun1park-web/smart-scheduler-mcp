"""Site manager dashboard — comprehensive site status at a glance.

Provides:
- One-line site briefing (overall status)
- Progress breakdown by discipline with delay warnings
- Markdown dashboard report for AI-assisted briefings
- Auto-generated recovery suggestions for delayed activities
"""
from __future__ import annotations

from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.billing import get_billing_summary
from core.models import Activity
from core.number_utils import percentage
from core.progress import get_today_schedule_summary
from core.recovery import suggest_recovery_plans


# ---------------------------------------------------------------------------
# Site briefing (one-liner)
# ---------------------------------------------------------------------------


def generate_site_briefing(
    db_path: str | Path,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Generate a concise site status briefing.

    Returns key metrics and a single-sentence Korean status summary.
    """
    today = as_of or date.today()
    activities = db.list_activities(db_path)
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}
    project_info = db.load_project_summary(db_path)
    project = project_info.get("project")

    # Progress metrics
    total_planned = 0.0
    total_actual = 0.0
    total_weight = 0.0
    delayed_activities: list[dict[str, Any]] = []

    for act in activities:
        cost = cost_map.get(act.activity_id)
        weight = cost.execution_budget if cost else 0.0
        planned_pct = _time_progress(act, today)
        actual_pct = _actual_or_time_progress(db_path, act, today)

        total_planned += planned_pct * weight
        total_actual += actual_pct * weight
        total_weight += weight

        if planned_pct > 0 and (planned_pct - actual_pct) > 5.0:
            delayed_activities.append({
                "activity_id": act.activity_id,
                "name": act.name,
                "discipline": act.discipline,
                "planned_pct": round(planned_pct, 1),
                "actual_pct": round(actual_pct, 1),
                "gap_pct": round(planned_pct - actual_pct, 1),
            })

    overall_planned = round(total_planned / total_weight, 2) if total_weight > 0 else 0.0
    overall_actual = round(total_actual / total_weight, 2) if total_weight > 0 else 0.0
    gap = round(overall_actual - overall_planned, 2)

    # Cost metrics
    billing_info = get_billing_summary(db_path)
    billing_rate = billing_info.get("overall_billing_rate_pct", 0.0)

    # Status determination
    if gap >= 0:
        status = "정상"
        status_emoji = "green"
    elif gap >= -3:
        status = "주의"
        status_emoji = "yellow"
    else:
        status = "부진"
        status_emoji = "red"

    # Today's schedule (planned starts/finishes + overdue starts)
    today_schedule = get_today_schedule_summary(db_path, as_of=today)

    # One-liner
    project_name = getattr(project, "name", "프로젝트") if project else "프로젝트"
    briefing = (
        f"[{status}] {project_name} — "
        f"계획 {overall_planned:.1f}% / 실적 {overall_actual:.1f}% "
        f"(차이 {gap:+.1f}%p), "
        f"기성률 {billing_rate:.1f}%, "
        f"부진공정 {len(delayed_activities)}건, "
        f"오늘 착수 {today_schedule['starts_today_count']}건 / "
        f"완료 예정 {today_schedule['finishes_today_count']}건"
        + (f", 미착수 지연 {today_schedule['overdue_start_count']}건"
           if today_schedule['overdue_start_count'] else "")
    )

    return {
        "ok": True,
        "as_of": today.isoformat(),
        "project_name": project_name,
        "status": status,
        "status_level": status_emoji,
        "overall_planned_pct": overall_planned,
        "overall_actual_pct": overall_actual,
        "progress_gap_pct": gap,
        "billing_rate_pct": billing_rate,
        "activity_count": len(activities),
        "delayed_count": len(delayed_activities),
        "today_schedule": today_schedule,
        "briefing": briefing,
    }


# ---------------------------------------------------------------------------
# Progress by discipline
# ---------------------------------------------------------------------------


def get_progress_by_discipline(
    db_path: str | Path,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Return progress metrics grouped by discipline."""
    today = as_of or date.today()
    activities = db.list_activities(db_path)
    cost_map = {c.activity_id: c for c in db.list_cost_items(db_path)}

    disc_data: dict[str, dict[str, Any]] = defaultdict(
        lambda: {
            "planned_weighted": 0.0,
            "actual_weighted": 0.0,
            "total_weight": 0.0,
            "contract": 0.0,
            "execution": 0.0,
            "billing": 0.0,
            "invested": 0.0,
            "count": 0,
            "delayed": 0,
        }
    )

    for act in activities:
        cost = cost_map.get(act.activity_id)
        d = disc_data[act.discipline]
        weight = cost.execution_budget if cost else 0.0
        planned = _time_progress(act, today)
        actual = _actual_or_time_progress(db_path, act, today)

        d["planned_weighted"] += planned * weight
        d["actual_weighted"] += actual * weight
        d["total_weight"] += weight
        d["count"] += 1

        if cost:
            d["contract"] += cost.contract_amount
            d["execution"] += cost.execution_budget
            d["billing"] += cost.billing_amount
            d["invested"] += cost.invested_cost

        if planned > 0 and (planned - actual) > 5.0:
            d["delayed"] += 1

    rows: list[dict[str, Any]] = []
    for disc in sorted(disc_data.keys()):
        d = disc_data[disc]
        w = d["total_weight"]
        planned_pct = round(d["planned_weighted"] / w, 2) if w > 0 else 0.0
        actual_pct = round(d["actual_weighted"] / w, 2) if w > 0 else 0.0
        rows.append({
            "discipline": disc,
            "activity_count": d["count"],
            "planned_pct": planned_pct,
            "actual_pct": actual_pct,
            "gap_pct": round(actual_pct - planned_pct, 2),
            "contract_amount": round(d["contract"], 0),
            "execution_budget": round(d["execution"], 0),
            "billing_amount": round(d["billing"], 0),
            "billing_rate_pct": round(percentage(d["billing"], d["contract"]), 2),
            "delayed_count": d["delayed"],
        })

    return {"ok": True, "as_of": today.isoformat(), "rows": rows}


# ---------------------------------------------------------------------------
# Delayed activities with recovery suggestions
# ---------------------------------------------------------------------------


def get_delayed_with_recovery(
    db_path: str | Path,
    *,
    as_of: date | None = None,
    threshold_pct: float = 5.0,
    top_n: int = 10,
) -> dict[str, Any]:
    """Return delayed activities with auto-generated recovery suggestions."""
    today = as_of or date.today()
    activities = db.list_activities(db_path)

    delayed: list[dict[str, Any]] = []
    for act in activities:
        planned = _time_progress(act, today)
        actual = _actual_or_time_progress(db_path, act, today)
        gap = planned - actual

        if gap <= threshold_pct:
            continue

        # Determine delay reason
        reason_code = _infer_delay_reason(act, gap, today)
        plans = suggest_recovery_plans(reason_code)

        delayed.append({
            "activity_id": act.activity_id,
            "code": act.code,
            "name": act.name,
            "discipline": act.discipline,
            "planned_pct": round(planned, 1),
            "actual_pct": round(actual, 1),
            "gap_pct": round(gap, 1),
            "reason_code": reason_code,
            "recovery_suggestions": [
                {"title": p["title"], "description": p.get("description", "")}
                for p in plans[:3]
            ],
        })

    delayed.sort(key=lambda x: -x["gap_pct"])
    return {
        "ok": True,
        "as_of": today.isoformat(),
        "delayed_count": len(delayed),
        "rows": delayed[:top_n],
    }


# ---------------------------------------------------------------------------
# Markdown dashboard report
# ---------------------------------------------------------------------------


def generate_dashboard_markdown(
    db_path: str | Path,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Generate a comprehensive Markdown dashboard report."""
    today = as_of or date.today()

    briefing = generate_site_briefing(db_path, as_of=today)
    progress = get_progress_by_discipline(db_path, as_of=today)
    delayed = get_delayed_with_recovery(db_path, as_of=today, top_n=5)
    billing = get_billing_summary(db_path)

    lines: list[str] = []
    lines.append(f"# {briefing['project_name']} 현장 현황")
    lines.append(f"**기준일**: {today.isoformat()}")
    lines.append("")

    # Status summary
    lines.append("## 종합 현황")
    lines.append(f"- **상태**: {briefing['status']}")
    lines.append(f"- **계획 공정률**: {briefing['overall_planned_pct']:.1f}%")
    lines.append(f"- **실적 공정률**: {briefing['overall_actual_pct']:.1f}%")
    lines.append(f"- **공정 차이**: {briefing['progress_gap_pct']:+.1f}%p")
    lines.append(f"- **기성률**: {briefing['billing_rate_pct']:.1f}%")
    lines.append(f"- **부진공정**: {briefing['delayed_count']}건")
    lines.append("")

    # Discipline breakdown
    lines.append("## 공종별 공정률")
    lines.append("| 공종 | 활동수 | 계획(%) | 실적(%) | 차이(%p) | 기성률(%) | 부진 |")
    lines.append("|------|--------|---------|---------|----------|-----------|------|")
    for row in progress.get("rows", []):
        lines.append(
            f"| {row['discipline']} | {row['activity_count']} | "
            f"{row['planned_pct']:.1f} | {row['actual_pct']:.1f} | "
            f"{row['gap_pct']:+.1f} | {row['billing_rate_pct']:.1f} | "
            f"{row['delayed_count']} |"
        )
    lines.append("")

    # Billing summary
    lines.append("## 기성 현황")
    b_rows = billing.get("rows", [])
    if b_rows:
        lines.append("| 공종 | 도급액 | 실행예산 | 기성액 | 기성률(%) |")
        lines.append("|------|--------|----------|--------|-----------|")
        for row in b_rows:
            lines.append(
                f"| {row['discipline']} | {row['contract_amount']:,.0f} | "
                f"{row['execution_budget']:,.0f} | {row['billing_amount']:,.0f} | "
                f"{row['billing_rate_pct']:.1f} |"
            )
    lines.append("")

    # Delayed activities
    d_rows = delayed.get("rows", [])
    if d_rows:
        lines.append("## 부진공정 TOP 5")
        for i, d in enumerate(d_rows, 1):
            lines.append(f"### {i}. {d['name']} ({d['discipline']})")
            lines.append(f"- 계획 {d['planned_pct']:.1f}% → 실적 {d['actual_pct']:.1f}% (부진 {d['gap_pct']:.1f}%p)")
            lines.append(f"- 원인: {d['reason_code']}")
            if d["recovery_suggestions"]:
                lines.append("- 만회대책:")
                for s in d["recovery_suggestions"]:
                    lines.append(f"  - {s['title']}")
            lines.append("")

    md_content = "\n".join(lines)
    return {
        "ok": True,
        "as_of": today.isoformat(),
        "markdown": md_content,
        "briefing": briefing["briefing"],
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _time_progress(activity: Activity, as_of: date) -> float:
    """Time-based linear progress percentage."""
    if activity.es_date is None or activity.ef_date is None:
        return 0.0
    if as_of < activity.es_date:
        return 0.0
    if as_of >= activity.ef_date:
        return 100.0
    total = max((activity.ef_date - activity.es_date).days, 1)
    elapsed = (as_of - activity.es_date).days
    return round(elapsed / total * 100, 2)


def _actual_or_time_progress(db_path: str | Path, activity: Activity, as_of: date) -> float:
    """Return actual progress with the priority:

    1. Daily-record quantity sums (most precise)
    2. ``Activity.progress_pct`` manual entry (site-manager quick input)
    3. Time-based linear progress (fallback)
    """
    records = db.list_daily_records(db_path, activity_id=activity.activity_id, end_date=as_of)
    if records:
        planned = sum(r.planned_qty for r in records)
        actual = sum(r.actual_qty for r in records)
        if planned > 0:
            return min(percentage(actual, planned), 100.0)
    if activity.progress_pct > 0:
        return min(float(activity.progress_pct), 100.0)
    return _time_progress(activity, as_of)


def _infer_delay_reason(activity: Activity, gap_pct: float, today: date) -> str:
    """Infer a delay reason code from activity characteristics."""
    if gap_pct > 20:
        return "critical_delay"
    if activity.es_date and today > activity.es_date and gap_pct > 10:
        return "slow_progress"
    if activity.discipline in ("기계설비", "전기설비", "소방설비"):
        return "mep_coordination"
    return "general"
