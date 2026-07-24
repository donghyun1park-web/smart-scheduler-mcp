"""인력(Man-day) 관리 모듈 테스트 (v3.7).

실측 현장(평택FED 일반설비, 63빌딩 등)의 직종·규모 패턴을 참고한 시나리오.
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from unittest.mock import patch

from core import db
from core.labor import (
    classify_trade_group,
    foreign_labor_summary,
    labor_budget_status,
    labor_by_trade,
    labor_histogram,
    peak_manpower,
    record_labor,
    save_parsed_labor,
)
from core.models import Calendar, Project
from core.report_parser import _normalize_labor, _safe_int


@pytest.fixture
def labor_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "labor.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "T", "1111100"))
    db.create_project(db_path, Project("p1", "평택FED", date(2022, 1, 1), "cal-1"))

    # 일반설비 — 2024년 배관공·덕트공·관리자 (실측 직종)
    rows = [
        (date(2024, 3, 1), "관리자", 8, 0),
        (date(2024, 3, 1), "덕트공", 25, 5),
        (date(2024, 3, 2), "관리자", 8, 0),
        (date(2024, 3, 2), "덕트공", 30, 6),
        (date(2024, 3, 2), "배관공", 12, 2),
        (date(2024, 4, 1), "배관공", 40, 8),
        (date(2024, 4, 1), "보온공", 15, 0),
    ]
    for d, trade, hc, fc in rows:
        record_labor(db_path, work_date=d, trade=trade, headcount=hc,
                     foreign_count=fc, discipline="일반설비", company="세일이엔에스",
                     dry_run=False)
    return db_path


# ─── 직종 분류 ─────────────────────────────────────────────────────────────────

class TestTradeGroup:
    def test_management(self):
        assert classify_trade_group("소장") == "관리"
        assert classify_trade_group("관리자") == "관리"

    def test_mechanical(self):
        assert classify_trade_group("배관공") == "기계설비"
        assert classify_trade_group("덕트공") == "기계설비"

    def test_control(self):
        assert classify_trade_group("시공팀") == "자동제어"

    def test_unknown(self):
        assert classify_trade_group("드론조종사") == "기타"


# ─── record_labor ─────────────────────────────────────────────────────────────

class TestRecordLabor:
    def test_dry_run_no_save(self, labor_db):
        r = record_labor(labor_db, work_date=date(2024, 5, 1), trade="배관공",
                         headcount=10, dry_run=True)
        assert r["ok"] and r["dry_run"]
        # 저장 안 됨
        recs = db.list_labor_records(labor_db, start_date=date(2024, 5, 1))
        assert len(recs) == 0

    def test_save(self, labor_db):
        r = record_labor(labor_db, work_date=date(2024, 5, 1), trade="배관공",
                         headcount=10, dry_run=False)
        assert r["ok"] and "labor_id" in r

    def test_foreign_exceeds_total_rejected(self, labor_db):
        r = record_labor(labor_db, work_date=date(2024, 5, 1), trade="배관공",
                         headcount=5, foreign_count=10, dry_run=True)
        assert r["ok"] is False

    def test_negative_rejected(self, labor_db):
        r = record_labor(labor_db, work_date=date(2024, 5, 1), trade="배관공",
                         headcount=-1, dry_run=True)
        assert r["ok"] is False


# ─── 직종별 누계 ───────────────────────────────────────────────────────────────

class TestLaborByTrade:
    def test_totals(self, labor_db):
        res = labor_by_trade(labor_db)
        # 8+25+8+30+12+40+15 = 138
        assert res["total_mandays"] == 138
        assert res["trade_count"] == 4  # 관리자/덕트공/배관공/보온공

    def test_share_sums_to_100(self, labor_db):
        res = labor_by_trade(labor_db)
        assert abs(sum(t["share_pct"] for t in res["by_trade"]) - 100.0) < 0.5

    def test_top_trade_is_ductwork(self, labor_db):
        res = labor_by_trade(labor_db)
        # 덕트공 25+30=55 최대
        assert res["by_trade"][0]["trade"] == "덕트공"
        assert res["by_trade"][0]["mandays"] == 55

    def test_group_rollup(self, labor_db):
        res = labor_by_trade(labor_db)
        groups = {g["group"]: g["mandays"] for g in res["by_group"]}
        assert groups["관리"] == 16          # 관리자 8+8
        assert groups["기계설비"] == 122       # 나머지


# ─── 히스토그램 ────────────────────────────────────────────────────────────────

class TestHistogram:
    def test_monthly_buckets(self, labor_db):
        res = labor_histogram(labor_db, interval="monthly")
        periods = {p["period"]: p for p in res["periods"]}
        assert periods["2024-03"]["mandays"] == 83    # 8+25+8+30+12
        assert periods["2024-04"]["mandays"] == 55    # 40+15

    def test_cumulative(self, labor_db):
        res = labor_histogram(labor_db, interval="monthly")
        assert res["periods"][-1]["cumulative"] == 138
        assert res["periods"][-1]["cumulative_pct"] == 100.0

    def test_peak_period(self, labor_db):
        res = labor_histogram(labor_db, interval="monthly")
        assert res["peak_period"] == "2024-03"
        assert res["peak_mandays"] == 83

    def test_daily_interval(self, labor_db):
        res = labor_histogram(labor_db, interval="daily")
        periods = {p["period"]: p["mandays"] for p in res["periods"]}
        assert periods["2024-03-02"] == 50   # 8+30+12


# ─── 피크 인원 ─────────────────────────────────────────────────────────────────

class TestPeak:
    def test_peak_day(self, labor_db):
        res = peak_manpower(labor_db)
        assert res["peak_date"] == "2024-04-01"  # 배관공40+보온공15=55
        assert res["peak_headcount"] == 55

    def test_working_days(self, labor_db):
        res = peak_manpower(labor_db)
        assert res["working_days"] == 3   # 3/1, 3/2, 4/1

    def test_empty(self, tmp_path):
        db_path = tmp_path / "empty.scheduler"
        db.initialize_database(db_path)
        res = peak_manpower(db_path)
        assert res["peak_headcount"] == 0


# ─── 계약 대비 ─────────────────────────────────────────────────────────────────

class TestBudget:
    def test_usage_pct(self, labor_db):
        # 실측 참조: 세일이엔에스 계약 50,586 man-day
        res = labor_budget_status(labor_db, contract_mandays=50586)
        assert res["invested_mandays"] == 138
        assert res["remaining_mandays"] == 50586 - 138
        assert res["status"] == "정상"

    def test_near_limit(self, labor_db):
        res = labor_budget_status(labor_db, contract_mandays=140)
        assert res["status"] == "임박"   # 138/140 = 98.6%

    def test_over(self, labor_db):
        res = labor_budget_status(labor_db, contract_mandays=100)
        assert res["status"] == "초과"
        assert res["remaining_mandays"] == -38


# ─── 외국인 ────────────────────────────────────────────────────────────────────

class TestForeign:
    def test_foreign_pct(self, labor_db):
        res = foreign_labor_summary(labor_db)
        # 외국인 5+6+2+8 = 21 / 138
        assert res["foreign_mandays"] == 21
        assert res["foreign_pct"] == round(21 / 138 * 100, 1)


# ─── 출역일보 파싱 정규화 (report_parser) ─────────────────────────────────────

class TestNormalizeLabor:
    def test_safe_int_variants(self):
        assert _safe_int("1,236") == 1236
        assert _safe_int("-") == 0
        assert _safe_int(None) == 0
        assert _safe_int(5) == 5
        assert _safe_int("abc") == 0

    def test_drops_total_rows_and_computes(self):
        raw = {
            "work_date": "2026-05-22",
            "labor": [
                {"trade": "소장", "today": "1", "cumulative": "135"},
                {"trade": "직영", "today": "2", "cumulative": "1,236"},
                {"trade": "합계", "today": "3", "cumulative": "1371"},  # 제외돼야 함
            ],
            "foreign_count": "0",
            "warnings": [],
        }
        out = _normalize_labor(raw)
        trades = [x["trade"] for x in out["labor"]]
        assert "합계" not in trades
        assert len(out["labor"]) == 2
        assert out["total_today"] == 3       # 1+2 (합계행 제외 후 자동합산)
        assert out["labor"][1]["cumulative"] == 1236

    def test_empty_labor_warns(self):
        out = _normalize_labor({"labor": [], "warnings": []})
        assert any("인식" in w for w in out["warnings"])


# ─── save_parsed_labor ────────────────────────────────────────────────────────

class TestSaveParsedLabor:
    _PARSED = {
        "work_date": "2026-05-22",
        "company": "HDC랩스",
        "discipline": "일반설비",
        "labor": [
            {"trade": "소장", "today": 1, "cumulative": 135},
            {"trade": "직영", "today": 2, "cumulative": 1236},
            {"trade": "안전", "today": 0, "cumulative": 577},  # today 0 → 제외
        ],
        "foreign_count": 3,
        "total_today": 3,
    }

    def test_dry_run_preview(self, labor_db):
        res = save_parsed_labor(labor_db, self._PARSED, dry_run=True)
        assert res["ok"] and res["dry_run"]
        assert res["saved_count"] == 2       # today>0 인 소장·직영만
        assert res["total_headcount"] == 3

    def test_save_persists(self, labor_db):
        before = len(db.list_labor_records(labor_db, start_date=date(2026, 5, 22)))
        res = save_parsed_labor(labor_db, self._PARSED, dry_run=False)
        assert res["ok"] and res["saved_count"] == 2
        recs = db.list_labor_records(labor_db, start_date=date(2026, 5, 22))
        assert len(recs) - before == 2
        # 외국인은 금일 최다 직종(직영 2명)에 귀속
        jikyeong = [r for r in recs if r.trade == "직영"][0]
        assert jikyeong.foreign_count == 3
        assert jikyeong.company == "HDC랩스"

    def test_discipline_override(self, labor_db):
        save_parsed_labor(labor_db, self._PARSED, discipline="자동제어", dry_run=False)
        recs = db.list_labor_records(labor_db, discipline="자동제어",
                                     start_date=date(2026, 5, 22))
        assert len(recs) == 2

    def test_empty_rejected(self, labor_db):
        res = save_parsed_labor(labor_db, {"labor": []}, dry_run=True)
        assert res["ok"] is False


# ─── 카카오 출역일보 라우팅 ───────────────────────────────────────────────────

class TestKakaoLaborRouting:
    def test_labor_photo_saves(self, labor_db):
        from core.kakao_report import handle_utterance
        parsed = {
            "work_date": "2026-05-22", "company": "HDC랩스", "discipline": "일반설비",
            "labor": [{"trade": "직영", "today": 5, "cumulative": 1236}],
            "foreign_count": 1, "total_today": 5, "warnings": [],
        }
        with patch("core.kakao_report._download_image", return_value=b"\xff\xd8\xff"), \
             patch("core.kakao_report.parse_labor_report_image", return_value=parsed):
            reply = handle_utterance(
                labor_db, bot_user_key="u1", utterance="출역",
                image_urls=("https://secure.kakao.com/l1.jpg",),
            )
        assert "출역일보 저장 완료" in reply
        recs = db.list_labor_records(labor_db, start_date=date(2026, 5, 22))
        assert any(r.trade == "직영" and r.headcount == 5 for r in recs)
