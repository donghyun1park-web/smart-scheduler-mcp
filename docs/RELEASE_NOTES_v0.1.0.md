# Smart Node-Scheduler v0.1.0 Release Notes

`v0.1.0` is the first internal MVP release of Smart Node-Scheduler. It is
intended as a practical bridge between real-world Excel schedules and a
repeatable CPM/Gantt/S-Curve/reporting workflow.

## Release Definition

This release means:

- Real Excel schedule files can be imported into a SQLite `.scheduler` project.
- Users can review and correct WBS, activities, relationships, calendars, and
  costs.
- Corrected project data can be recalculated with CPM.
- The same project data can produce Gantt, S-Curve, and Excel report outputs.

This release does not mean:

- A relationship-free timeline Excel file automatically produces a
  field-trusted completion date.
- Smart Node-Scheduler replaces P6.
- AI logic, P6 XER, PDF, resource leveling, or advanced constraints are
  included.

## Main Features

- SQLite project storage
- Core project models and CRUD helpers
- CPM wrapper with FS, SS, FF and lag support
- Korean calendar and workday/date mapping
- MCP tool surface:
  - `list_projects`
  - `load_project`
  - `create_project`
  - `import_excel`
  - `apply_sequences`
  - `calculate_cpm`
  - `get_critical_path`
  - `generate_report`
- Streamlit Viewer for editing and review
- Standard sequence application
- Standard column-based Excel import
- Korean timeline schedule import
- Plotly Gantt
- S-Curve data and chart
- Excel report with five sheets:
  - `요약`
  - `WBS`
  - `Activity 상세`
  - `관계`
  - `S-Curve 데이터`

## UAT Summary

HongEundong 355 real Excel UAT:

- Source file: `C:\MirTalk\Download\홍은동 355번지 가로주택_전체공정표.xlsx`
- Import mode: `korean_timeline`
- Imported activities: 49
- Failed rows: 0
- Initial relationships: 0
- Initial S-Curve rows: 0
- Excel report: generated
- Report sheets: all five verified

Relationship/cost correction UAT:

- Added FS relationships: 12
- Added cost activities: 12
- Total cost entered: 78,000,000
- S-Curve rows after correction: 400
- Excel relationship sheet rows: 12
- Excel S-Curve data sheet rows: 400
- Critical Path highlight rows: 1

## Known Limitations

- Korean timeline Excel files usually do not contain predecessor/relationship
  columns. Smart Node-Scheduler imports activities from those files, but
  meaningful Critical Path and completion date results require relationship
  correction.
- If an Excel file does not contain cost data, S-Curve output is empty until
  costs are mapped or manually entered.
- Completion dates are only as reliable as the imported or corrected schedule
  logic.
- Korean timeline import currently infers row-level durations from timeline
  spans. It does not infer predecessor candidates from bar positions.
- P6 XER, AI logic recommendations, PDF output, resource leveling, advanced
  multi-calendar constraints, and PyInstaller packaging are outside v0.1.

## Recommended Workflow

1. Create or load a project.
2. Import Excel.
3. Review import warnings.
4. Correct or add relationships.
5. Enter or map costs if S-Curve is needed.
6. Review calendar settings.
7. Calculate CPM.
8. Review Gantt and Critical Path.
9. Review S-Curve.
10. Generate the Excel report.
11. Open the report and verify the five sheets and Critical Path highlight.

## Verification

Latest v0.1 verification:

- Python: `3.12.10`
- `pip check`: `No broken requirements found.`
- `pytest`: `42 passed`
- skipped tests: `0`
- `ruff`: `All checks passed!`
- `mypy`: `Success: no issues found in 64 source files`
