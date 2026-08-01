"""인력(Man-day) 관리·분석 엔진 (v3.7).

실제 현장 출역일보(직종별 출력인원)에서 배운 개념을 반영:
  - 직종별 누계 man-day (관리자/배관공/덕트공/보온공/시공팀 ...)
  - 인력 투입 히스토그램 + 누계 곡선 (기성 S-curve와 대칭)
  - 계약 man-day 대비 실투입률 (예: 세일이엔에스 계약 50,586명)
  - 피크 인원 (최대 일일 투입) — 가설/숙소/식수 계획 근거
  - 외국인 인원 비율

참조 실측(2026): 평택FED 일반설비 50,586명 / 자동제어 6,497명,
              63빌딩 일반설비 16,833명 / 자동제어 2,367명.

labor_records 테이블(직종별) 기반. 기존 daily_records.workers(집계치)와 별개로,
직종 해상도가 필요한 인력 관리에 사용한다.
"""
from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.models import LaborRecord

# 표준 직종 분류 (실측 4개 현장 기반 참조 — 강제 아님, 자유 입력 허용)
STANDARD_TRADES: dict[str, list[str]] = {
    "관리": ["소장", "공사", "공무", "안전", "관리자"],
    "기계설비": ["SHOP", "직영", "배관공", "용접공", "덕트공", "보온공",
                 "공조", "위생", "화기", "배관", "덕트", "보온"],
    "자동제어": ["시공팀"],
}


def classify_trade_group(trade: str) -> str:
    """직종 → 대분류(관리/기계설비/자동제어/기타)."""
    for group, members in STANDARD_TRADES.items():
        if trade in members:
            return group
    return "기타"


# ─── 입력 ─────────────────────────────────────────────────────────────────────

