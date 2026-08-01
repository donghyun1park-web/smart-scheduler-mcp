from __future__ import annotations

from datetime import date
from typing import Any, Iterable, Mapping

from core.number_utils import to_float


Issue = dict[str, Any]


def detect_schedule_delay(activity: Mapping[str, Any], threshold_pct: float = 3.0) -> list[Issue]:
    planned = to_float(activity.get("planned_progress_pct"))
    actual = to_float(activity.get("actual_progress_pct"))
    gap = round(planned - actual, 2)
    if gap <= threshold_pct:
        return []
    return [
        _issue(
            activity,
            reason_code="schedule_progress_delay",
            severity=_severity_from_gap(gap),
            delay_days=0,
            message=(
                f"{_activity_name(activity)} progress delay: planned {planned:.1f}%, "
                f"actual {actual:.1f}%, gap {gap:.1f}%."
            ),
            risk_score=gap,
        )
    ]


def detect_overdue_activity(activity: Mapping[str, Any], *, today: date | None = None) -> list[Issue]:
    today = today or date.today()
    finish_date = _date_value(activity.get("finish_date"))
    status = str(activity.get("status") or "").lower()
    if finish_date is None or finish_date >= today or status in {"completed", "complete", "done"}:
        return []
    delay_days = (today - finish_date).days
    return [
        _issue(
            activity,
            reason_code="finish_overdue",
            severity=_severity_from_days(delay_days),
            delay_days=delay_days,
            message=f"{_activity_name(activity)} is overdue: finish {finish_date.isoformat()}, today {today.isoformat()}.",
            risk_score=delay_days * 2,
        )
    ]


def detect_predecessor_blocks(activity: Mapping[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    for predecessor in _list_value(activity.get("predecessors")):
        pred = _mapping_value(predecessor)
        status = str(pred.get("status") or "").lower()
        if status not in {"completed", "complete", "done"}:
            pred_name = str(pred.get("name") or pred.get("activity_id") or "unknown predecessor")
            issues.append(
                _issue(
                    activity,
                    reason_code="predecessor_incomplete",
                    severity="warning",
                    delay_days=0,
                    message=f"{_activity_name(activity)} is blocked by incomplete predecessor {pred_name}.",
                    risk_score=8.0,
                )
            )
    return issues


def detect_material_delays(activity: Mapping[str, Any], *, today: date | None = None) -> list[Issue]:
    today = today or date.today()
    issues: list[Issue] = []
    for material in _list_value(activity.get("materials")):
        row = _mapping_value(material)
        status = str(row.get("status") or "").lower()
        actual_date = _date_value(row.get("actual_date"))
        expected_date = _date_value(row.get("expected_date"))
        if actual_date is None and expected_date is not None and expected_date < today and status not in {"arrived", "delivered"}:
            delay_days = (today - expected_date).days
            material_name = str(row.get("material_name") or "material")
            issues.append(
                _issue(
                    activity,
                    reason_code="material_delay",
                    severity=_severity_from_days(delay_days),
                    delay_days=delay_days,
                    message=(
                        f"{_activity_name(activity)} material delay: {material_name}, "
                        f"expected {expected_date.isoformat()}, no actual receipt."
                    ),
                    risk_score=delay_days * 2 + 5,
                )
            )
    return issues


def detect_inspection_delays(activity: Mapping[str, Any], *, today: date | None = None) -> list[Issue]:
    today = today or date.today()
    issues: list[Issue] = []
    for inspection in _list_value(activity.get("inspections")):
        row = _mapping_value(inspection)
        status = str(row.get("status") or "").lower()
        actual_date = _date_value(row.get("actual_date"))
        planned_date = _date_value(row.get("planned_date"))
        if actual_date is None and planned_date is not None and planned_date < today and status not in {"approved", "passed"}:
            delay_days = (today - planned_date).days
            inspection_type = str(row.get("inspection_type") or "inspection")
            issues.append(
                _issue(
                    activity,
                    reason_code="inspection_delay",
                    severity=_severity_from_days(delay_days),
                    delay_days=delay_days,
                    message=(
                        f"{_activity_name(activity)} inspection delay: {inspection_type}, "
                        f"planned {planned_date.isoformat()}, no approval date."
                    ),
                    risk_score=delay_days * 2 + 4,
                )
            )
    return issues


def detect_manpower_shortage(activity: Mapping[str, Any]) -> list[Issue]:
    planned = to_float(activity.get("planned_workers"))
    actual = to_float(activity.get("actual_workers"))
    if planned <= 0 or actual >= planned:
        return []
    shortage = planned - actual
    return [
        _issue(
            activity,
            reason_code="manpower_shortage",
            severity="warning",
            delay_days=0,
            message=f"{_activity_name(activity)} manpower shortage: planned {planned:.0f}, actual {actual:.0f}.",
            risk_score=shortage,
        )
    ]


def generate_delay_report(
    activities: Iterable[Mapping[str, Any]],
    *,
    today: date | None = None,
    top_n: int = 10,
) -> list[Issue]:
    issues: list[Issue] = []
    for activity in activities:
        issues.extend(detect_schedule_delay(activity))
        issues.extend(detect_overdue_activity(activity, today=today))
        issues.extend(detect_predecessor_blocks(activity))
        issues.extend(detect_material_delays(activity, today=today))
        issues.extend(detect_inspection_delays(activity, today=today))
        issues.extend(detect_manpower_shortage(activity))
    issues.sort(key=lambda issue: (-to_float(issue.get("risk_score")), str(issue.get("activity_id"))))
    return issues[:top_n]


def _issue(
    activity: Mapping[str, Any],
    *,
    reason_code: str,
    severity: str,
    delay_days: int,
    message: str,
    risk_score: float,
) -> Issue:
    return {
        "activity_id": activity.get("activity_id"),
        "activity_name": _activity_name(activity),
        "owner": activity.get("owner") or "",
        "reason_code": reason_code,
        "severity": severity,
        "delay_days": delay_days,
        "message": message,
        "risk_score": round(risk_score, 2),
    }


def _activity_name(activity: Mapping[str, Any]) -> str:
    return str(activity.get("name") or activity.get("activity_name") or activity.get("activity_id") or "activity")


def _severity_from_gap(gap: float) -> str:
    if gap > 15:
        return "critical"
    if gap > 7:
        return "danger"
    return "warning"


def _severity_from_days(days: int) -> str:
    if days > 14:
        return "critical"
    if days > 7:
        return "danger"
    return "warning"


def _date_value(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))


def _list_value(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _mapping_value(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
