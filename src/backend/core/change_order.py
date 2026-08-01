"""Change Order management engine.

Provides creation, approval workflow, cost/schedule impact calculation,
and summary reporting for construction change orders.

Inspired by DDC Change Order Processor, adapted to function-based pattern.
"""
from __future__ import annotations

import uuid
from datetime import date
from pathlib import Path
from typing import Any

from dataclasses import replace

from core import db
from core.models import (
    CO_STATUSES,
    CO_STATUS_KR,
    CO_TYPE_KR,
    CO_TYPES,
    ChangeLogEntry,
    ChangeOrder,
    ChangeOrderItem,
)


# ---------------------------------------------------------------------------
# Create change order
# ---------------------------------------------------------------------------


def create_change_order_in_db(
    db_path: str | Path,
    title: str,
    *,
    description: str = "",
    co_type: str = "scope_addition",
    requested_by: str = "",
    request_date: date | None = None,
    direct_cost: float = 0.0,
    markup_pct: float = 0.0,
    schedule_impact_days: int = 0,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Create a new change order (draft status).

    Parameters
    ----------
    co_type : one of 'scope_addition', 'design_change', 'owner_directed',
              'field_condition', 'value_engineering'
    markup_pct : markup percentage applied to direct_cost (e.g. 10.0 = 10%)
    dry_run : if True, validates but does not persist
    """
    if co_type not in CO_TYPES:
        return {"ok": False, "error": f"유효하지 않은 CO 유형: {co_type}. 가능: {sorted(CO_TYPES)}"}

    total_cost = direct_cost * (1 + markup_pct / 100.0)
    co_id = f"co-{uuid.uuid4().hex[:8]}"

    co = ChangeOrder(
        co_id=co_id,
        title=title,
        description=description,
        co_type=co_type,
        status="draft",
        requested_by=requested_by,
        request_date=request_date,
        direct_cost=direct_cost,
        markup_pct=markup_pct,
        total_cost=round(total_cost, 0),
        schedule_impact_days=schedule_impact_days,
    )

    if not dry_run:
        db.create_change_order(db_path, co)

    return {
        "ok": True,
        "dry_run": dry_run,
        "co_id": co_id,
        "title": title,
        "co_type": co_type,
        "co_type_kr": CO_TYPE_KR.get(co_type, co_type),
        "status": "draft",
        "status_kr": CO_STATUS_KR["draft"],
        "direct_cost": direct_cost,
        "markup_pct": markup_pct,
        "total_cost": round(total_cost, 0),
        "schedule_impact_days": schedule_impact_days,
    }


# ---------------------------------------------------------------------------
# Add item to change order
# ---------------------------------------------------------------------------


def add_co_item_to_db(
    db_path: str | Path,
    co_id: str,
    activity_id: str,
    *,
    cost_change: float = 0.0,
    duration_change: int = 0,
    description: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """Add a line item to an existing change order."""
    co = db.get_change_order(db_path, co_id)
    if not co:
        return {"ok": False, "error": f"변경지시를 찾을 수 없습니다: {co_id}"}

    if co.status not in ("draft", "pending"):
        return {"ok": False, "error": f"수정 불가 상태: {CO_STATUS_KR.get(co.status, co.status)}"}

    # Verify activity exists
    activities = db.list_activities(db_path)
    act = next((a for a in activities if a.activity_id == activity_id), None)
    if not act:
        return {"ok": False, "error": f"활동을 찾을 수 없습니다: {activity_id}"}

    co_item_id = f"coi-{uuid.uuid4().hex[:8]}"
    item = ChangeOrderItem(
        co_item_id=co_item_id,
        co_id=co_id,
        activity_id=activity_id,
        cost_change=cost_change,
        duration_change=duration_change,
        description=description,
    )

    if not dry_run:
        db.create_change_order_item(db_path, item)

    return {
        "ok": True,
        "dry_run": dry_run,
        "co_item_id": co_item_id,
        "co_id": co_id,
        "activity_id": activity_id,
        "activity_name": act.name,
        "cost_change": cost_change,
        "duration_change": duration_change,
    }


# ---------------------------------------------------------------------------
# Update change order status
# ---------------------------------------------------------------------------


def update_co_status_in_db(
    db_path: str | Path,
    co_id: str,
    new_status: str,
    *,
    approved_by: str = "",
    approval_date: date | None = None,
    dry_run: bool = True,
) -> dict[str, Any]:
    """Update change order status (draft→pending→approved/rejected)."""
    if new_status not in CO_STATUSES:
        return {"ok": False, "error": f"유효하지 않은 상태: {new_status}. 가능: {sorted(CO_STATUSES)}"}

    co = db.get_change_order(db_path, co_id)
    if not co:
        return {"ok": False, "error": f"변경지시를 찾을 수 없습니다: {co_id}"}

    # Validate transitions
    valid_transitions: dict[str, set[str]] = {
        "draft": {"pending", "rejected"},
        "pending": {"approved", "rejected"},
        "approved": {"applied"},
        "applied": set(),
        "rejected": {"draft"},
    }
    if new_status not in valid_transitions.get(co.status, set()):
        return {
            "ok": False,
            "error": (
                f"'{CO_STATUS_KR.get(co.status, co.status)}'에서 "
                f"'{CO_STATUS_KR.get(new_status, new_status)}'(으)로 전환 불가"
            ),
        }

    if not dry_run:
        db.update_change_order_status(
            db_path, co_id,
            status=new_status,
            approved_by=approved_by,
            approval_date=approval_date,
        )

    return {
        "ok": True,
        "dry_run": dry_run,
        "co_id": co_id,
        "previous_status": co.status,
        "previous_status_kr": CO_STATUS_KR.get(co.status, co.status),
        "new_status": new_status,
        "new_status_kr": CO_STATUS_KR.get(new_status, new_status),
        "approved_by": approved_by,
    }


# ---------------------------------------------------------------------------
# Calculate CO impact
# ---------------------------------------------------------------------------


def calculate_co_impact(
    db_path: str | Path,
    co_id: str,
) -> dict[str, Any]:
    """Calculate total cost and schedule impact of a change order."""
    co = db.get_change_order(db_path, co_id)
    if not co:
        return {"ok": False, "error": f"변경지시를 찾을 수 없습니다: {co_id}"}

    items = db.list_change_order_items(db_path, co_id)

    items_detail = []
    total_cost_change = 0.0
    total_duration_change = 0

    for item in items:
        activities = db.list_activities(db_path)
        act = next((a for a in activities if a.activity_id == item.activity_id), None)
        items_detail.append({
            "co_item_id": item.co_item_id,
            "activity_id": item.activity_id,
            "activity_name": act.name if act else "unknown",
            "cost_change": item.cost_change,
            "duration_change": item.duration_change,
            "description": item.description,
        })
        total_cost_change += item.cost_change
        total_duration_change += item.duration_change

    return {
        "ok": True,
        "co_id": co_id,
        "title": co.title,
        "co_type": co.co_type,
        "co_type_kr": CO_TYPE_KR.get(co.co_type, co.co_type),
        "status": co.status,
        "status_kr": CO_STATUS_KR.get(co.status, co.status),
        "header_direct_cost": co.direct_cost,
        "header_markup_pct": co.markup_pct,
        "header_total_cost": co.total_cost,
        "header_schedule_impact_days": co.schedule_impact_days,
        "items_count": len(items),
        "items": items_detail,
        "items_total_cost_change": round(total_cost_change, 0),
        "items_total_duration_change": total_duration_change,
    }


# ---------------------------------------------------------------------------
# List change orders
# ---------------------------------------------------------------------------


def list_change_orders_from_db(
    db_path: str | Path,
    *,
    status: str | None = None,
    co_type: str | None = None,
) -> dict[str, Any]:
    """List change orders with optional filters."""
    orders = db.list_change_orders(db_path, status=status, co_type=co_type)
    return {
        "ok": True,
        "count": len(orders),
        "orders": [
            {
                "co_id": co.co_id,
                "title": co.title,
                "co_type": co.co_type,
                "co_type_kr": CO_TYPE_KR.get(co.co_type, co.co_type),
                "status": co.status,
                "status_kr": CO_STATUS_KR.get(co.status, co.status),
                "requested_by": co.requested_by,
                "direct_cost": co.direct_cost,
                "total_cost": co.total_cost,
                "schedule_impact_days": co.schedule_impact_days,
                "request_date": co.request_date.isoformat() if co.request_date else None,
            }
            for co in orders
        ],
    }


# ---------------------------------------------------------------------------
# CO summary
# ---------------------------------------------------------------------------


def apply_change_order_in_db(
    db_path: str | Path,
    co_id: str,
    *,
    applied_by: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """승인된 변경지시를 activities·cost_items에 실반영합니다.

    Parameters
    ----------
    co_id : 반영할 변경지시 ID
    applied_by : 반영 담당자 이름
    dry_run : True이면 변경 내용 미리보기만 반환 (DB 미수정)

    동작
    ----
    - CO 상태가 'approved'인지 확인합니다.
    - 각 ChangeOrderItem에 대해:
        - Activity.duration += item.duration_change
        - Activity.cost    += item.cost_change
        - CostItem.execution_budget += item.cost_change  (cost_item 없으면 신규 생성)
    - CO 상태를 'applied'로 변경합니다.
    - 각 activity 변경사항을 change_log에 기록합니다.
    """
    co = db.get_change_order(db_path, co_id)
    if not co:
        return {"ok": False, "error": f"변경지시를 찾을 수 없습니다: {co_id}"}

    if co.status != "approved":
        return {
            "ok": False,
            "error": (
                f"실반영은 '승인' 상태에서만 가능합니다. "
                f"현재 상태: {CO_STATUS_KR.get(co.status, co.status)}"
            ),
        }

    items = db.list_change_order_items(db_path, co_id)
    if not items:
        return {
            "ok": False,
            "error": "적용할 세부항목이 없습니다. 먼저 add_change_order_item으로 항목을 추가하세요.",
        }

    activities = {a.activity_id: a for a in db.list_activities(db_path)}
    cost_items = {ci.activity_id: ci for ci in db.list_cost_items(db_path)}

    applied_items: list[dict[str, Any]] = []

    for item in items:
        act = activities.get(item.activity_id)
        if not act:
            applied_items.append({
                "co_item_id": item.co_item_id,
                "activity_id": item.activity_id,
                "status": "skipped",
                "reason": "activity not found",
            })
            continue

        # Compute new values
        new_duration = max(0, act.duration + item.duration_change)
        new_cost = max(0.0, act.cost + item.cost_change)

        if not dry_run:
            # Update activity
            updated_act = replace(act, duration=new_duration, cost=new_cost)
            db.update_activity(db_path, updated_act)

            # Update or create cost_item
            ci = cost_items.get(item.activity_id)
            if ci:
                updated_ci = replace(
                    ci,
                    execution_budget=round(ci.execution_budget + item.cost_change, 0),
                )
                db.upsert_cost_item(db_path, updated_ci)
            else:
                from core.models import CostItem
                new_ci = CostItem(
                    cost_item_id=f"ci-{uuid.uuid4().hex[:8]}",
                    activity_id=item.activity_id,
                    execution_budget=max(0.0, item.cost_change),
                )
                db.upsert_cost_item(db_path, new_ci)

            # Log change
            change_entry = ChangeLogEntry(
                change_id=f"chg-{uuid.uuid4().hex[:8]}",
                target_table="activities",
                target_id=item.activity_id,
                before_value=(
                    f"duration={act.duration}, cost={act.cost}"
                ),
                after_value=(
                    f"duration={new_duration}, cost={new_cost}"
                ),
                reason=f"CO 실반영: {co.title} ({co_id})",
                user=applied_by,
                approved_by=co.approved_by,
            )
            db.log_change(db_path, change_entry)

        applied_items.append({
            "co_item_id": item.co_item_id,
            "activity_id": item.activity_id,
            "activity_name": act.name,
            "duration_before": act.duration,
            "duration_after": new_duration,
            "duration_change": item.duration_change,
            "cost_before": act.cost,
            "cost_after": new_cost,
            "cost_change": item.cost_change,
            "status": "applied",
        })

    if not dry_run:
        # Mark CO as applied
        db.update_change_order_status(
            db_path, co_id,
            status="applied",
            approved_by=co.approved_by,
        )

    return {
        "ok": True,
        "dry_run": dry_run,
        "co_id": co_id,
        "title": co.title,
        "applied_by": applied_by,
        "items_processed": len(applied_items),
        "items": applied_items,
        "status_after": "applied" if not dry_run else "approved (dry_run)",
        "status_after_kr": "실반영완료" if not dry_run else "미리보기 (실제 반영 안 됨)",
    }


def get_co_summary(db_path: str | Path) -> dict[str, Any]:
    """Get overall change order summary across all COs."""
    orders = db.list_change_orders(db_path)

    if not orders:
        return {
            "ok": True,
            "total_count": 0,
            "by_status": {},
            "by_type": {},
            "total_direct_cost": 0,
            "total_with_markup": 0,
            "total_schedule_impact_days": 0,
        }

    by_status: dict[str, dict[str, Any]] = {}
    by_type: dict[str, dict[str, Any]] = {}

    for co in orders:
        # By status
        s = by_status.setdefault(co.status, {
            "status_kr": CO_STATUS_KR.get(co.status, co.status),
            "count": 0, "direct_cost": 0.0, "total_cost": 0.0,
        })
        s["count"] += 1
        s["direct_cost"] += co.direct_cost
        s["total_cost"] += co.total_cost

        # By type
        t = by_type.setdefault(co.co_type, {
            "type_kr": CO_TYPE_KR.get(co.co_type, co.co_type),
            "count": 0, "direct_cost": 0.0, "total_cost": 0.0,
        })
        t["count"] += 1
        t["direct_cost"] += co.direct_cost
        t["total_cost"] += co.total_cost

    # Round
    for d in by_status.values():
        d["direct_cost"] = round(d["direct_cost"], 0)
        d["total_cost"] = round(d["total_cost"], 0)
    for d in by_type.values():
        d["direct_cost"] = round(d["direct_cost"], 0)
        d["total_cost"] = round(d["total_cost"], 0)

    return {
        "ok": True,
        "total_count": len(orders),
        "by_status": by_status,
        "by_type": by_type,
        "total_direct_cost": round(sum(co.direct_cost for co in orders), 0),
        "total_with_markup": round(sum(co.total_cost for co in orders), 0),
        "total_schedule_impact_days": sum(co.schedule_impact_days for co in orders),
        "approved_count": sum(1 for co in orders if co.status == "approved"),
        "pending_count": sum(1 for co in orders if co.status == "pending"),
    }
