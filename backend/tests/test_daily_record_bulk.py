"""Tests for the TSV bulk DailyRecord parser/applier."""
from __future__ import annotations

import uuid
from datetime import date

import pytest

from core import db
from core.daily_record_bulk import apply_parsed_rows, parse_tsv
from core.models import Activity, WBS
from tools.project_tools import create_project


VALID_TSV = """작업코드\t일자\t계획수량\t실적수량\t작업자수\t비고
A-001\t2026-06-10\t100\t90\t5\t오후 우천
A-002\t2026-06-10\t50\t50\t3\t정상
"""


def test_parse_tsv_skips_header_and_returns_two_rows():
    parsed = parse_tsv(VALID_TSV)
    assert len(parsed.rows) == 2
    assert parsed.failed_rows == []
    assert parsed.rows[0].activity_code == "A-001"
    assert parsed.rows[0].work_date == date(2026, 6, 10)
    assert parsed.rows[0].planned_qty == 100
    assert parsed.rows[0].actual_qty == 90
    assert parsed.rows[0].workers == 5
    assert parsed.rows[0].remarks == "오후 우천"


def test_parse_tsv_reports_per_row_failures():
    text = (
        "작업코드\t일자\t계획수량\t실적수량\n"
        "A-001\t2026-06-10\t100\t90\n"        # ok
        "A-002\tnot-a-date\t50\t40\n"          # bad date
        "A-003\t2026-06-10\tabc\t40\n"         # bad number
        "incomplete\t2026-06-10\n"             # too few cells
    )
    parsed = parse_tsv(text)
    assert len(parsed.rows) == 1
    assert {r["row"] for r in parsed.failed_rows} == {3, 4, 5}
    reasons = " ".join(r["reason"] for r in parsed.failed_rows)
    assert "일자" in reasons or "ISO" in reasons
    assert "필수 열" in reasons or "계획수량" in reasons or "숫자" in reasons


def test_parse_tsv_accepts_comma_numbers_and_skips_comments():
    text = (
        "# 이번 주 보고\n"
        "\n"
        "A-001\t2026-06-10\t1,200\t1,150\n"
    )
    parsed = parse_tsv(text)
    assert len(parsed.rows) == 1
    assert parsed.rows[0].planned_qty == 1200
    assert parsed.rows[0].actual_qty == 1150


def test_apply_parsed_rows_inserts_records_and_reports_skipped(tmp_path):
    project = create_project(
        "TSV 적용 테스트",
        "2026-06-01",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    path = project["project_path"]
    wbs = db.add_wbs(path, WBS(str(uuid.uuid4()), None, "MEP", "MEP", 1))
    db.add_activity(path, Activity(str(uuid.uuid4()), "A-001", "위생", wbs.wbs_id, "위생", "1F", 3, 0))
    # A-002 is missing on purpose → should be reported as skipped

    parsed = parse_tsv(VALID_TSV)
    result = apply_parsed_rows(path, parsed)
    assert result["created"] == 1
    assert len(result["skipped"]) == 1
    assert result["skipped"][0]["activity_code"] == "A-002"

    records = db.list_daily_records(path)
    assert len(records) == 1
    assert records[0].planned_qty == 100
    assert records[0].actual_qty == 90
    assert records[0].workers == 5
