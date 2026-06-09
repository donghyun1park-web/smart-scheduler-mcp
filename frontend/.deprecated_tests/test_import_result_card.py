"""Tests for the import-result summary helper (pure function, no Streamlit)."""
from __future__ import annotations

from viewer.components.import_result_card import summarize_import_result


def test_summarize_v2_3_importer_shape():
    raw = {
        "ok": True,
        "dry_run": True,
        "imported": {"activities": 247, "wbs": 12, "cost_items": 0, "relationships": 198},
        "warnings": ["헤더 행 매핑 일부 누락"],
        "failed_rows": [],
        "backup_path": None,
    }
    s = summarize_import_result(raw)
    assert s["ok"] is True
    assert s["dry_run"] is True
    assert (s["activities"], s["wbs"], s["cost_items"], s["relationships"]) == (247, 12, 0, 198)
    assert s["warnings"] == ["헤더 행 매핑 일부 누락"]


def test_summarize_legacy_importer_shape():
    raw = {
        "ok": False,
        "added_activities": 3,
        "added_relationships": 2,
        "warnings": [],
        "failed_rows": [{"row": 5, "reason": "duration 누락"}],
    }
    s = summarize_import_result(raw)
    assert s["ok"] is False
    assert s["activities"] == 3
    assert s["relationships"] == 2
    assert len(s["failed_rows"]) == 1


def test_summarize_handles_missing_keys():
    s = summarize_import_result({})
    assert s["activities"] == 0
    assert s["warnings"] == []
    assert s["ok"] is True  # no errors/failed_rows means ok defaults True
