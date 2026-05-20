from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from tools.analysis_tools import calculate_cpm, get_critical_path
from tools.calibration_tools import calibrate_completion_date
from tools.import_tools import import_excel
from tools.project_tools import create_project, list_projects, load_project
from tools.report_tools import generate_report
from tools.sequence_tools import apply_sequences


def build_server() -> FastMCP:
    mcp = FastMCP("smart-scheduler-mcp")
    mcp.tool()(list_projects)
    mcp.tool()(load_project)
    mcp.tool()(create_project)
    mcp.tool()(import_excel)
    mcp.tool()(apply_sequences)
    mcp.tool()(calculate_cpm)
    mcp.tool()(get_critical_path)
    mcp.tool()(generate_report)
    mcp.tool()(calibrate_completion_date)
    return mcp


if __name__ == "__main__":
    build_server().run()
