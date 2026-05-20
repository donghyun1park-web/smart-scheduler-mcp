# Smart Node-Scheduler v0.1.1 Release Notes

## Summary

Smart Node-Scheduler v0.1.1 is a post-v0.1.0 follow-up release that adds the
HongEundong completion-date calibration workflow and user-facing execution
documentation.

This release keeps the v0.1.0 Internal MVP baseline intact while adding an
explicit workflow for comparing imported CPM results with calibrated CPM
results.

## Added

### HongEundong Completion-Date Calibration Workflow

- Added `CalibrationPatch`
- Added `DependencyOverride`
- Added `DurationOverride`
- Added `LagOverride`
- Added before/after CPM comparison
- Added target finish date delta reporting
- Added unknown task warning/report handling
- Added cycle detection warning/report handling
- Added correction records with `applied_order`

### MCP Tool

- Added `calibrate_completion_date`
- Registered the tool in `server.py`
- Added wrapper tests for MCP/tool usage

### Fixtures and Tests

- Added HongEundong minimal import fixture
- Added HongEundong calibration patch fixture
- Added tests for:
  - dependency count increase
  - imported schedule immutability
  - before/after finish date comparison
  - target finish date delta calculation
  - unknown task id handling
  - cycle dependency detection
  - fixture-based finish-date delta improvement
  - MCP tool registration

### Documentation

- Added `docs/HONGEUNDONG_COMPLETION_DATE_CALIBRATION.md`
- Added `docs/SMART_SCHEDULER_EXECUTION_GUIDE.md`
- Added screenshot assets under `docs/assets/screenshots`
- Added README documentation links

## Important Behavior

The target finish date is a validation reference, not an automatic scheduling
constraint.

현장 신뢰 준공일은 검증 기준이며, CPM 일정을 강제로 맞추기 위한 제약조건이 아닙니다.

The workflow does not automatically manipulate durations or dependencies to
force the CPM finish date to match the target finish date. Calibration is
applied only through explicit user-provided patches.

## Validation

```text
pip check: No broken requirements found.
pytest: 49 passed
ruff: All checks passed.
mypy: Success, no issues found in 68 source files
```

## Release Boundary

This release does not modify the `v0.1.0` tag.

`v0.1.0` remains the closed Internal MVP baseline.
`v0.1.1` adds the first post-MVP calibration workflow and execution
documentation.

## Known Limitations

- Relationship-free timeline Excel cannot produce fully reliable CPM results
  without user correction.
- Target finish date is not used to automatically reshape the schedule.
- Calibration quality depends on explicit dependency, lag, and duration patches
  provided by the user.
- The HongEundong fixture is a minimal sanitized fixture, not a full
  real-project dataset.
