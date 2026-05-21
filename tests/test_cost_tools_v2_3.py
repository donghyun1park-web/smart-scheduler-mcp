from __future__ import annotations

import json
from datetime import date

from core import db
from core.models import Activity, Calendar, CostItem, DailyRecord, Project, WBS
from tools.cost_tools import (
    analyze_evm_from_db,
    get_evm_s_curve_data,
    summarize_cost_by_discipline,
)


def test_analyze_evm_from_db_returns_snapshot_keys(tmp_path):
    db_path = _cost_db(tmp_path)

    result = analyze_evm_from_db(str(db_path), as_of_date="2026-01-15")

    assert result["ok"] is True
    assert result["totals"]["pv"] > 0
    assert result["totals"]["ev"] > 0
    assert result["totals"]["ac"] == 700.0
    for key in ("pv", "ev", "ac", "sv", "cv", "spi", "cpi", "status"):
        assert key in result["totals"]
    json.dumps(result, ensure_ascii=False)


def test_get_evm_s_curve_data_returns_chart_ready_rows(tmp_path):
    db_path = _cost_db(tmp_path)

    result = get_evm_s_curve_data(
        str(db_path),
        start_date="2026-01-01",
        end_date="2026-01-03",
    )

    assert result["ok"] is True
    assert [row["date"] for row in result["series"]] == [
        "2026-01-01",
        "2026-01-02",
        "2026-01-03",
    ]
    assert all({"date", "pv", "ev", "ac"} <= set(row) for row in result["series"])
    json.dumps(result, ensure_ascii=False)


def test_summarize_cost_by_discipline_handles_zero_denominators(tmp_path):
    db_path = _cost_db(tmp_path, include_zero=True)

    result = summarize_cost_by_discipline(str(db_path))

    assert result["ok"] is True
    assert len(result["rows"]) >= 1
    assert all("discipline" in row for row in result["rows"])
    assert all("status" in row for row in result["rows"])
    json.dumps(result, ensure_ascii=False)


def _cost_db(tmp_path, *, include_zero: bool = False):
    path = tmp_path / "cost.scheduler"
    db.initialize_database(path)
    db.create_calendar(path, Calendar("cal", "Calendar", "1111100"))
    db.create_project(path, Project("proj", "Cost Pilot", date(2026, 1, 1), "cal"))
    db.create_wbs(path, WBS("wbs", None, "ROOT", "ROOT"))
    db.create_activity(
        path,
        Activity(
            "a1",
            "A001",
            "Structure",
            "wbs",
            "architecture",
            "1F",
            10,
            es_date=date(2026, 1, 1),
            ef_date=date(2026, 1, 10),
        ),
    )
    db.upsert_cost_item(
        path,
        CostItem("c1", "a1", contract_amount=1200, execution_budget=1000, invested_cost=700, billing_amount=400),
    )
    db.create_daily_record(path, DailyRecord("d1", "a1", date(2026, 1, 10), planned_qty=100, actual_qty=50))
    if include_zero:
        db.create_activity(
            path,
            Activity(
                "a2",
                "A002",
                "Zero budget",
                "wbs",
                "mechanical",
                "1F",
                5,
                es_date=date(2026, 1, 1),
                ef_date=date(2026, 1, 5),
            ),
        )
        db.upsert_cost_item(path, CostItem("c2", "a2"))
    return path
