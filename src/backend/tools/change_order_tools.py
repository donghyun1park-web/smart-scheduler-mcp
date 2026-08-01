"""MCP tool wrappers for change order management."""
from __future__ import annotations

from datetime import date
from typing import Any


def create_change_order(
    db_path: str,
    title: str,
    description: str = "",
    co_type: str = "scope_addition",
    requested_by: str = "",
    request_date: str = "",
    direct_cost: float = 0.0,
    markup_pct: float = 0.0,
    schedule_impact_days: int = 0,
    dry_run: bool = True,
) -> dict[str, Any]:
    """변경지시(CO) 생성.

    co_type: scope_addition(범위추가), design_change(설계변경),
             owner_directed(발주처지시), field_condition(현장조건변경),
             value_engineering(VE제안)
    dry_run=True이면 검증만 수행합니다.
    """
    from core.change_order import create_change_order_in_db

    req_date = date.fromisoformat(request_date) if request_date else None
    return create_change_order_in_db(
        db_path, title,
        description=description,
        co_type=co_type,
        requested_by=requested_by,
        request_date=req_date,
        direct_cost=direct_cost,
        markup_pct=markup_pct,
        schedule_impact_days=schedule_impact_days,
        dry_run=dry_run,
    )


def add_change_order_item(
    db_path: str,
    co_id: str,
    activity_id: str,
    cost_change: float = 0.0,
    duration_change: int = 0,
    description: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """변경지시에 세부항목 추가.

    활동별 원가 변동(cost_change)과 공기 변동(duration_change)을 기록합니다.
    dry_run=True이면 검증만 수행합니다.
    """
    from core.change_order import add_co_item_to_db

    return add_co_item_to_db(
        db_path, co_id, activity_id,
        cost_change=cost_change,
        duration_change=duration_change,
        description=description,
        dry_run=dry_run,
    )


def update_change_order_status(
    db_path: str,
    co_id: str,
    new_status: str,
    approved_by: str = "",
    approval_date: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """변경지시 상태 변경 (초안→검토중→승인/반려).

    new_status: draft(초안), pending(검토중), approved(승인), rejected(반려)
    dry_run=True이면 검증만 수행합니다.
    """
    from core.change_order import update_co_status_in_db

    appr_date = date.fromisoformat(approval_date) if approval_date else None
    return update_co_status_in_db(
        db_path, co_id, new_status,
        approved_by=approved_by,
        approval_date=appr_date,
        dry_run=dry_run,
    )


def list_change_orders_tool(
    db_path: str,
    status: str = "",
    co_type: str = "",
) -> dict[str, Any]:
    """변경지시 목록 조회.

    status, co_type으로 필터링 가능합니다.
    """
    from core.change_order import list_change_orders_from_db

    return list_change_orders_from_db(
        db_path,
        status=status or None,
        co_type=co_type or None,
    )


def get_change_order_impact(
    db_path: str,
    co_id: str,
) -> dict[str, Any]:
    """변경지시 원가/공기 영향 분석.

    헤더 정보와 세부항목별 원가·공기 변동을 집계합니다.
    """
    from core.change_order import calculate_co_impact

    return calculate_co_impact(db_path, co_id)


def get_change_order_summary(
    db_path: str,
) -> dict[str, Any]:
    """변경지시 전체 현황 요약.

    상태별·유형별 집계, 총 직접비, 총 마크업비, 총 공기영향을 반환합니다.
    """
    from core.change_order import get_co_summary

    return get_co_summary(db_path)


def apply_change_order(
    db_path: str,
    co_id: str,
    applied_by: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """승인된 변경지시를 activities·cost_items에 실반영합니다.

    반드시 status='approved' 상태의 CO에만 적용 가능합니다.
    각 세부항목의 공기 변동(duration_change)과 원가 변동(cost_change)이
    해당 activity와 cost_item에 직접 반영됩니다.

    dry_run=True(기본값)이면 변경 내용 미리보기만 반환합니다.
    실제 반영은 dry_run=False로 명시적으로 지정해야 합니다.
    """
    from core.change_order import apply_change_order_in_db

    return apply_change_order_in_db(
        db_path,
        co_id,
        applied_by=applied_by,
        dry_run=dry_run,
    )
