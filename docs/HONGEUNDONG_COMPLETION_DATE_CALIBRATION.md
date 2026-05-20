# HongEundong Completion-Date Calibration Workflow

## Why This Exists

Smart Node-Scheduler `v0.1.0` can import real Excel schedules, then generate
CPM, Gantt, S-Curve, and Excel reports after users supplement missing planning
logic.

The HongEundong UAT showed a common field condition: the source Excel was a
Korean timeline schedule. It contained enough information to create row-level
activities, but it did not contain reliable predecessor relationships or cost
columns. The imported schedule was therefore usable as a starting point, not as
a field-trusted CPM schedule.

This workflow adds an explicit calibration layer for comparing imported CPM
results with user-corrected CPM results.

## Relationship To v0.1.0

`v0.1.0` remains the baseline internal MVP. This workflow does not change the
meaning of that release. It extends the UAT path by making these layers explicit:

1. Source/imported data
2. User correction patch
3. Derived calibrated schedule
4. Before/after CPM comparison report

The imported source schedule is not silently overwritten by calibration.

## Calibration Patch

A calibration patch can include:

- dependency overrides
- duration overrides
- lag overrides
- an optional target finish date
- notes or reasons for field assumptions

Each correction should preserve this idea:

```text
task_id
field
old_value
new_value
reason
source
```

## Target Finish Date

Target finish date is a validation reference, not an automatic scheduling
constraint.

현장 신뢰 준공일은 검증 기준이며, CPM 일정을 강제로 맞추기 위한 제약조건이 아니다.

The target finish date is used to calculate:

- imported finish date
- calibrated finish date
- delta before calibration
- delta after calibration

It must not be used to distort durations or invent dependencies without planner
review.

## Before/After Comparison

The calibration report includes:

- project name
- target finish date
- before finish date
- after finish date
- delta days before
- delta days after
- critical path before
- critical path after
- dependency count before
- dependency count after
- duration override count
- lag override count
- warnings

## MCP Tool

The MCP tool entry point is:

```text
calibrate_completion_date
```

Example input:

```json
{
  "project_path": "path/to/project.scheduler",
  "target_finish_date": "2026-06-12",
  "dependency_overrides": [
    {
      "predecessor_id": "a",
      "successor_id": "b",
      "dependency_type": "FS",
      "lag_days": 0,
      "reason": "field sequence correction"
    }
  ],
  "duration_overrides": [],
  "lag_overrides": [],
  "notes": "HongEundong UAT calibration"
}
```

## Limitations

- Supported dependency types follow the current CPM engine: FS, SS, and FF.
- SF is not supported in this workflow.
- The workflow does not infer a complete dependency network from timeline bars.
- The workflow does not guarantee field-correct completion dates without user
  review.
- Cost calibration is outside the first priority for completion-date
  calibration. Costs remain relevant for S-Curve review.

## Fixtures

Minimal fixtures live under `tests/fixtures/`:

- `hongeundong_minimal_import.json`
- `hongeundong_calibration_patch.json`

They verify that dependency correction can improve the finish-date delta without
mutating the imported schedule.
