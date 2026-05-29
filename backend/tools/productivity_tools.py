"""MCP tools for labor productivity analysis.

Provides productivity analysis by activity/discipline and trend tracking.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from core.productivity import (
    analyze_activity_productivity,
    analyze_productivity_summary,
    get_productivity_trend as _get_trend,
)


def analyze_productivity(
    db_path: str,
    *,
    activity_id: str | None = None,
    discipline: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Analyze labor productivity from daily records.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : 특정 활동 분석 (지정 시 해당 활동만)
    discipline : 공종 필터 (activity_id 미지정 시 사용)
    start_date / end_date : 분석 기간 (YYYY-MM-DD)

    Returns productivity index (생산성 지수), status (우수/정상/부진/위험),
    output per worker, and discipline breakdown.
    """
    if activity_id:
        return analyze_activity_productivity(
            db_path, activity_id,
            start_date=_parse_date(start_date),
            end_date=_parse_date(end_date),
        )
    return analyze_productivity_summary(
        db_path,
        discipline=discipline,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )


def get_productivity_trend(
    db_path: str,
    activity_id: str,
    *,
    periods: int = 7,
) -> dict[str, Any]:
    """Get daily productivity trend for an activity.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : 대상 활동 ID
    periods : 최근 N일간 추세 (기본 7일)

    Returns daily productivity data points and trend direction (개선/유지/하락).
    """
    return _get_trend(db_path, activity_id, periods=periods)


def _parse_date(value: str | None) -> date | None:
    if value and value.strip():
        return date.fromisoformat(value.strip())
    return None
