from __future__ import annotations

import dataclasses
from pathlib import Path

from core import db
from core.models import Activity, NotificationLog


def update_activity_status(
    db_path: str | Path,
    activity_id: str,
    new_status: str,
    delayed_days: int = 0,
) -> None:
    """Updates an activity's status and dispatches event-driven notifications if applicable."""
    activities = db.list_activities(db_path)
    activity_map = {a.activity_id: a for a in activities}

    if activity_id not in activity_map:
        return

    activity = activity_map[activity_id]
    old_status = activity.status

    if old_status == new_status and delayed_days == 0:
        return

    updated_activity = dataclasses.replace(activity, status=new_status)
    if delayed_days > 0 and new_status == "DELAYED":
        updated_activity = dataclasses.replace(
            updated_activity, duration=activity.duration + delayed_days
        )

    db.update_activity(db_path, updated_activity)

    if delayed_days > 0 and new_status == "DELAYED":
        from core.cpm import run_cpm_for_project
        run_cpm_for_project(db_path)
        
        # Reload activity_map to get updated dates
        activities = db.list_activities(db_path)
        activity_map = {a.activity_id: a for a in activities}
        updated_activity = activity_map[activity_id]

    if new_status in ("DONE", "DELAYED"):
        _dispatch_notifications(db_path, updated_activity, activity_map, delayed_days)


def _dispatch_notifications(
    db_path: str | Path,
    trigger_activity: Activity,
    activity_map: dict[str, Activity],
    delayed_days: int,
) -> None:
    relationships = db.list_relationships(db_path)

    for rel in relationships:
        if rel.pred_id == trigger_activity.activity_id:
            successor = activity_map.get(rel.succ_id)
            if not successor:
                continue

            if trigger_activity.status == "DONE":
                msg = f"✅ [작업가능 알림] {trigger_activity.name} 작업이 방금 완료되었습니다. 다음 공정({successor.discipline})인 {successor.name} 착수가 가능합니다."
                log = NotificationLog(
                    log_id=0,
                    activity_id=trigger_activity.activity_id,
                    target_role=successor.discipline,
                    notification_type="READY",
                    message=msg,
                )
                db.create_notification_log(db_path, log)

            elif trigger_activity.status == "DELAYED":
                new_date = successor.es_date.isoformat() if successor.es_date else "미정"
                msg = f"⚠️ [일정연기] 선행 공정 '{trigger_activity.name}' {delayed_days}일 지연으로, '{successor.name}' 일정이 {new_date}로 자동 연기되었습니다."
                log = NotificationLog(
                    log_id=0,
                    activity_id=trigger_activity.activity_id,
                    target_role=successor.discipline,
                    notification_type="DELAYED",
                    message=msg,
                )
                db.create_notification_log(db_path, log)
