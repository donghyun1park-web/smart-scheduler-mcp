from __future__ import annotations

import json

from viewer.components.site_manager_dashboard import (
    DEFAULT_DASHBOARD_THRESHOLDS,
    build_site_manager_dashboard_summary,
)


def test_build_site_manager_dashboard_summary_has_required_metrics():
    summary = build_site_manager_dashboard_summary(_load_sample_data())

    assert summary["planned_progress_pct"] == 62.0
    assert summary["actual_progress_pct"] > 0
    assert summary["progress_variance_pct"] == round(
        summary["actual_progress_pct"] - summary["planned_progress_pct"],
        2,
    )
    assert summary["cost_execution_rate"] > 0
    assert summary["billing_rate"] > 0
    assert summary["delayed_activity_count"] >= 4
    assert summary["risk_discipline"]
    assert summary["key_risks"]


def test_dashboard_status_uses_configurable_green_yellow_orange_red_thresholds():
    data = _load_sample_data()
    thresholds = {**DEFAULT_DASHBOARD_THRESHOLDS, "yellow_min": -5, "orange_min": -10}

    summary = build_site_manager_dashboard_summary(data, thresholds=thresholds)

    assert summary["status"] in {"green", "yellow", "orange", "red"}
    assert summary["thresholds"]["yellow_min"] == -5
    if summary["progress_variance_pct"] < -10:
        assert summary["status"] == "red"


def _load_sample_data() -> dict[str, object]:
    with open("samples/ai_construction_site_sample.json", encoding="utf-8") as file:
        return json.load(file)
