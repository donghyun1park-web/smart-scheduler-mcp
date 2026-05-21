"""Tests for core.schedule_importer."""
from __future__ import annotations

from datetime import date

import pytest

from core.schedule_importer import (
    ParsedActivity,
    _merge_continuation_rows,
    _normalize_discipline,
    parse_schedule_excel,
)


# ---------------------------------------------------------------------------
# Unit tests: discipline normalization
# ---------------------------------------------------------------------------


def test_normalize_discipline_known():
    assert _normalize_discipline("골조공사") == "건축"
    assert _normalize_discipline("토공사") == "토목"
    assert _normalize_discipline("기계설비") == "기계설비"
    assert _normalize_discipline("부대토목") == "토목"


def test_normalize_discipline_unknown_returns_cleaned():
    assert _normalize_discipline("특수공종") == "특수공종"


def test_normalize_discipline_empty():
    assert _normalize_discipline("") == "공통"


# ---------------------------------------------------------------------------
# Unit tests: merge continuation rows
# ---------------------------------------------------------------------------


def _make_activity(row: int, item: str = "", es: date | None = None, ef: date | None = None) -> ParsedActivity:
    return ParsedActivity(
        row_number=row,
        discipline="건축",
        item=item,
        detail="",
        es_date=es,
        ef_date=ef,
        duration_days=(ef - es).days if es and ef else 0,
        bar_texts=[],
    )


def test_merge_extends_date_range():
    activities = [
        _make_activity(10, "골조", date(2027, 1, 10), date(2027, 6, 10)),
        _make_activity(11, "", date(2027, 5, 10), date(2027, 12, 10)),  # continuation
    ]
    merged = _merge_continuation_rows(activities)
    assert len(merged) == 1
    assert merged[0].item == "골조"
    assert merged[0].es_date == date(2027, 1, 10)
    assert merged[0].ef_date == date(2027, 12, 10)


def test_merge_keeps_named_activities_separate():
    activities = [
        _make_activity(10, "골조", date(2027, 1, 10), date(2027, 6, 10)),
        _make_activity(12, "마감", date(2028, 1, 10), date(2028, 6, 10)),
    ]
    merged = _merge_continuation_rows(activities)
    assert len(merged) == 2


def test_merge_empty_list():
    assert _merge_continuation_rows([]) == []


# ---------------------------------------------------------------------------
# Integration test: parse real schedule (if available)
# ---------------------------------------------------------------------------

SCHEDULE_PATH = r"C:/MirTalk/Download/홍은동 355번지 가로주택_전체공정표.xlsx"
SHEET_NAME = "전체예정공정표(홍은동 가로주택정비사업-BEST)REV01"


@pytest.fixture
def schedule_result():
    """Parse the real schedule file, skip if not available."""
    from pathlib import Path

    if not Path(SCHEDULE_PATH).exists():
        pytest.skip("Schedule file not available")
    return parse_schedule_excel(SCHEDULE_PATH, sheet_name=SHEET_NAME)


def test_parse_real_schedule_project_info(schedule_result):
    assert "홍은동" in schedule_result.project_name
    assert schedule_result.project_start == date(2026, 6, 1)


def test_parse_real_schedule_activity_count(schedule_result):
    assert 20 <= len(schedule_result.activities) <= 50


def test_parse_real_schedule_activities_have_dates(schedule_result):
    with_dates = [a for a in schedule_result.activities if a.es_date and a.ef_date]
    assert len(with_dates) >= 15


def test_parse_real_schedule_disciplines(schedule_result):
    disciplines = {a.discipline for a in schedule_result.activities}
    assert "토공사" in disciplines or "골조공사" in disciplines
