"""MCP tools for material tracking and inspection management.

Exposes the existing DB material/inspection tables through MCP tools
and provides a combined activity logistics view.
"""
from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from core import db
from core.models import InspectionRecord, MaterialRecord


# ---------------------------------------------------------------------------
# Material tools
# ---------------------------------------------------------------------------


def add_material(
    db_path: str,
    activity_id: str,
    material_name: str,
    *,
    order_date: str | None = None,
    expected_date: str | None = None,
    status: str = "planned",
) -> dict[str, Any]:
    """Add a material tracking record for an activity.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : activity this material belongs to
    material_name : name of the material (e.g. '밸브 50A')
    order_date : date material was ordered (YYYY-MM-DD)
    expected_date : expected delivery date (YYYY-MM-DD)
    status : 'planned', 'ordered', 'delivered', 'installed'
    """
    material_id = f"mat-{uuid.uuid4().hex[:8]}"
    record = MaterialRecord(
        material_id=material_id,
        activity_id=activity_id,
        material_name=material_name,
        order_date=_parse_date(order_date),
        expected_date=_parse_date(expected_date),
        status=status,
    )
    created = db.create_material_record(db_path, record)
    return {
        "ok": True,
        "material_id": created.material_id,
        "activity_id": activity_id,
        "material_name": material_name,
        "status": status,
    }


