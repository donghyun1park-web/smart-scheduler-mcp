"""MCP tools for schedule delay analysis.

Provides delay event recording, listing, analysis reports,
and time extension claim calculation.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from core.delay_analysis import (
    calculate_time_extension_entitlement,
    generate_delay_analysis,
    list_delay_events_from_db,
    record_delay_event_to_db,
)


def record_delay_event(
    db_path: str,
    activity_id: str,
    delay_type: str,
    cause_code: str,
    *,
    responsible_party: str = "",
    start_date: str | None = None,
    end_date: str | None = None,
    delay_days: int = 0,
    cost_impact: float = 0.0,
    description: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Record a classified delay event for an activity.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : 지연이 발생한 활동 ID
    delay_type : 지연 유형 — 'excusable_compensable'(면책보상가능),
                 'excusable_non_compensable'(면책보상불가),
                 'non_excusable'(비면책), 'concurrent'(동시지연)
    cause_code : 지연 원인 — 'owner_change', 'design_error', 'weather',
                 'material_delay', 'labor_shortage', 'permit_delay',
                 'site_condition', 'subcontractor', 'other'
    responsible_party : 책임 주체
    start_date / end_date : 지연 기간 (YYYY-MM-DD)
    delay_days : 지연 일수 (0이면 날짜에서 자동 계산)
    cost_impact : 비용 영향 (원)
    description : 설명
    dry_run : True면 검증만, False면 DB 저장
    """
    return record_delay_event_to_db(
        db_path, activity_id, delay_type, cause_code,
        responsible_party=responsible_party,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
        delay_days=delay_days,
        cost_impact=cost_impact,
        description=description,
        dry_run=dry_run,
    )


def list_delay_events_tool(
    db_path: str,
    *,
    activity_id: str | None = None,
    delay_type: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List recorded delay events with optional filters.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : 활동 ID 필터
    delay_type : 지연 유형 필터
    status : 상태 필터 ('open', 'resolved', 'claimed')
    """
    return list_delay_events_from_db(
        db_path,
        activity_id=activity_id,
        delay_type=delay_type,
        status=status,
    )


def analyze_delays(
    db_path: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Generate comprehensive delay analysis report.

    Parameters
    ----------
    db_path : path to the .scheduler file
    start_date / end_date : 분석 기간 필터 (YYYY-MM-DD)

    Returns total delay days, cost impact, breakdown by type and cause.
    """
    return generate_delay_analysis(
        db_path,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )


def calculate_time_extension_claim(
    db_path: str,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """Calculate time extension claim entitlement from excusable delays.

    Parameters
    ----------
    db_path : path to the .scheduler file
    start_date / end_date : 대상 기간 (YYYY-MM-DD)

    Returns recommended extension days, compensable cost, breakdown by delay type.
    면책 지연만 공기연장 대상이며, 면책보상가능 지연은 비용 보상도 포함.
    """
    return calculate_time_extension_entitlement(
        db_path,
        start_date=_parse_date(start_date),
        end_date=_parse_date(end_date),
    )


def _parse_date(value: str | None) -> date | None:
    if value and value.strip():
        return date.fromisoformat(value.strip())
    return None
