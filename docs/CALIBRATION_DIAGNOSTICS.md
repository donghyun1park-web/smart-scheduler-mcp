# Calibration Diagnostics

## Purpose

Calibration diagnostics help a planner decide whether an imported schedule is
ready for CPM review or still needs field correction. The diagnostics do not
repair the schedule automatically. They identify data quality risks and make
calibration patch problems visible before a field-trust finish date is
interpreted.

## Schedule Diagnostics

The calibration workflow now returns diagnostics for both the imported schedule
and the calibrated schedule:

```text
diagnostics.before
diagnostics.after
```

Each diagnostics block includes:

```text
task_count
dependency_count
tasks_without_predecessor_count
tasks_without_successor_count
isolated_task_count
missing_duration_count
zero_or_negative_duration_count
missing_cost_count
duplicate_task_id_count
cycle_detected
disconnected_component_count
relationship_coverage_ratio
cost_coverage_ratio
warnings
```

## Relationship Coverage

Relationship coverage is calculated as:

```text
dependency_count / task_count
```

This is a practical field UAT signal, not a CPM correctness proof. Low coverage
means many imported tasks are not connected by explicit logic and the CPM finish
date may not be field-trustworthy yet.

When coverage is below the configured threshold, the workflow emits:

```text
LOW_RELATIONSHIP_COVERAGE
```

## Cost Coverage

Cost coverage is calculated as:

```text
tasks_with_cost / task_count
```

Cost-free imported schedules can still be used for CPM and Gantt review, but
S-Curve output will be incomplete or empty until costs are mapped or entered.

When coverage is below the configured threshold, the workflow emits:

```text
LOW_COST_COVERAGE
```

## Warning Severity and Codes

Warnings use a structured record:

```json
{
  "severity": "warning",
  "code": "LOW_RELATIONSHIP_COVERAGE",
  "message": "Relationship coverage is below recommended threshold.",
  "task_id": "TASK-001",
  "applied_order": 3
}
```

Supported severities:

```text
info
warning
error
```

Current diagnostic and patch validation codes include:

```text
UNKNOWN_TASK_ID
DUPLICATE_DEPENDENCY_OVERRIDE
CONFLICTING_DURATION_OVERRIDE
CONFLICTING_LAG_OVERRIDE
INVALID_DURATION
INVALID_LAG
DEPENDENCY_CYCLE
LOW_RELATIONSHIP_COVERAGE
LOW_COST_COVERAGE
DUPLICATE_TASK_ID
UNKNOWN_RELATIONSHIP
UNSUPPORTED_DEPENDENCY_TYPE
```

Error-level warnings block a clean calibration result. Warning-level diagnostics
can still produce before/after CPM comparison output, but the field UAT status
will explain what needs correction.

## Field UAT Status

`comparison.field_uat_status` summarizes whether the imported or calibrated
schedule is ready for review.

Possible values:

```text
ready_for_review
needs_relationship_correction
needs_cost_correction
blocked_by_cycle
blocked_by_invalid_patch
```

Status rules:

```text
blocked_by_cycle:
- cycle detection is present after calibration

blocked_by_invalid_patch:
- error-level patch validation warnings are present

needs_relationship_correction:
- relationship coverage remains below the threshold

needs_cost_correction:
- cost coverage remains below the threshold

ready_for_review:
- no error-level warnings
- no dependency cycle
- relationship and cost coverage are above thresholds
```

## Cycle Detection

If calibration creates a dependency cycle, CPM output is not reliable. The
workflow returns:

```text
field_uat_status = blocked_by_cycle
warning code = DEPENDENCY_CYCLE
ok = false
```

The user must remove or correct the cyclic dependency before treating the finish
date as meaningful.

## Target Finish Date

Target finish date is a validation reference, not an automatic scheduling
constraint.

현장 신뢰 준공일은 검증 기준이며, CPM 일정을 강제로 맞추기 위한 제약조건이 아니다.

The workflow never adjusts durations, dependencies, lags, or critical path
membership just to match a target date. The target date is used only to calculate
before/after delta values.

## Limitations

- Diagnostics identify schedule data quality risks; they do not automatically
  fix schedules.
- Relationship-free Excel still requires user correction for reliable CPM.
- Cost-free Excel still requires cost mapping or manual cost input for S-Curve.
- The HongEundong fixtures are sanitized minimal samples, not full real-project
  datasets.
- Excel report calibration summary sheets are not part of this stabilization
  pass; the JSON/dict calibration report is the source of truth for v0.1.2.
