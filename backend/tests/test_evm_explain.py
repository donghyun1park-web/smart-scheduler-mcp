from __future__ import annotations

import json

from core.evm_explain import explain_evm_snapshot_ko, explain_evm_totals_ko


def test_explain_evm_totals_describes_schedule_and_cost_risk():
    result = explain_evm_totals_ko(
        {"pv": 1000, "ev": 800, "ac": 1200, "spi": 0.8, "cpi": 0.67, "status": "risk"}
    )

    assert result["status"] == "risk"
    assert result["headline_ko"]
    assert result["recommended_actions_ko"]
    assert result["metrics_ko"]["pv"]
    json.dumps(result, ensure_ascii=False)


def test_explain_evm_snapshot_handles_healthy_and_missing_data():
    healthy = explain_evm_snapshot_ko(
        {"planned_value": 1000, "earned_value": 1100, "actual_cost": 900, "spi": 1.1, "cpi": 1.22}
    )
    missing = explain_evm_totals_ko({})

    assert healthy["status"] == "healthy"
    assert missing["status"] == "not_available"
    assert "데이터" in missing["summary_ko"]
