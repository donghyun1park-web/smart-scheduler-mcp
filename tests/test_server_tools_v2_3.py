from __future__ import annotations

from server import build_server


def test_build_server_registers_v2_3_tools_without_removing_existing_tools():
    server = build_server()
    tool_names = set(server._tool_manager._tools)

    for tool_name in {
        "import_excel",
        "import_excel_input_to_db",
        "import_schedule_excel",
        "import_budget_excel",
        "analyze_evm_from_db",
        "get_evm_s_curve_data",
        "summarize_cost_by_discipline",
        "suggest_activity_relationships",
        "generate_activity_relationships",
    }:
        assert tool_name in tool_names
