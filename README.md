# Smart Node-Scheduler v0.1

Python-based MEP schedule assistant MVP for SQLite-backed schedule storage,
CPM calculation, MCP tools, a Streamlit viewer, Plotly visualizations, and
Excel reporting.

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
