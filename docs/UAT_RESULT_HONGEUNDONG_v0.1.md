# HongEundong 355 Schedule UAT Result

Tested against `v0.1.0-rc1` plus the Korean timeline Excel import fix.

## Source

| Item | Value |
| --- | --- |
| Excel file | `C:\MirTalk\Download\홍은동 355번지 가로주택_전체공정표.xlsx` |
| Temp copy used for automation | `C:\tmp\hongeundong_schedule.xlsx` |
| Tested sheet | Active sheet: `전체예정공정표(홍은동 가로주택정비사업-WORST)` |
| Project start date | `2026-06-01` |
| Calendar | Korean 5-day |

## Result

| Metric | Value |
| --- | --- |
| Import status | Pass |
| Imported activities | 49 |
| Imported relationships | 0 |
| Failed rows | 0 |
| Warnings | 2 |
| CPM status | Pass |
| CPM total duration | 1700 workdays |
| CPM completion date | `2033-04-27` |
| Critical Path activity count | 1 |
| Gantt traces | 49 |
| S-Curve rows | 0 |
| Excel report status | Pass |
| Excel report sheets | `요약`, `WBS`, `Activity 상세`, `관계`, `S-Curve 데이터` |

Report output from this run:

```text
C:\tmp\smart_scheduler_uat\20260520_114857\reports\hongeundong-355-uat-650d5963_report.xlsx
```

## Findings

- The original workbook is a Korean 10-day timeline style schedule, not a
  normal `code/name/duration` table.
- The importer now auto-detects headers such as `공 종`, `항 목`, `구 분` and
  imports row-level activities without requiring a column mapping preset.
- Relationships are not inferable from this workbook layout, so they are left
  empty and must be reviewed manually.
- Cost data is not present in the imported timeline rows, so S-Curve output has
  no rows. This is an input-data limitation, not a chart failure.
- CPM calculation succeeds technically, but the completion date is not field
  reliable until relationships and schedule-position constraints are reviewed.

## Release Decision

Do not tag `v0.1.0` solely from this run. The UAT uncovered one necessary import
fix, and the next release candidate should include this fix before final UAT.
