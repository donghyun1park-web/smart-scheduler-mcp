"""Active alert scanning.

Instead of building an external push infrastructure (SMS / KakaoTalk), this
module surfaces actionable warnings that Claude can mention proactively during
briefings. It captures ~80% of the value of push notifications with zero
external infrastructure.

Alert thresholds are read from ``ProjectSettings.thresholds`` when available,
falling back to sensible defaults, so each site can tune them.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

from core import db

# Default thresholds (overridable via ProjectSettings.thresholds)
_DEFAULTS = {
    "progress_gap_warn_pct": 3.0,   # 계획-실적 차이 경고
    "progress_gap_crit_pct": 7.0,   # 계획-실적 차이 위험
    "material_overdue_days": 0,     # 납기 초과 일수 (0 = 당일도 경고)
    "co_pending_warn_count": 1,     # 승인 대기 CO 건수
}

# Material statuses meaning "not yet on site"
_NOT_DELIVERED = {"planned", "ordered"}


def _load_thresholds(db_path: str | Path) -> dict[str, Any]:
    thresholds = dict(_DEFAULTS)
    try:
        project_info = db.load_project_summary(db_path)
        project = project_info.get("project")
        project_id = getattr(project, "project_id", "") if project else ""
        if project_id:
            settings = db.get_project_settings(db_path, project_id)
            if settings and settings.thresholds:
                thresholds.update(settings.thresholds)
    except Exception:
        # Threshold loading must never break alert scanning
        pass
    return thresholds


def scan_alerts(
    db_path: str | Path,
    *,
    as_of: date | None = None,
) -> dict[str, Any]:
    """Scan the project for actionable alerts.

    Returns a list of alerts each with a level emoji, category, and message,
    sorted with critical (🔴) items first.
    """
    today = as_of or date.today()
    th = _load_thresholds(db_path)
    alerts: list[dict[str, Any]] = []

    # --- 1. Overdue material deliveries ---------------------------------
    overdue_days = int(th.get("material_overdue_days", 0))
    try:
        materials = db.list_materials(db_path)
    except Exception:
        materials = []
    for m in materials:
        if m.status in _NOT_DELIVERED and m.expected_date:
            late = (today - m.expected_date).days
            if late >= overdue_days and m.expected_date <= today:
                alerts.append({
                    "level": "🔴",
                    "category": "자재납기",
                    "code": "material_overdue",
                    "message": (
                        f"{m.material_name} 납기 초과 ({late}일 지연, "
                        f"예정 {m.expected_date.isoformat()}, 상태 {m.status})"
                    ),
                    "ref_id": m.material_id,
                })

    # --- 2. Pending change orders --------------------------------------
    try:
        pending_cos = db.list_change_orders(db_path, status="pending")
    except Exception:
        pending_cos = []
    if len(pending_cos) >= int(th.get("co_pending_warn_count", 1)):
        total = sum(co.total_cost for co in pending_cos)
        alerts.append({
            "level": "🟡",
            "category": "설계변경",
            "code": "co_pending",
            "message": (
                f"변경지시 승인 대기 {len(pending_cos)}건 "
                f"(총 {total:,.0f}원)"
            ),
            "ref_id": None,
        })

    # --- 3. Approved-but-not-applied change orders ---------------------
    try:
        approved_cos = db.list_change_orders(db_path, status="approved")
    except Exception:
        approved_cos = []
    if approved_cos:
        alerts.append({
            "level": "🟡",
            "category": "설계변경",
            "code": "co_unapplied",
            "message": (
                f"승인됐지만 미반영된 변경지시 {len(approved_cos)}건 "
                f"(apply_change_order 필요)"
            ),
            "ref_id": None,
        })

    # --- 4. Schedule progress gap --------------------------------------
    gap_alert = _progress_gap_alert(db_path, today, th)
    if gap_alert:
        alerts.append(gap_alert)

    # Sort: 🔴 first, then 🟡, then others
    _order = {"🔴": 0, "🟡": 1, "🟢": 2}
    alerts.sort(key=lambda a: _order.get(a["level"], 3))

    crit = sum(1 for a in alerts if a["level"] == "🔴")
    warn = sum(1 for a in alerts if a["level"] == "🟡")
    return {
        "ok": True,
        "as_of": today.isoformat(),
        "alert_count": len(alerts),
        "critical_count": crit,
        "warning_count": warn,
        "alerts": alerts,
    }


def _progress_gap_alert(
    db_path: str | Path,
    today: date,
    th: dict[str, Any],
) -> dict[str, Any] | None:
    """Compute overall planned-vs-actual gap and emit an alert if significant.

    Imported lazily to avoid a circular import with dashboard (which imports
    alerts for briefing integration).
    """
    try:
        from core.dashboard import generate_site_briefing
    except Exception:
        return None

    # Call the underlying briefing WITHOUT alerts to avoid recursion.
    try:
        brief = generate_site_briefing(db_path, as_of=today, _include_alerts=False)
    except TypeError:
        # Older signature without the flag
        brief = generate_site_briefing(db_path, as_of=today)
    except Exception:
        return None

    gap = brief.get("progress_gap_pct", 0.0)  # actual - planned (음수 = 부진)
    behind = -float(gap)  # positive means behind schedule
    crit = float(th.get("progress_gap_crit_pct", 7.0))
    warn = float(th.get("progress_gap_warn_pct", 3.0))

    if behind >= crit:
        return {
            "level": "🔴",
            "category": "공정지연",
            "code": "progress_gap_critical",
            "message": f"전체 공정 부진 (계획 대비 {behind:.1f}%p 지연)",
            "ref_id": None,
        }
    if behind >= warn:
        return {
            "level": "🟡",
            "category": "공정지연",
            "code": "progress_gap_warning",
            "message": f"전체 공정 주의 (계획 대비 {behind:.1f}%p 지연)",
            "ref_id": None,
        }
    return None
