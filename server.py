from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools.analysis_tools import calculate_cpm, get_critical_path
from tools.calibration_tools import calibrate_completion_date
from tools.construction_tools import (
    detect_delays,
    generate_weekly_report,
    generate_weekly_report_from_db,
    input_daily_record,
    import_excel_input_to_db,
    list_change_log_tool,
    suggest_recovery,
    summarize_site_status,
)
from tools.billing_tools import apply_billing, billing_s_curve, billing_summary, calculate_billing
from tools.cost_tools import analyze_evm_from_db, get_evm_s_curve_data, summarize_cost_by_discipline
from tools.diagnostic_tools import (
    check_data_health,
    explain_evm_from_db,
    get_workflow_status,
    suggest_next_actions,
)
from tools.dashboard_tools import (
    get_dashboard_report,
    get_delayed_activities,
    get_discipline_progress,
    get_site_briefing,
)
from tools.field_uat_tools import run_field_uat_workflow
from tools.import_tools import import_budget_excel, import_excel, import_schedule_excel
from tools.material_tools import (
    add_inspection,
    add_material,
    get_activity_logistics,
    list_inspections_tool,
    list_materials_tool,
    update_inspection,
    update_material,
)
from tools.progress_tools import get_activity_progress, get_today_schedule, set_activity_progress
from tools.project_tools import create_project, list_projects, load_project
from tools.relationship_tools import generate_activity_relationships, suggest_activity_relationships
from tools.report_tools import generate_report
from tools.sequence_tools import apply_sequences


def build_server() -> FastMCP:
    mcp = FastMCP("smart-scheduler-mcp")
    mcp.tool()(list_projects)
    mcp.tool()(load_project)
    mcp.tool()(create_project)
    mcp.tool()(import_excel)
    mcp.tool()(import_schedule_excel)
    mcp.tool()(import_budget_excel)
    mcp.tool()(apply_sequences)
    mcp.tool()(calculate_cpm)
    mcp.tool()(get_critical_path)
    mcp.tool()(analyze_evm_from_db)
    mcp.tool()(get_evm_s_curve_data)
    mcp.tool()(summarize_cost_by_discipline)
    mcp.tool()(suggest_activity_relationships)
    mcp.tool()(generate_activity_relationships)
    mcp.tool()(generate_report)
    mcp.tool()(calibrate_completion_date)
    mcp.tool()(run_field_uat_workflow)
    mcp.tool()(input_daily_record)
    mcp.tool()(detect_delays)
    mcp.tool()(suggest_recovery)
    mcp.tool()(generate_weekly_report)
    mcp.tool()(import_excel_input_to_db)
    mcp.tool()(generate_weekly_report_from_db)
    mcp.tool()(list_change_log_tool)
    mcp.tool()(summarize_site_status)
    # v2.4: Billing
    mcp.tool()(calculate_billing)
    mcp.tool()(apply_billing)
    mcp.tool()(billing_summary)
    mcp.tool()(billing_s_curve)
    # v2.4: Dashboard
    mcp.tool()(get_site_briefing)
    mcp.tool()(get_dashboard_report)
    mcp.tool()(get_discipline_progress)
    mcp.tool()(get_delayed_activities)
    # v2.4: Materials & Inspections
    mcp.tool()(add_material)
    mcp.tool()(list_materials_tool)
    mcp.tool()(update_material)
    mcp.tool()(add_inspection)
    mcp.tool()(list_inspections_tool)
    mcp.tool()(update_inspection)
    mcp.tool()(get_activity_logistics)
    # v2.5: Operations center diagnostics
    mcp.tool()(check_data_health)
    mcp.tool()(suggest_next_actions)
    mcp.tool()(explain_evm_from_db)
    mcp.tool()(get_workflow_status)
    # Quick progress entry / today schedule
    mcp.tool()(set_activity_progress)
    mcp.tool()(get_activity_progress)
    mcp.tool()(get_today_schedule)
    return mcp


if __name__ == "__main__":
    build_server().run()
