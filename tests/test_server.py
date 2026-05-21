from __future__ import annotations

from server import build_server


def test_build_server_returns_mcp_instance():
    server = build_server()

    assert server.name == "smart-scheduler-mcp"


def test_build_server_registers_calibration_tool():
    server = build_server()

    assert "calibrate_completion_date" in server._tool_manager._tools


def test_build_server_registers_field_uat_tool():
    server = build_server()

    assert "run_field_uat_workflow" in server._tool_manager._tools


def test_build_server_registers_construction_v2_tools():
    server = build_server()

    for tool_name in {
        "input_daily_record",
        "detect_delays",
        "suggest_recovery",
        "generate_weekly_report",
        "import_excel_input_to_db",
        "generate_weekly_report_from_db",
        "summarize_site_status",
    }:
        assert tool_name in server._tool_manager._tools
