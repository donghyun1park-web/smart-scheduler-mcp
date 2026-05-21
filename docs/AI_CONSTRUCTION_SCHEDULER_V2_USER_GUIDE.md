# AI Construction Scheduler v2.0 MVP User Guide

## Scope

The v2.0 MVP adds field-progress, cost, delay, recovery-draft, Excel, dashboard,
and MCP workflows on top of the existing Smart Node-Scheduler v0.1 CPM,
SQLite, MCP, Streamlit, Plotly, and Excel report foundation.

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
.\.venv\Scripts\python.exe -c "import json; from core.reporting import create_weekly_construction_report; data=json.load(open('samples\\ai_construction_site_sample.json', encoding='utf-8')); print(create_weekly_construction_report(data, 'samples\\ai_construction_weekly_report.xlsx'))"
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

## MCP Tools

The v2.0 MVP registers these tools:

- `input_daily_record`
- `detect_delays`
- `suggest_recovery`
- `generate_weekly_report`
- `summarize_site_status`

`suggest_recovery` returns candidate recovery drafts and assumptions only. Field
leadership must review and decide whether to apply any plan.

## Known Limitations

- Daily records are validated and normalized through MCP but are not yet written
  into SQLite by the tool wrapper.
- The v2 dashboard reads normalized JSON sample data. Direct SQLite-backed
  dashboard loading is a follow-up.
- Weekly report charts and print layouts are intentionally simple.
- Full EVM, BIM, weather APIs, photo handling, cloud collaboration, and user
  authentication are outside MVP scope.
