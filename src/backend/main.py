"""FastAPI backend for Smart Scheduler mobile input.

Endpoints
---------
GET  /api/activities           공종별 활동 목록 (모바일 폼용)
POST /api/daily-record         일일 실적 저장
GET  /api/dashboard-data       소장 대시보드 KPI
POST /api/update-status        활동 상태 변경 (기존 유지)
POST /api/parse-daily-report   공사일보 사진/Excel → 구조화 데이터 (v3.1)
POST /kakao/skill              카카오 오픈빌더 챗봇 스킬서버 (v3.6)
GET  /api/kakao-briefing       카톡 붙여넣기용 브리핑 텍스트 (v3.6)
GET  /api/kakao-reminder       카톡 붙여넣기용 미제출 리마인더 (v3.6)
"""
from __future__ import annotations

import os
import sys
import uuid
from datetime import date, datetime
from pathlib import Path
from typing import Any

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from pydantic import BaseModel
import uvicorn

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.db import create_daily_record, list_activities
from core.kakao_format import format_briefing_for_kakao, format_reminder_for_kakao
from core.kakao_report import handle_utterance
from core.kakao_skill import build_callback_waiting, build_simple_text, parse_skill_payload
from core.models import DailyRecord
from core.notifications import update_activity_status
from core.report_parser import parse_report_excel, parse_report_image

app = FastAPI(title="Smart Scheduler API", version="3.6")

# ── 기본 DB 경로 (Docker 볼륨 마운트 기준) ────────────────────────────────────
_DEFAULT_DB = os.environ.get("DEFAULT_DB_PATH", "/data/현장.scheduler")


@app.on_event("startup")
def _ensure_schema() -> None:
    """기존 DB에 신규 테이블(kakao_users 등) 마이그레이션 보증. DB 없으면 건너뜀."""
    from core.db import initialize_database
    if Path(_DEFAULT_DB).exists():
        initialize_database(_DEFAULT_DB)


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


@app.post("/api/parse-daily-report")
async def parse_daily_report(
    file: UploadFile = File(..., description="공사일보 파일 (JPG/PNG/Excel)"),
    db_path: str = Form(default=_DEFAULT_DB),
) -> dict[str, Any]:
    """공사일보 이미지 또는 Excel → 구조화 JSON.

    이미지(jpg/png): Claude Vision API 호출 (ANTHROPIC_API_KEY 필요)
    Excel(xlsx):     openpyxl로 고정 위치 파싱
    """
    content = await file.read()
    filename = (file.filename or "").lower()

    try:
        if filename.endswith((".xlsx", ".xls")):
            parsed = parse_report_excel(content)
        else:
            # MIME 타입 결정
            if filename.endswith(".png"):
                mime = "image/png"
            elif filename.endswith(".webp"):
                mime = "image/webp"
            else:
                mime = "image/jpeg"
            parsed = parse_report_image(content, mime)

        return {"ok": True, "parsed": parsed, "warnings": parsed.get("warnings", [])}

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"파싱 오류: {e}")


# ─── 카카오톡 챗봇 스킬서버 (v3.6) ────────────────────────────────────────────

# 이미지 파싱(10~20초)이 오픈빌더 타임아웃(5초)을 넘길 때:
#   callbackUrl 있으면 → useCallback 응답 후 백그라운드 처리 → 콜백 전송
#   없으면 → 처리 결과를 보관하고 사용자가 "결과" 입력 시 회신
_LAST_RESULTS: dict[str, str] = {}


def _process_and_callback(db_path: str, bot_user_key: str, utterance: str,
                          image_urls: tuple[str, ...], callback_url: str) -> None:
    """백그라운드: 처리 후 콜백 전송(가능하면) + 결과 보관."""
    import requests as _requests
    try:
        text = handle_utterance(
            db_path, bot_user_key=bot_user_key, utterance=utterance, image_urls=image_urls
        )
    except Exception as e:
        text = f"❌ 처리 중 오류: {e}"
    _LAST_RESULTS[bot_user_key] = text
    if callback_url:
        try:
            _requests.post(callback_url, json=build_simple_text(text), timeout=10)
        except Exception:
            pass  # 콜백 실패 시 "결과" 조회로 대체


@app.post("/kakao/skill")
async def kakao_skill(request: Request, background_tasks: BackgroundTasks) -> dict[str, Any]:
    """카카오 i 오픈빌더 스킬서버 엔드포인트."""
    body = await request.json()
    payload = parse_skill_payload(body)
    db_path = _DEFAULT_DB

    # 비동기 결과 조회
    if payload.utterance in ("결과", "확인"):
        text = _LAST_RESULTS.pop(payload.bot_user_key, "")
        return build_simple_text(text or "처리 중이거나 결과가 없습니다. 잠시 후 다시 입력해주세요.")

    # 이미지 첨부 → 오래 걸림 → 백그라운드 처리
    if payload.image_urls:
        background_tasks.add_task(
            _process_and_callback,
            db_path, payload.bot_user_key, payload.utterance,
            payload.image_urls, payload.callback_url,
        )
        if payload.callback_url:
            return build_callback_waiting("🤖 AI가 일보를 읽는 중입니다... (10~20초)")
        return build_simple_text(
            "🤖 일보 접수! AI가 읽는 중입니다.\n잠시 후 \"결과\" 라고 입력하면 확인됩니다."
        )

    # 텍스트 발화는 즉시 처리 (빠름)
    text = handle_utterance(
        db_path, bot_user_key=payload.bot_user_key, utterance=payload.utterance
    )
    return build_simple_text(text)


@app.get("/api/kakao-briefing")
def kakao_briefing(db_path: str = Query(default=_DEFAULT_DB)) -> dict[str, str]:
    """카톡 붙여넣기용 브리핑 텍스트 (대시보드 복사 버튼용)."""
    return {"text": format_briefing_for_kakao(db_path)}


@app.get("/api/kakao-reminder")
def kakao_reminder(
    db_path: str = Query(default=_DEFAULT_DB),
    base_url: str = Query(default="", description="모바일 입력 앱 주소"),
) -> dict[str, str]:
    """카톡 붙여넣기용 미제출 리마인더 텍스트."""
    return {"text": format_reminder_for_kakao(db_path, base_url=base_url)}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now().isoformat()}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
