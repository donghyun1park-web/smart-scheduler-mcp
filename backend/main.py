"""FastAPI backend for Smart Scheduler mobile input.

Endpoints
---------
GET  /api/activities      공종별 활동 목록 (모바일 폼용)
POST /api/daily-record    일일 실적 저장
GET  /api/dashboard-data  소장 대시보드 KPI
POST /api/update-status   활동 상태 변경 (기존 유지)
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
import uvicorn

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import create_daily_record, list_activities
from core.models import DailyRecord
from core.notifications import update_activity_status

app = FastAPI(title="Smart Scheduler API", version="3.0")

# ── 기본 DB 경로 (Docker 볼륨 마운트 기준) ────────────────────────────────────
_DEFAULT_DB = os.environ.get("DEFAULT_DB_PATH", "/data/현장.scheduler")


# ─── Request / Response models ────────────────────────────────────────────────

class StatusUpdateRequest(BaseModel):
    activity_id: str
    new_status: str
    delayed_days: int = 0
    db_path: str = _DEFAULT_DB


class DailyRecordRequest(BaseModel):
    db_path: str = _DEFAULT_DB
    activity_id: str
    work_date: str          # YYYY-MM-DD
    progress_pct: float     # 0‒100 (진행률 %)
    workers: int = 0
    remarks: str = ""


# ─── Endpoints ────────────────────────────────────────────────────────────────

@app.get("/api/activities")
def get_activities(
    discipline: str = Query(default="건축", description="공종 (건축/기계설비/전기설비/토목)"),
    db_path: str = Query(default=_DEFAULT_DB),
    as_of: str | None = Query(default=None, description="기준일 YYYY-MM-DD, 기본 오늘"),
) -> list[dict[str, Any]]:
    """공종별 활동 목록 반환 (모바일 폼 드롭다운용)."""
    try:
        activities = list_activities(db_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB 오류: {e}")

    as_of_date = date.fromisoformat(as_of) if as_of else date.today()

    filtered = [
        a for a in activities
        if a.discipline == discipline
        and (a.es_date is None or a.es_date <= as_of_date)   # 시작된 활동
        and (a.ef_date is None or a.ef_date >= as_of_date)   # 아직 안 끝난 활동
    ]

    return [
        {
            "activity_id": a.activity_id,
            "code":        a.code,
            "name":        a.name,
            "zone":        a.zone or "",
            "discipline":  a.discipline,
            "progress_pct": getattr(a, "progress_pct", 0) or 0,
            "duration":    a.duration,
            "label":       f"[{a.zone or '-'}] {a.name}" if a.zone else a.name,
        }
        for a in filtered
    ]


@app.post("/api/daily-record")
def post_daily_record(req: DailyRecordRequest) -> dict[str, Any]:
    """일일 실적 저장. progress_pct → actual_qty로 매핑."""
    try:
        record = DailyRecord(
            record_id=str(uuid.uuid4()),
            activity_id=req.activity_id,
            work_date=date.fromisoformat(req.work_date),
            planned_qty=100.0,          # 진행률 기준 (100% 기준 정규화)
            actual_qty=req.progress_pct,
            workers=req.workers,
            remarks=req.remarks,
        )
        saved = create_daily_record(req.db_path, record)
        return {"ok": True, "record_id": saved.record_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"저장 실패: {e}")


@app.get("/api/dashboard-data")
def get_dashboard_data(db_path: str = Query(default=_DEFAULT_DB)) -> dict[str, Any]:
    """소장 대시보드 KPI (실 DB 연동)."""
    try:
        from core.dashboard import generate_site_briefing
        brief = generate_site_briefing(db_path)
        return {
            "overall_progress": brief.get("overall_progress_pct", 0),
            "planned_progress":  brief.get("planned_progress_pct", 0),
            "status":            brief.get("status", "Unknown"),
            "delayed_count":     brief.get("delayed_count", 0),
            "alert_summary":     brief.get("alert_summary", ""),
            "recent_alerts":     [
                a.get("message", "") for a in brief.get("alerts", [])
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/update-status")
def update_status(req: StatusUpdateRequest) -> dict[str, Any]:
    """활동 상태 변경 (완료/지연) — 기존 API 유지."""
    try:
        update_activity_status(req.db_path, req.activity_id, req.new_status, req.delayed_days)
        return {"status": "success", "message": f"{req.activity_id} 업데이트 완료"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