def record_labor(
    db_path: str | Path,
    *,
    work_date: date,
    trade: str,
    headcount: int,
    foreign_count: int = 0,
    discipline: str = "",
    company: str = "",
    activity_id: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """직종별 출력인원 1건 기록. dry_run=True면 검증만."""
    if headcount < 0 or foreign_count < 0:
        return {"ok": False, "error": "인원은 음수일 수 없습니다."}
    if foreign_count > headcount:
        return {"ok": False, "error": "외국인 인원이 전체 인원보다 많을 수 없습니다."}

    record = LaborRecord(
        labor_id=str(uuid.uuid4()),
        work_date=work_date,
        trade=trade.strip(),
        headcount=int(headcount),
        foreign_count=int(foreign_count),
        discipline=discipline.strip(),
        company=company.strip(),
        activity_id=activity_id,
    )
    if dry_run:
        return {"ok": True, "dry_run": True, "preview": _record_to_dict(record)}
    saved = db.add_labor_record(db_path, record)
    return {"ok": True, "labor_id": saved.labor_id}


# ─── 출역일보 파싱 결과 저장 (v3.7) ─────────────────────────────────────────────

def save_parsed_labor(
    db_path: str | Path,
    parsed: dict[str, Any],
    *,
    discipline: str = "",
    company: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """report_parser.parse_labor_report_image() 결과 → labor_records 저장.

    parsed["labor"]의 각 직종별 '금일(today)' 인원을 하루치 LaborRecord로 저장한다.
    외국인 인원(foreign_count)은 인원이 가장 많은 직종에 귀속시킨다(근사).
    discipline/company 인자가 있으면 파싱값보다 우선한다.
    """
    from datetime import date as _date

    labor = parsed.get("labor") or []
    if not labor:
        return {"ok": False, "error": "저장할 직종별 인원이 없습니다."}

    work_date = _date.fromisoformat(parsed.get("work_date") or _date.today().isoformat())
    disc = (discipline or parsed.get("discipline") or "").strip()
    comp = (company or parsed.get("company") or "").strip()

    # 외국인 배분: 금일 인원 최다 직종에 몰아준다 (양식상 총계만 있는 경우 대응)
    foreign_total = int(parsed.get("foreign_count") or 0)
    top_idx = max(range(len(labor)), key=lambda i: int(labor[i].get("today") or 0)) if labor else -1

    entries = [
        {
            "work_date": work_date,
            "trade": str(row.get("trade") or "").strip(),
            "headcount": int(row.get("today") or 0),
            "foreign_count": foreign_total if i == top_idx else 0,
            "discipline": disc,
            "company": comp,
        }
        for i, row in enumerate(labor)
        if int(row.get("today") or 0) > 0 and str(row.get("trade") or "").strip()
    ]

    if not entries:
        return {"ok": False, "error": "금일 투입 인원이 0입니다."}

    if dry_run:
        return {
            "ok": True, "dry_run": True,
            "work_date": work_date.isoformat(),
            "saved_count": len(entries),
            "total_headcount": sum(e["headcount"] for e in entries),
            "preview": entries,
        }

    saved = 0
    for e in entries:
        db.add_labor_record(db_path, LaborRecord(
            labor_id=str(uuid.uuid4()),
            work_date=e["work_date"],
            trade=e["trade"],
            headcount=e["headcount"],
            foreign_count=e["foreign_count"],
            discipline=e["discipline"],
            company=e["company"],
        ))
        saved += 1
    return {
        "ok": True,
        "work_date": work_date.isoformat(),
        "saved_count": saved,
        "total_headcount": sum(e["headcount"] for e in entries),
    }


# ─── 직종별 누계 ───────────────────────────────────────────────────────────────

def labor_by_trade(
    db_path: str | Path,
    *,
    discipline: str | None = None,
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """직종별 누계 man-day + 비율."""
    records = db.list_labor_records(
        db_path, discipline=discipline, start_date=start_date, end_date=end_date
    )
    by_trade: dict[str, int] = defaultdict(int)
    by_group: dict[str, int] = defaultdict(int)
    total = 0
    for r in records:
        by_trade[r.trade] += r.headcount
        by_group[classify_trade_group(r.trade)] += r.headcount
        total += r.headcount

    trades = [
        {
            "trade": t,
            "group": classify_trade_group(t),
            "mandays": n,
            "share_pct": round(n / total * 100, 1) if total else 0.0,
        }
        for t, n in sorted(by_trade.items(), key=lambda kv: -kv[1])
    ]
    groups = [
        {"group": g, "mandays": n, "share_pct": round(n / total * 100, 1) if total else 0.0}
        for g, n in sorted(by_group.items(), key=lambda kv: -kv[1])
    ]
    return {
        "ok": True,
        "total_mandays": total,
        "trade_count": len(trades),
        "by_trade": trades,
        "by_group": groups,
    }


# ─── 히스토그램 + 누계 곡선 ────────────────────────────────────────────────────

def labor_histogram(
    db_path: str | Path,
    *,
    discipline: str | None = None,
    interval: str = "monthly",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """기간별 투입 man-day 히스토그램 + 누계 곡선.

    interval: "monthly"(기본) | "weekly" | "daily"
    반환 periods: [{period, mandays, cumulative, cumulative_pct}]
    """
    records = db.list_labor_records(
        db_path, discipline=discipline, start_date=start_date, end_date=end_date
    )
    bucket: dict[str, int] = defaultdict(int)
    for r in records:
        bucket[_period_key(r.work_date, interval)] += r.headcount

    total = sum(bucket.values())
    periods: list[dict[str, Any]] = []
    cumulative = 0
    for key in sorted(bucket):
        cumulative += bucket[key]
        periods.append({
            "period": key,
            "mandays": bucket[key],
            "cumulative": cumulative,
            "cumulative_pct": round(cumulative / total * 100, 1) if total else 0.0,
        })
    peak = max(periods, key=lambda p: p["mandays"]) if periods else None
    return {
        "ok": True,
        "interval": interval,
        "total_mandays": total,
        "period_count": len(periods),
        "peak_period": peak["period"] if peak else None,
        "peak_mandays": peak["mandays"] if peak else 0,
        "periods": periods,
    }


# ─── 피크 인원 (일일 최대) ─────────────────────────────────────────────────────

def peak_manpower(
    db_path: str | Path,
    *,
    discipline: str | None = None,
) -> dict[str, Any]:
    """일일 최대 투입 인원 + 날짜 (가설·숙소·식수 계획 근거)."""
    records = db.list_labor_records(db_path, discipline=discipline)
    daily: dict[date, int] = defaultdict(int)
    for r in records:
        daily[r.work_date] += r.headcount
    if not daily:
        return {"ok": True, "peak_headcount": 0, "peak_date": None, "avg_headcount": 0.0}

    peak_date = max(daily, key=lambda d: daily[d])
    working_days = len(daily)
    total = sum(daily.values())
    return {
        "ok": True,
        "peak_headcount": daily[peak_date],
        "peak_date": peak_date.isoformat(),
        "avg_headcount": round(total / working_days, 1),
        "working_days": working_days,
        "total_mandays": total,
    }


# ─── 계약 man-day 대비 실투입 ──────────────────────────────────────────────────

def labor_budget_status(
    db_path: str | Path,
    *,
    contract_mandays: float,
    discipline: str | None = None,
    as_of: date | None = None,
) -> dict[str, Any]:
    """계약 man-day 대비 누계 실투입률.

    contract_mandays: 계약상 총 투입 예정 인원 (예: 세일이엔에스 50,586)
    """
    records = db.list_labor_records(db_path, discipline=discipline, end_date=as_of)
    invested = sum(r.headcount for r in records)
    remaining = contract_mandays - invested
    usage_pct = round(invested / contract_mandays * 100, 1) if contract_mandays else 0.0

    if usage_pct >= 100:
        status = "초과"
    elif usage_pct >= 90:
        status = "임박"
    elif usage_pct >= 0:
        status = "정상"
    else:
        status = "정상"
    return {
        "ok": True,
        "contract_mandays": contract_mandays,
        "invested_mandays": invested,
        "remaining_mandays": remaining,
        "usage_pct": usage_pct,
        "status": status,
    }


# ─── 외국인 비율 ───────────────────────────────────────────────────────────────

def foreign_labor_summary(
    db_path: str | Path,
    *,
    discipline: str | None = None,
) -> dict[str, Any]:
    """외국인 인원 누계 + 비율 (안전교육·체류자격 관리 근거)."""
    records = db.list_labor_records(db_path, discipline=discipline)
    total = sum(r.headcount for r in records)
    foreign = sum(r.foreign_count for r in records)
    return {
        "ok": True,
        "total_mandays": total,
        "foreign_mandays": foreign,
        "foreign_pct": round(foreign / total * 100, 1) if total else 0.0,
    }


# ─── 헬퍼 ─────────────────────────────────────────────────────────────────────

def _period_key(d: date, interval: str) -> str:
    if interval == "daily":
        return d.isoformat()
    if interval == "weekly":
        iso = d.isocalendar()
        return f"{iso[0]}-W{iso[1]:02d}"
    return f"{d.year}-{d.month:02d}"  # monthly


def _record_to_dict(r: LaborRecord) -> dict[str, Any]:
    return {
        "work_date": r.work_date.isoformat(),
        "trade": r.trade,
        "headcount": r.headcount,
        "foreign_count": r.foreign_count,
        "discipline": r.discipline,
        "company": r.company,
    }
