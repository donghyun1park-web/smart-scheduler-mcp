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
| Import mode | `korean_timeline` |
| Imported activities | 49 |
| Imported relationships | 0 |
| Failed rows | 0 |
| Warnings | 3 |
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
- The importer now auto-detects spaced Korean headers such as `공 종`, `항 목`,
  and `구 분`, then imports row-level activities without requiring a column
  mapping preset.
- Relationships are not inferable from this workbook layout, so
  `relationships=0` is an input-data limitation rather than an importer crash.
- Cost data is not present in the imported timeline rows, so `S-Curve rows=0`
  is expected until costs are mapped or entered manually.
- CPM calculation succeeds technically, but the Critical Path and completion
  date are not field reliable until relationships and schedule-position
  constraints are reviewed.

## Import Warnings

The Korean timeline import path should return warnings equivalent to:

```json
{
  "import_mode": "korean_timeline",
  "warnings": [
    "Detected Korean timeline schedule format; imported row-level activities with inferred durations.",
    "No predecessor/relationship column was found. CPM can run, but Critical Path and completion date require manual relationship correction.",
    "No cost column was found. S-Curve will be empty until costs are mapped or entered manually."
  ]
}
```

## Release Decision

Do not tag `v0.1.0` solely from this run. The UAT uncovered one necessary import
fix. Cut `v0.1.0-rc2`, then run a second UAT that manually corrects
relationships and costs before deciding on the final `v0.1.0` tag.
