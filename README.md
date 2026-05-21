# Smart Node-Scheduler v0.1

Python-based MEP schedule assistant MVP for SQLite-backed schedule storage,
CPM calculation, MCP tools, a Streamlit viewer, Plotly visualizations, and
Excel reporting.

## AI Construction Schedule v2.0 MVP

This branch extends the v0.1 scheduler into an Excel-centered construction
schedule MVP while preserving the existing CPM, SQLite, MCP, Streamlit, Plotly,
and v0.1 Excel report behavior.

### v2.1 Follow-Up Stabilization

The v2.1 pass keeps the v2 SQLite and Excel loop intact and adds:

- DB-backed Streamlit site-manager dashboard loading from a `.scheduler` DB.
- `report_style` audience variants: `internal`, `hq`, and `client`.
- Shared number conversion helpers in `core.number_utils`.
- Recovery templates for equipment, inspection/approval, design change,
  subcontractor, and weather delay reasons.

New v2.0 MVP entry points:

```powershell
# Create a field input workbook template.
.\.venv\Scripts\python.exe -c "from core.excel_io import create_field_input_template; print(create_field_input_template('samples\\field_input_template.xlsx', project_name='Demo Site'))"

# Generate a weekly construction report from the sample site data.
.\.venv\Scripts\python.exe -c "import json; from core.reporting import create_weekly_construction_report; data=json.load(open('samples\\ai_construction_site_sample.json', encoding='utf-8')); print(create_weekly_construction_report(data, 'samples\\ai_construction_weekly_report.xlsx', report_style='internal'))"

# Import a completed field-input workbook into SQLite and generate a DB-backed report.
.\.venv\Scripts\python.exe -c "from core.importer import import_field_input_to_db, generate_weekly_report_from_db; print(import_field_input_to_db('path\\to\\project.scheduler', 'path\\to\\field_input.xlsx', project_id='project-1')); print(generate_weekly_report_from_db('path\\to\\project.scheduler', 'path\\to\\weekly_from_db.xlsx', report_style='hq'))"

# Load dashboard-ready data directly from SQLite.
.\.venv\Scripts\python.exe -c "from viewer.components.site_manager_dashboard import load_site_dashboard_data_from_db; print(load_site_dashboard_data_from_db('path\\to\\project.scheduler', project_id='project-1'))"

# Run the site-manager dashboard.
.\.venv\Scripts\python.exe -m streamlit run viewer/pages/08_site_manager_dashboard.py
```

The sample data at `samples/ai_construction_site_sample.json` includes normal
work, delayed work, predecessor blocking, cost overrun, material delay,
inspection delay, missing owner, and baseline-change scenarios.

New MCP tools:

- `input_daily_record`
- `detect_delays`
- `suggest_recovery`
- `generate_weekly_report`
- `import_excel_input_to_db`
- `generate_weekly_report_from_db`
- `summarize_site_status`

`suggest_recovery` only returns draft/candidate/review-required language. It
does not confirm or order a recovery action.

See:

- [AI Construction Scheduler v2 User Guide](docs/AI_CONSTRUCTION_SCHEDULER_V2_USER_GUIDE.md)
- [AI Construction Scheduler v2 Data Model](docs/AI_CONSTRUCTION_SCHEDULER_V2_DATA_MODEL.md)
- [Release Notes v0.2.1](docs/RELEASE_NOTES_v0.2.1.md)
- [Release Notes v0.2.0 MVP](docs/RELEASE_NOTES_v0.2.0-MVP.md)

## v0.1 Scope

- Core dataclasses and SQLite `.scheduler` project storage
- FS, SS, FF relationship support with lag; SF is intentionally out of scope
- CPM calculation through the `core.cpm` wrapper
- Korean calendar and workday-to-date mapping
- MCP tools for project, import, sequence, analysis, and report workflows
- Streamlit Viewer for project editing and CPM review
- Plotly Gantt and S-Curve views
- Excel report generation with five sheets

Out of scope for v0.1: P6 XER, PDF output, AI recommendations, resource
leveling, advanced multi-calendar constraints, PyInstaller packaging, and
natural-language what-if workflows.

## Documentation

- [Release Notes v0.1.0](docs/RELEASE_NOTES_v0.1.0.md)
- [Release Notes v0.1.1](docs/RELEASE_NOTES_v0.1.1.md)
- [HongEundong Completion-Date Calibration](docs/HONGEUNDONG_COMPLETION_DATE_CALIBRATION.md)
- [Calibration Diagnostics](docs/CALIBRATION_DIAGNOSTICS.md)
- [Execution Guide](docs/SMART_SCHEDULER_EXECUTION_GUIDE.md)

## Environment Gate

This project must be developed and verified with Python `>=3.11,<3.13`.
Python 3.14 or Python 2.7 test results are not acceptance evidence for this
repository.

Windows setup:

```powershell
py -0p
where.exe python
where.exe py

py -3.12 --version
py -3.12 -m venv .venv

.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip install --upgrade pip setuptools wheel
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
```

Do not add `python>=3.11` to `requirements.txt`; runtime version limits belong
in `pyproject.toml` as `requires-python`.

The latest v0.1 RC verification used Python `3.12.10`.

## MCP Server

Run the MCP server from the repository root:

```powershell
.\.venv\Scripts\python.exe server.py
```

The server registers the v0.1 tool surface:

- `list_projects`
- `load_project`
- `create_project`
- `import_excel`
- `apply_sequences`
- `calculate_cpm`
- `get_critical_path`
- `generate_report`

`generate_report` creates the Week 4 Excel report instead of returning the
earlier Week 2 placeholder.

## Streamlit Viewer

Run the viewer from the repository root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run viewer/app.py
```

The viewer supports project loading, WBS and activity editing, relationships,
calendar settings, Excel import, standard sequence application, CPM execution,
Gantt, S-Curve, and Excel report generation.

## Excel Report

Reports can be generated through the MCP `generate_report` tool, the Streamlit
Report panel, or directly from Python:

```powershell
.\.venv\Scripts\python.exe -c "from tools.report_tools import generate_report; print(generate_report('path\\to\\project.scheduler'))"
```

If no output path is provided, the report is written to a `reports` folder next
to the project database. The workbook contains five sheets:

1. `요약`
2. `WBS`
3. `Activity 상세`
4. `관계`
5. `S-Curve 데이터`

Critical Path activities are highlighted in the Activity detail sheet.

## Test And Quality Gates

Run the full acceptance checks with the project virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

Latest verified v0.1 RC result:

- Python: `3.12.10`
- `pip check`: `No broken requirements found.`
- `pytest`: `41 passed`
- skipped tests: `0`
- `ruff`: `All checks passed!`
- `mypy`: `Success: no issues found in 64 source files`
- Streamlit smoke: `streamlit_started=True`

## UAT Before Final Release

Before declaring the final v0.1 release, run one real project through this flow:

1. Create or load a project.
2. Import a real conceptual schedule Excel file.
3. Save the column mapping preset.
4. Apply a plumbing or HVAC standard sequence if useful.
5. Manually correct activities and relationships.
6. Calculate CPM.
7. Review Gantt and S-Curve.
8. Generate the Excel report.
9. Open the workbook and confirm the five sheets and Critical Path highlight.
10. Record elapsed time and the most inconvenient manual correction step.