def list_materials_tool(
    db_path: str,
    *,
    activity_id: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List material records, optionally filtered by activity or status.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : filter by activity
    status : filter by status ('planned', 'ordered', 'delivered', 'installed')
    """
    materials = db.list_materials(db_path, activity_id=activity_id, status=status)
    return {
        "ok": True,
        "count": len(materials),
        "materials": [
            {
                "material_id": m.material_id,
                "activity_id": m.activity_id,
                "material_name": m.material_name,
                "order_date": m.order_date.isoformat() if m.order_date else None,
                "expected_date": m.expected_date.isoformat() if m.expected_date else None,
                "actual_date": m.actual_date.isoformat() if m.actual_date else None,
                "status": m.status,
            }
            for m in materials
        ],
    }


def update_material(
    db_path: str,
    material_id: str,
    *,
    status: str,
    actual_date: str | None = None,
) -> dict[str, Any]:
    """Update material delivery status.

    Parameters
    ----------
    db_path : path to the .scheduler file
    material_id : ID of the material record
    status : new status ('ordered', 'delivered', 'installed')
    actual_date : actual delivery date (YYYY-MM-DD)
    """
    updated = db.update_material_status(
        db_path, material_id, status=status, actual_date=_parse_date(actual_date),
    )
    return {
        "ok": True,
        "material_id": updated.material_id,
        "status": updated.status,
        "actual_date": updated.actual_date.isoformat() if updated.actual_date else None,
    }


# ---------------------------------------------------------------------------
# Inspection tools
# ---------------------------------------------------------------------------


def add_inspection(
    db_path: str,
    activity_id: str,
    inspection_type: str,
    *,
    planned_date: str | None = None,
    status: str = "planned",
) -> dict[str, Any]:
    """Add an inspection record for an activity.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : activity this inspection belongs to
    inspection_type : type of inspection (e.g. '배관수압시험', '절연저항측정')
    planned_date : planned inspection date (YYYY-MM-DD)
    status : 'planned', 'scheduled', 'passed', 'failed', 'deferred'
    """
    inspection_id = f"insp-{uuid.uuid4().hex[:8]}"
    record = InspectionRecord(
        inspection_id=inspection_id,
        activity_id=activity_id,
        inspection_type=inspection_type,
        planned_date=_parse_date(planned_date),
        status=status,
    )
    created = db.create_inspection_record(db_path, record)
    return {
        "ok": True,
        "inspection_id": created.inspection_id,
        "activity_id": activity_id,
        "inspection_type": inspection_type,
        "status": status,
    }


def list_inspections_tool(
    db_path: str,
    *,
    activity_id: str | None = None,
    status: str | None = None,
) -> dict[str, Any]:
    """List inspection records, optionally filtered by activity or status.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : filter by activity
    status : filter by status ('planned', 'scheduled', 'passed', 'failed', 'deferred')
    """
    inspections = db.list_inspections(db_path, activity_id=activity_id, status=status)
    return {
        "ok": True,
        "count": len(inspections),
        "inspections": [
            {
                "inspection_id": i.inspection_id,
                "activity_id": i.activity_id,
                "inspection_type": i.inspection_type,
                "planned_date": i.planned_date.isoformat() if i.planned_date else None,
                "actual_date": i.actual_date.isoformat() if i.actual_date else None,
                "status": i.status,
                "approver": i.approver,
            }
            for i in inspections
        ],
    }


def update_inspection(
    db_path: str,
    inspection_id: str,
    *,
    status: str,
    actual_date: str | None = None,
    approver: str | None = None,
) -> dict[str, Any]:
    """Update inspection status and result.

    Parameters
    ----------
    db_path : path to the .scheduler file
    inspection_id : ID of the inspection record
    status : new status ('passed', 'failed', 'deferred')
    actual_date : actual inspection date (YYYY-MM-DD)
    approver : name of the approver
    """
    updated = db.update_inspection_status(
        db_path,
        inspection_id,
        status=status,
        actual_date=_parse_date(actual_date),
        approver=approver,
    )
    return {
        "ok": True,
        "inspection_id": updated.inspection_id,
        "status": updated.status,
        "actual_date": updated.actual_date.isoformat() if updated.actual_date else None,
        "approver": updated.approver,
    }


# ---------------------------------------------------------------------------
# Combined logistics view
# ---------------------------------------------------------------------------


def get_activity_logistics(
    db_path: str,
    activity_id: str,
) -> dict[str, Any]:
    """Get combined view of an activity with its materials and inspections.

    Parameters
    ----------
    db_path : path to the .scheduler file
    activity_id : target activity ID

    Returns activity info, material list, inspection list, and logistics summary.
    """
    activities = db.list_activities(db_path)
    activity = next((a for a in activities if a.activity_id == activity_id), None)
    if not activity:
        return {"ok": False, "error": f"Activity not found: {activity_id}"}

    cost_items = db.list_cost_items(db_path, activity_id=activity_id)
    cost = cost_items[0] if cost_items else None
    materials = db.list_materials(db_path, activity_id=activity_id)
    inspections = db.list_inspections(db_path, activity_id=activity_id)

    # Material summary
    mat_by_status: dict[str, int] = {}
    for m in materials:
        mat_by_status[m.status] = mat_by_status.get(m.status, 0) + 1

    overdue_materials = [
        m for m in materials
        if m.expected_date and m.status in ("planned", "ordered") and m.expected_date < date.today()
    ]

    # Inspection summary
    insp_by_status: dict[str, int] = {}
    for i in inspections:
        insp_by_status[i.status] = insp_by_status.get(i.status, 0) + 1

    upcoming_inspections = [
        i for i in inspections
        if i.planned_date and i.status in ("planned", "scheduled") and i.planned_date >= date.today()
    ]
    upcoming_inspections.sort(key=lambda x: x.planned_date or date.max)

    return {
        "ok": True,
        "activity": {
            "activity_id": activity.activity_id,
            "code": activity.code,
            "name": activity.name,
            "discipline": activity.discipline,
            "es_date": activity.es_date.isoformat() if activity.es_date else None,
            "ef_date": activity.ef_date.isoformat() if activity.ef_date else None,
            "duration": activity.duration,
        },
        "cost": {
            "contract_amount": cost.contract_amount if cost else 0,
            "execution_budget": cost.execution_budget if cost else 0,
            "billing_amount": cost.billing_amount if cost else 0,
        } if cost else None,
        "materials": {
            "total": len(materials),
            "by_status": mat_by_status,
            "overdue_count": len(overdue_materials),
            "items": [
                {
                    "material_id": m.material_id,
                    "material_name": m.material_name,
                    "status": m.status,
                    "expected_date": m.expected_date.isoformat() if m.expected_date else None,
                    "actual_date": m.actual_date.isoformat() if m.actual_date else None,
                }
                for m in materials
            ],
        },
        "inspections": {
            "total": len(inspections),
            "by_status": insp_by_status,
            "upcoming": [
                {
                    "inspection_id": i.inspection_id,
                    "inspection_type": i.inspection_type,
                    "planned_date": i.planned_date.isoformat() if i.planned_date else None,
                    "status": i.status,
                }
                for i in upcoming_inspections[:5]
            ],
        },
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_date(value: str | None) -> date | None:
    if value and value.strip():
        return date.fromisoformat(value.strip())
    return None
