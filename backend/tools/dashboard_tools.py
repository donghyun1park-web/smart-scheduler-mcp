"""MCP tools for site manager dashboard."""
from __future__ import annotations

from typing import Any

from core.dashboard import (
    generate_dashboard_markdown,
    generate_site_briefing,
    get_delayed_with_recovery,
    get_progress_by_discipline,
)


def get_site_briefing(
    db_path: str,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Get a concise one-line site status briefing.

    Returns overall progress, billing rate, and delayed activity count
    with a Korean status summary sentence.

    Parameters
    ----------
    db_path : path to the .scheduler file
    as_of : reference date (YYYY-MM-DD), defaults to today
    """
    from datetime import date as d
    as_of_date = d.fromisoformat(as_of) if as_of else None
    return generate_site_briefing(db_path, as_of=as_of_date)


def get_dashboard_report(
    db_path: str,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Generate a comprehensive Markdown dashboard report.

    Includes: status summary, discipline-level progress, billing status,
    delayed activities with recovery suggestions.

    Parameters
    ----------
    db_path : path to the .scheduler file
    as_of : reference date (YYYY-MM-DD), defaults to today
    """
    from datetime import date as d
    as_of_date = d.fromisoformat(as_of) if as_of else None
    return generate_dashboard_markdown(db_path, as_of=as_of_date)


def get_discipline_progress(
    db_path: str,
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """Return progress metrics grouped by discipline.

    Shows planned vs actual progress, billing rate, and delayed count
    per discipline.

    Parameters
    ----------
    db_path : path to the .scheduler file
    as_of : reference date (YYYY-MM-DD), defaults to today
    """
    from datetime import date as d
    as_of_date = d.fromisoformat(as_of) if as_of else None
    return get_progress_by_discipline(db_path, as_of=as_of_date)


def get_delayed_activities(
    db_path: str,
    *,
    as_of: str | None = None,
    threshold_pct: float = 5.0,
    top_n: int = 10,
) -> dict[str, Any]:
    """Return delayed activities with auto-generated recovery suggestions.

    Activities where (planned - actual) > threshold_pct are flagged.

    Parameters
    ----------
    db_path : path to the .scheduler file
    as_of : reference date (YYYY-MM-DD), defaults to today
    threshold_pct : minimum gap to flag as delayed (default 5.0%)
    top_n : max delayed activities to return (default 10)
    """
    from datetime import date as d
    as_of_date = d.fromisoformat(as_of) if as_of else None
    return get_delayed_with_recovery(
        db_path, as_of=as_of_date, threshold_pct=threshold_pct, top_n=top_n,
    )


def get_site_alerts(
    db_path: str = "",
    *,
    as_of: str | None = None,
) -> dict[str, Any]:
    """현장의 조치 필요 경고를 스캔합니다.

    자재 납기 초과, 승인 대기/미반영 변경지시, 공정 부진 등을
    🔴 위험 / 🟡 주의 수준으로 정리해 반환합니다.

    Parameters
    ----------
    db_path : .scheduler 파일 경로 (생략 시 활성 프로젝트 사용)
    as_of : 기준일 (YYYY-MM-DD), 기본값 오늘
    """
    from datetime import date as d
    from core.alerts import scan_alerts
    from core.context import resolve_db_path

    as_of_date = d.fromisoformat(as_of) if as_of else None
    return scan_alerts(resolve_db_path(db_path), as_of=as_of_date)
