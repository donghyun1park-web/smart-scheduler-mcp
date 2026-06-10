from __future__ import annotations

from datetime import date
from typing import Mapping, cast

from core.data_health import check_data_health as check_data_health_core
from core.evm_explain import explain_evm_totals_ko
from core.next_actions import UserProfile, suggest_next_actions as suggest_next_actions_core
from core.workflows import get_daily_close_status, get_weekly_report_precheck_status
from tools.cost_tools import analyze_evm_from_db


def check_data_health(
    db_path: str,
    project_id: str | None = None,
    as_of: str | None = None,
    max_issues: int = 50,
) -> dict[str, object]:
    report = check_data_health_core(
        db_path,
        project_id=project_id,
        as_of=_parse_date(as_of),
        max_issues=max_issues,
    )
    return {"ok": True, **report.to_dict()}


def suggest_next_actions(
    db_path: str,
    profile: str = "field_admin",
    as_of: str | None = None,
    limit: int = 5,
) -> dict[str, object]:
    actions = suggest_next_actions_core(
        db_path,
        profile=_profile(profile),
        as_of=_parse_date(as_of),
        limit=limit,
    )
    return {"ok": True, "profile": profile, "actions": [action.to_dict() for action in actions]}


def explain_evm_from_db(
    db_path: str,
    *,
    project_id: str | None = None,
    as_of: str | None = None,
    discipline: str | None = None,
    zone: str | None = None,
) -> dict[str, object]:
    evm = analyze_evm_from_db(
        db_path,
        project_id=project_id,
        as_of_date=as_of,
        discipline=discipline,
        zone=zone,
    )
    totals = cast(Mapping[str, object], evm.get("totals", {}))
    explanation = explain_evm_totals_ko(totals)
    return {"ok": True, "evm": evm, "explanation": explanation}


def get_workflow_status(
    db_path: str,
    *,
    as_of: str | None = None,
) -> dict[str, object]:
    as_of_date = _parse_date(as_of)
    daily = get_daily_close_status(db_path, as_of=as_of_date)
    weekly = get_weekly_report_precheck_status(db_path, as_of=as_of_date)
    return {
        "ok": True,
        "daily_close": daily.to_dict(),
        "weekly_report_precheck": weekly.to_dict(),
    }


def _parse_date(value: str | None) -> date | None:
    if value is None or not str(value).strip():
        return None
    return date.fromisoformat(value)


def _profile(value: str) -> UserProfile:
    if value in {"field_admin", "site_manager", "hq", "developer"}:
        return cast(UserProfile, value)
    return "field_admin"
