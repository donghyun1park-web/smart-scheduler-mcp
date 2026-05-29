from __future__ import annotations

from core.cpm import run_cpm
from core.models import Activity, Relationship


def test_run_cpm_returns_standard_dtos_for_fs_chain():
    activities = [
        _activity("a", "A", 3),
        _activity("b", "B", 2),
        _activity("c", "C", 4),
    ]
    relationships = [
        Relationship("r1", "a", "b", "FS", 0),
        Relationship("r2", "b", "c", "FS", 0),
    ]

    result = run_cpm(activities, relationships)

    assert result.cycles_detected == []
    assert result.total_duration_days == 9
    assert result.critical_count == 3
    assert [item.activity_id for item in result.activities] == ["a", "b", "c"]
    assert result.activities[0].es_workday == 0
    assert result.activities[0].ef_workday == 3
    assert result.activities[2].lf_workday == 9
    assert all(item.is_critical for item in result.activities)


def test_run_cpm_handles_disconnected_starting_activities():
    activities = [
        _activity("a", "A", 3),
        _activity("b", "B", 2),
        _activity("c", "C", 4),
    ]
    relationships = [Relationship("r1", "a", "c", "FS", 0)]

    result = run_cpm(activities, relationships)

    by_id = {item.activity_id: item for item in result.activities}
    assert result.total_duration_days == 7
    assert by_id["b"].es_workday == 0
    assert by_id["b"].total_float == 5
    assert not by_id["b"].is_critical


def test_run_cpm_reports_cycles_without_crashing():
    activities = [
        _activity("a", "A", 1),
        _activity("b", "B", 1),
        _activity("c", "C", 1),
    ]
    relationships = [
        Relationship("r1", "a", "b", "FS", 0),
        Relationship("r2", "b", "c", "FS", 0),
        Relationship("r3", "c", "a", "FS", 0),
    ]

    result = run_cpm(activities, relationships)

    assert result.activities == []
    assert result.cycles_detected == [["a", "b", "c", "a"]]


def _activity(activity_id: str, code: str, duration: int) -> Activity:
    return Activity(
        activity_id=activity_id,
        code=code,
        name=code,
        wbs_id="wbs",
        discipline="공조",
        zone="1F",
        duration=duration,
    )
