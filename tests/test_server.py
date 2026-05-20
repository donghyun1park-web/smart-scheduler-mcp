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
