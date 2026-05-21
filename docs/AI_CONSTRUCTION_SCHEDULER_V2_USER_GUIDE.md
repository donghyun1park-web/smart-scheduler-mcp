# AI Construction Scheduler v2 User Guide

## Scope

The v2.0 MVP adds field-progress, cost, delay, recovery-draft, Excel,
dashboard, and MCP workflows on top of the existing Smart Node-Scheduler v0.1
CPM, SQLite, MCP, Streamlit, Plotly, and Excel report foundation.

The v2.1 stabilization pass adds DB-backed dashboard loading, audience-specific
report prose, shared number conversion helpers, and additional field recovery
templates without replacing the v2 SQLite schema.

The v2.2 field stabilization pass adds safe import conflict policies, dry-run
validation, import pre-backup, change-log MCP access, a real DB smoke-test
script, protected Excel templates, and simple EVM summaries.

## Environment

Use the project virtual environment with Python `>=3.11,<3.13`.

```powershell
.\.venv\Scripts\python.exe --version
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m ruff check .
.\.venv\Scripts\python.exe -m mypy .
```

Python 3.14 or Python 2.7 results are not acceptance evidence.

## Excel Field Template

Create a field-input workbook:

```powershell
.\.venv\Scripts\python.exe -c "from core.excel_io import create_field_input_template; print(create_field_input_template('samples\\field_input_template.xlsx', project_name='Demo Site'))"
```

Workbook sheets:

- `01_실적입력`
- `02_원가입력`
- `03_자재검측`
- `04_공정표`
- `05_대시보드`
- `06_부진공정`
- `07_보고서`

Yellow cells are input fields. Green cells are Python-calculated or summary
fields. Red/orange styling is reserved for error and attention states.

## Weekly Report

Generate the sample weekly report:

```powershell
.\.venv\Scripts\python.exe -c "import json; from core.reporting import create_weekly_construction_report; data=json.load(open('samples\\ai_construction_site_sample.json', encoding='utf-8')); print(create_weekly_construction_report(data, 'samples\\ai_construction_weekly_report.xlsx', report_style='internal'))"
```

Report sheets include:

- `05_대시보드`
- `금주 실적`
- `부진공정 TOP 10`
- `만회대책 초안`
- `원가현황`
- `다음 주 예정공정`
- `간트 데이터`
- `07_보고서`

`report_style` controls the report wording:

- `internal`: field/internal wording with direct action and owner follow-up.
- `hq`: headquarters wording focused on progress, cost execution, billing, and
  management risk.
- `client`: official owner/supervisor wording that avoids internal cost,
  blame, and final-decision phrasing.

## Excel Input To SQLite

After a field workbook has been filled in, import it into a `.scheduler` DB:

```powershell
.\.venv\Scripts\python.exe -c "from core.importer import import_field_input_to_db; print(import_field_input_to_db('path\\to\\project.scheduler', 'path\\to\\field_input.xlsx', project_id='project-1'))"
```

Useful v2.2 import options:

```powershell
# Validate only. No DB changes and no backup.
.\.venv\Scripts\python.exe -c "from core.importer import import_field_input_to_db; print(import_field_input_to_db('path\\to\\project.scheduler', 'path\\to\\field_input.xlsx', dry_run=True))"

# Keep existing duplicate daily records.
.\.venv\Scripts\python.exe -c "from core.importer import import_field_input_to_db; print(import_field_input_to_db('path\\to\\project.scheduler', 'path\\to\\field_input.xlsx', conflict_policy='skip', actor='site-manager'))"

# Replace duplicate daily records and write change_log entries.
.\.venv\Scripts\python.exe -c "from core.importer import import_field_input_to_db; print(import_field_input_to_db('path\\to\\project.scheduler', 'path\\to\\field_input.xlsx', conflict_policy='replace', actor='site-manager'))"
```

Daily-record conflicts are detected by `activity_id + work_date`. The default
policy is `fail` so existing records are not silently overwritten.

Then generate a DB-backed weekly report:

```powershell
.\.venv\Scripts\python.exe -c "from core.importer import generate_weekly_report_from_db; print(generate_weekly_report_from_db('path\\to\\project.scheduler', 'path\\to\\weekly_from_db.xlsx', report_style='hq'))"
```

The import flow reads `01_실적입력`, `02_원가입력`, and `03_자재검측`, validates
sheet/header structure, stores records in v2 SQLite tables, and records an
import event in `change_log`.

Before a non-dry-run import, v2.2 creates a backup under the project `backups`
folder and returns `backup_path` in the import result.

## Site-Manager Dashboard

Run the dashboard:

```powershell
.\.venv\Scripts\python.exe -m streamlit run viewer/pages/08_site_manager_dashboard.py
```

The dashboard displays:

- Planned progress
- Actual progress
- Progress variance
- Cost execution rate
- Billing rate
- Delayed activity count
- Risk discipline
- Key risks
- Green/yellow/orange/red status

In v2.1, the Streamlit page supports two data sources:

- `SQLite DB`: enter a `.scheduler` DB path, optional `project_id`, and
  `as_of_date`; then use discipline, zone, and risk filters.
- `JSON/sample`: keep the existing sample JSON or uploaded JSON workflow for
  compatibility.

You can also load dashboard data directly in Python:

```powershell
.\.venv\Scripts\python.exe -c "from viewer.components.site_manager_dashboard import load_site_dashboard_data_from_db; print(load_site_dashboard_data_from_db('path\\to\\project.scheduler', project_id='project-1'))"
```

The DB-backed dashboard can generate reports with `internal`, `hq`, or `client`
style and expose the result through the Streamlit download button.

## Real DB Smoke Test

Never test directly against the source `.scheduler` file. Use the smoke script:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --excel path\to\field_input.xlsx --out-dir smoke_outputs
```

Add `--apply` only when you want to apply the Excel import to the copied DB
after dry-run validation.

## MCP Tools

The v2.0 MVP registers these tools:

- `input_daily_record`
- `detect_delays`
- `suggest_recovery`
- `generate_weekly_report`
- `import_excel_input_to_db`
- `generate_weekly_report_from_db`
- `list_change_log_tool`
- `summarize_site_status`

`suggest_recovery` returns candidate recovery drafts and assumptions only. Field
leadership must review and decide whether to apply any plan.

v2.1 recovery templates cover material, manpower, predecessor, equipment,
inspection/approval, design change, subcontractor, weather, and general delay
reasons. Outputs continue to use "초안", "후보", "검토 필요", and approval-required
wording.

## Known Limitations

- Daily/cost/material/inspection workbook rows can be imported into SQLite, but
  conflict resolution is intentionally simple MVP behavior.
- DB-backed dashboard loading assumes the current v2 schema, where activities
  are project-file scoped rather than separately project-scoped inside the DB.
- Weekly report charts and print layouts are intentionally simple.
- Full EVM, BIM, weather APIs, photo handling, cloud collaboration, and user
  authentication are outside MVP scope.
