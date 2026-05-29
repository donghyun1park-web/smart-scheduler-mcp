"""Tests for core.budget_importer."""
from __future__ import annotations

from pathlib import Path

import pytest

from core.budget_importer import (
    _aggregate_categories,
    _infer_discipline,
    _normalize_budget_discipline,
    ParsedBudgetItem,
    parse_budget_excel,
)


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def test_infer_discipline_from_filename():
    assert _infer_discipline("실행예산내역서(기계설비).xlsx") == "기계설비"
    assert _infer_discipline("실행예산내역서(전기,통신,전기소방).xlsx") == "전기설비"
    assert _infer_discipline("실행예산내역서(가설,토목,파일공사).xlsx") == "토목"
    assert _infer_discipline("실행예산내역서 (PC공사등).xlsx") == "건축"


def test_normalize_budget_discipline():
    assert _normalize_budget_discipline("기계설비") == "기계설비"
    assert _normalize_budget_discipline("전기") == "전기설비"
    assert _normalize_budget_discipline("토목") == "토목"
    assert _normalize_budget_discipline("") == "공통"


def test_aggregate_categories():
    items = [
        ParsedBudgetItem(1, "A", "", "", "001", "Cat1", "변경", 0, 0, 100, 0, 0, 200, "", "건축"),
        ParsedBudgetItem(2, "B", "", "", "002", "Cat1", "변경", 0, 0, 300, 0, 0, 400, "", "건축"),
        ParsedBudgetItem(3, "C", "", "", "003", "Cat2", "변경", 0, 0, 500, 0, 0, 600, "", "건축"),
    ]
    cats = _aggregate_categories(items)
    assert len(cats) == 2
    cat1 = next(c for c in cats if c.category == "Cat1")
    assert cat1.contract_amount == 400
    assert cat1.execution_amount == 600
    assert cat1.item_count == 2


# ---------------------------------------------------------------------------
# Integration tests: parse real budget files (if available)
# ---------------------------------------------------------------------------

BUDGET_FILES = {
    "건축": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서 (PC공사등).xlsx",
    "토목": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(가설,토목,파일공사).xlsx",
    "기계설비": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(기계설비).xlsx",
    "전기설비": r"C:/Users/User/OneDrive/바탕 화면/DB/실행예산내역서(전기,통신,전기소방).xlsx",
}


@pytest.fixture(params=list(BUDGET_FILES.keys()))
def budget_result(request):
    discipline = request.param
    path = BUDGET_FILES[discipline]
    if not Path(path).exists():
        pytest.skip(f"Budget file not available: {path}")
    return parse_budget_excel(path, discipline=discipline)


def test_parse_real_budget_has_items(budget_result):
    assert len(budget_result.items) > 0


def test_parse_real_budget_has_categories(budget_result):
    assert len(budget_result.categories) > 0


def test_parse_real_budget_execution_positive(budget_result):
    assert budget_result.total_execution_amount > 0


def test_parse_real_budget_items_have_names(budget_result):
    named = [i for i in budget_result.items if i.name]
    assert len(named) == len(budget_result.items)
