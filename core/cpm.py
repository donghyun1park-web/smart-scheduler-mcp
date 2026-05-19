from __future__ import annotations

from pathlib import Path

from core.models import Activity, ActivityCpmResult, CpmResult, Project, Relationship


def calculate_cpm(project_path: str | Path) -> dict[str, object]:
    """Run CPM for a SQLite project and return JSON-serializable data."""
    return run_cpm_for_project(project_path).to_dict()


def run_cpm_for_project(project_path: str | Path) -> CpmResult:
    from core import db
    from core.calendar_utils import KoreanCalendar, map_activity_dates

    activities = db.list_activities(project_path)
    relationships = db.list_relationships(project_path)
    result = run_cpm(activities, relationships)
    if not result.cycles_detected:
        summary = db.load_project_summary(project_path)
        project = summary["project"]
        if isinstance(project, Project):
            calendar_model = db.get_calendar(project_path, project.calendar_id)
            if calendar_model is not None:
                calendar = KoreanCalendar(calendar_model)
                duration_by_id = {
                    activity.activity_id: activity.duration for activity in activities
                }
                mapped = [
                    map_activity_dates(
                        activity_result,
                        project.start_date,
                        calendar,
                        duration=duration_by_id[activity_result.activity_id],
                    )
                    for activity_result in result.activities
                ]
                result = CpmResult(
                    activities=mapped,
                    total_duration_days=result.total_duration_days,
                    critical_count=result.critical_count,
                    completion_date=max(
                        (activity.ef_date for activity in mapped if activity.ef_date),
                        default=None,
                    ),
                    cycles_detected=result.cycles_detected,
                )
        db.update_cpm_results(project_path, result.activities)
    return result


def run_cpm(activities: list[Activity], relationships: list[Relationship]) -> CpmResult:
    activity_by_id = {activity.activity_id: activity for activity in activities}
    predecessor_map: dict[str, list[tuple[str, str, int]]] = {
        activity.activity_id: [] for activity in activities
    }
    for relationship in relationships:
        if relationship.pred_id not in activity_by_id:
            raise ValueError(f"Missing predecessor activity: {relationship.pred_id}")
        if relationship.succ_id not in activity_by_id:
            raise ValueError(f"Missing successor activity: {relationship.succ_id}")
        predecessor_map[relationship.succ_id].append(
            (relationship.pred_id, relationship.rel_type, relationship.lag_days)
        )

    dataset = [
        (activity.activity_id, predecessor_map[activity.activity_id], activity.duration)
        for activity in activities
    ]

    from core.cpm_pycritical import calculate_with_pycritical

    pycritical_result = calculate_with_pycritical(dataset)
    if pycritical_result.cycles_detected:
        return CpmResult(
            activities=[],
            total_duration_days=0,
            critical_count=0,
            cycles_detected=pycritical_result.cycles_detected,
        )
    if pycritical_result.table is None:
        raise RuntimeError("pyCritical returned no CPM table without cycle details")

    results = [
        _activity_result(activity, pycritical_result.table.loc[activity.activity_id])
        for activity in activities
    ]
    total_duration = max((result.ef_workday for result in results), default=0)
    critical_count = sum(1 for result in results if result.is_critical)
    return CpmResult(
        activities=results,
        total_duration_days=total_duration,
        critical_count=critical_count,
        cycles_detected=[],
    )


def _activity_result(activity: Activity, row) -> ActivityCpmResult:
    total_float = int(round(float(row["Slack"])))
    return ActivityCpmResult(
        activity_id=activity.activity_id,
        code=activity.code,
        es_workday=int(round(float(row["ES"]))),
        ef_workday=int(round(float(row["EF"]))),
        ls_workday=int(round(float(row["LS"]))),
        lf_workday=int(round(float(row["LF"]))),
        total_float=total_float,
        is_critical=total_float == 0,
    )
