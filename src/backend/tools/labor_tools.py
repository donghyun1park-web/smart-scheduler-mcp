"""MCP tools for 인력(Man-day) 관리 (v3.7).

직종별 출력인원 입력, 히스토그램·누계 곡선, 계약 대비 실투입, 피크 인원,
외국인 비율을 제공한다. 실제 현장 출역일보 구조에 대응.
"""
from __future__ import annotations

from datetime import date as _date
from typing import Any

from core.labor import (
    foreign_labor_summary,
    labor_budget_status,
    labor_by_trade,
    labor_histogram,
    peak_manpower,
    record_labor,
)


def _d(s: str | None) -> _date | None:
    return _date.fromisoformat(s) if s else None


def input_labor_record(
    db_path: str,
    work_date: str,
    trade: str,
    headcount: int,
    *,
    foreign_count: int = 0,
    discipline: str = "",
    company: str = "",
    activity_id: str = "",
    dry_run: bool = True,
) -> dict[str, Any]:
    """직종별 일일 출력인원 1건을 기록합니다.

    출역일보의 한 줄(예: 배관공 25명, 외국인 3명)에 대응합니다.

    Parameters
    ----------
    db_path : .scheduler 파일 경로
    work_date : 작업일 (YYYY-MM-DD)
    trade : 직종 (관리자/배관공/덕트공/보온공/시공팀 등, 자유 입력)
    headcount : 투입 인원
    foreign_count : 외국인 인원 (headcount 중 일부)
    discipline : 공종 (일반설비/자동제어/기계설비 등)
    company : 협력사명
    activity_id : 활동 연결 (선택)
    dry_run : True면 검증만 (기본값 안전)
    """
    return record_labor(
        db_path,
        work_date=_date.fromisoformat(work_date),
        trade=trade,
        headcount=headcount,
        foreign_count=foreign_count,
        discipline=discipline,
        company=company,
        activity_id=activity_id,
        dry_run=dry_run,
    )


def get_labor_by_trade(
    db_path: str,
    *,
    discipline: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """직종별 누계 man-day와 비율을 반환합니다.

    어느 직종에 인력이 집중됐는지(예: 덕트공 28%, 배관공 39%)를 파악해
    노무 계획·생산성 분석의 근거로 씁니다.
    """
    return labor_by_trade(
        db_path, discipline=discipline, start_date=_d(start_date), end_date=_d(end_date)
    )


def get_labor_histogram(
    db_path: str,
    *,
    discipline: str | None = None,
    interval: str = "monthly",
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict[str, Any]:
    """기간별 투입 man-day 히스토그램 + 누계 곡선을 반환합니다.

    기성 S-curve와 대칭되는 '인력 투입 곡선'으로, 피크 시점과
    누계 진척을 함께 봅니다. interval: monthly(기본)/weekly/daily.
    """
    return labor_histogram(
        db_path, discipline=discipline, interval=interval,
        start_date=_d(start_date), end_date=_d(end_date),
    )


def get_peak_manpower(
    db_path: str,
    *,
    discipline: str | None = None,
) -> dict[str, Any]:
    """일일 최대 투입 인원과 날짜, 평균 인원을 반환합니다.

    피크 인원은 가설사무실·숙소·식수·주차 등 현장 지원계획의 근거입니다.
    """
    return peak_manpower(db_path, discipline=discipline)


def get_labor_budget_status(
    db_path: str,
    contract_mandays: float,
    *,
    discipline: str | None = None,
    as_of: str | None = None,
) -> dict[str, Any]:
    """계약 man-day 대비 누계 실투입률을 반환합니다.

    contract_mandays: 계약상 총 투입 예정 인원 (예: 세일이엔에스 50,586).
    실투입이 계약 대비 임박/초과하면 노무비 리스크 신호입니다.
    상태: 정상 / 임박(≥90%) / 초과(≥100%).
    """
    return labor_budget_status(
        db_path, contract_mandays=contract_mandays,
        discipline=discipline, as_of=_d(as_of),
    )


def get_foreign_labor_summary(
    db_path: str,
    *,
    discipline: str | None = None,
) -> dict[str, Any]:
    """외국인 인원 누계와 비율을 반환합니다 (안전교육·체류자격 관리 근거)."""
    return foreign_labor_summary(db_path, discipline=discipline)
