# AI Construction Scheduler v2.2

## Summary

This PR upgrades `smart-scheduler-mcp` from the original Smart Node-Scheduler
v0.1 workflow into the AI Construction Scheduler v2.2 field-ready MVP.

The branch preserves the existing CPM, SQLite, Streamlit, MCP, and Excel report
behavior while adding Excel-centered field input, SQLite v2 field tables,
construction progress/cost/delay/recovery calculations, DB-backed reports,
DB-backed site-manager dashboard loading, import safety, real DB smoke-test
support, and simple EVM metrics.

## Why

Field users need to work through Excel and `.scheduler` files without silent
data loss. v2.2 therefore focuses on safe import behavior, validation before DB
changes, automatic backups, change-log visibility, and a smoke-test path that
never modifies the original field DB.

## Major Changes from v0.1 to v2.2

| 영역 | v0.1 | v2.2 |
|---|---|---|
| 대상 | MEP 공정표/CPM/Gantt | 토목·건축·기계·소방·전기 통합 현장관리 |
| DB | 기본 공정표 중심 | `SCHEMA_VERSION = 2`, 실적·원가·자재·검측·변경이력 |
| Excel | 보고서 출력 중심 | 입력 템플릿, import, 보고서, 시각 품질 개선 |
| MCP | 10 tools 수준의 기본 공정표 도구 | 18 tools, 현장 입력/보고/변경이력 도구 포함 |
| 보고서 | 기본 Excel report | 내부/본사/발주처 style, DB 기반 주간보고서 |
| 리스크 | CPM 중심 | 부진공정, 원가위험, 만회대책 후보 |
| EVM | 없음 | PV/EV/AC/SV/CV/SPI/CPI 계산 |
| Smoke Test | 없음 | 실제 `.scheduler` 복사본 기반 smoke script |

## Breaking Change / Migration Notice

SCHEMA_VERSION이 1에서 2로 변경되었습니다. 기존 `.scheduler` 파일을 v2.2
코드로 열면 `initialize_database()` 과정에서 v2 스키마로 자동 승격됩니다.
기존 파일을 열기 전 원본 `.scheduler` 파일을 별도로 백업하는 것을
권장합니다.

No v2.2 schema bump is required beyond `SCHEMA_VERSION = 2`; v2.2 adds import
safety, reports, smoke testing, and EVM logic on top of the v2 schema.

## MCP Tools

This branch registers 18 MCP tools:

1. `apply_sequences`
2. `calculate_cpm`
3. `calibrate_completion_date`
4. `create_project`
5. `detect_delays`
6. `generate_report`
7. `generate_weekly_report`
8. `generate_weekly_report_from_db`
9. `get_critical_path`
10. `import_excel`
11. `import_excel_input_to_db`
12. `input_daily_record`
13. `list_change_log_tool`
14. `list_projects`
15. `load_project`
16. `run_field_uat_workflow`
17. `suggest_recovery`
18. `summarize_site_status`

## Quality Gates

Verified on `feature/ai-construction-scheduler-v2` at commit `b1678a7` using
the project `.venv` Python:

| Gate | Result |
|---|---|
| pytest | `153 passed` |
| ruff | `All checks passed!` |
| mypy | `Success: no issues found in 114 source files` |

## Real DB Smoke Test

The real DB smoke test must never run against the original `.scheduler` file
directly. The script copies the DB into the output directory first, then runs
dashboard loading, import dry-run, three report styles, recovery template
checks, and result JSON generation on the copied DB.

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --excel path\to\field_input.xlsx --out-dir smoke_outputs\real_v2_2_20260521
```

Use `--apply` only after dry-run succeeds, and only against the copied DB:

```powershell
.\.venv\Scripts\python.exe scripts\smoke_test_real_scheduler.py --db path\to\real.scheduler --excel path\to\field_input.xlsx --out-dir smoke_outputs\real_v2_2_apply_20260521 --apply
```

Current PR preparation smoke check used a generated demo DB because no real
field `.scheduler` path was provided. The demo smoke run passed with
`original_unchanged=true`, three report styles generated, and no forbidden
recovery wording.

## Backward Compatibility

- Existing CPM and critical-path behavior is preserved.
- Existing v0.1 SQLite project storage and base Excel report writer are
  preserved.
- `Activity` is not bloated with field-specific columns; v2 data uses separate
  tables such as `daily_records`, `cost_items`, `materials`, `inspections`,
  `change_log`, `project_settings`, and `baseline_snapshots`.
- AI recovery output remains candidate/draft language only.
- Import defaults to `conflict_policy="fail"` so duplicate daily records are
  not silently overwritten.

## Merge Recommendation

이번 브랜치는 `b37edfb` → `a65275c` → `6b44244` → `b1678a7`의 4개 커밋이
각각 MVP, 안정화, v2.1, v2.2 성격을 가지므로 squash merge보다 merge commit을
권장합니다.

## Follow-up v2.3 Candidates

1. Change Log 날짜 범위 필터
2. EVM 대시보드/엑셀 시각화
3. `progress_pct` 단위 모호성 보강
4. 다중 프로젝트 비교 뷰
5. 실제 DB smoke test 발견사항 반영
