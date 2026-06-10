"""Tests for the delay-impact what-if cascade."""
from __future__ import annotations

import uuid
from dataclasses import replace
from datetime import date

import pytest

from core import db
from core.delay_impact import analyze_delay_impact
from core.models import Activity, Relationship, WBS
from tools.project_tools import create_project


@pytest.fixture()
def chain_project(tmp_path):
    """Linear chain A → B → C → D with stored CPM dates."""
    project = create_project(
        "지연 영향 테스트",
        "2026-06-01",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    path = project["project_path"]
    wbs = db.add_wbs(path, WBS(str(uuid.uuid4()), None, "MEP", "MEP", 1))

    def make(code, name, start, finish, critical=True):
        return Activity(
            str(uuid.uuid4()), code, name, wbs.wbs_id, "위생", "1F", 5, 0,
            es_date=start, ef_date=finish, is_critical=critical,
        )

    a = make("A", "매립배관", date(2026, 6, 1), date(2026, 6, 5))
    b = make("B", "수압시험", date(2026, 6, 8), date(2026, 6, 8))
    c = make("C", "보온", date(2026, 6, 9), date(2026, 6, 11))
    d = make("D", "마감", date(2026, 6, 12), date(2026, 6, 15))
    # Off-chain non-critical activity (no relationship to chain)
    z = make("Z", "별개작업", date(2026, 7, 1), date(2026, 7, 5), critical=False)
    for act in (a, b, c, d, z):
        db.add_activity(path, act)
    for pred, succ in [(a, b), (b, c), (c, d)]:
        db.add_relationship(
            path, Relationship(str(uuid.uuid4()), pred.activity_id, succ.activity_id, "FS", 0)
        )
    return path, {"a": a, "b": b, "c": c, "d": d, "z": z}


def test_analyze_delay_impact_propagates_through_chain(chain_project):
    path, acts = chain_project
    result = analyze_delay_impact(path, acts["a"].activity_id, 5)
    assert result["ok"] is True
    assert result["delay_days"] == 5
    assert result["impacted_count"] == 3  # B, C, D
    codes = [node["code"] for node in result["tree"]]
    assert codes == ["B", "C", "D"]
    # Every node shifted by 5 days
    for node in result["tree"]:
        assert node["shift_days"] == 5
        assert node["via"] == "FS"
    # Z (2026-07-05) is unrelated and already finishes later than D+5,
    # so project completion is unchanged.
    assert result["completion_delta_days"] == 0
    assert result["projected_completion_date"] == "2026-07-05"
    assert result["original_completion_date"] == "2026-07-05"


def test_analyze_delay_impact_skips_unrelated_activities(chain_project):
    path, acts = chain_project
    result = analyze_delay_impact(path, acts["b"].activity_id, 3)
    impacted = {n["code"] for n in result["tree"]}
    assert impacted == {"C", "D"}  # Z untouched, A is predecessor not successor


def test_analyze_delay_impact_rejects_invalid(chain_project):
    path, acts = chain_project
    assert analyze_delay_impact(path, acts["a"].activity_id, 0)["ok"] is False
    assert analyze_delay_impact(path, "ghost", 5)["ok"] is False


def test_analyze_delay_impact_shifts_completion_when_chain_is_driving(chain_project):
    """If we remove the unrelated late activity, the chain becomes the final
    work and a delay in A pushes project completion by the same amount."""
    path, acts = chain_project
    # Move Z earlier than D so D becomes the final activity
    db.update_activity(path, replace(acts["z"], es_date=date(2026, 6, 1), ef_date=date(2026, 6, 2)))
    result = analyze_delay_impact(path, acts["a"].activity_id, 5)
    assert result["completion_delta_days"] == 5
    # D originally ends 2026-06-15; +5 cal days → 2026-06-20
    assert result["projected_completion_date"] == "2026-06-20"


def test_analyze_delay_impact_completion_unchanged_when_other_activity_finishes_later(chain_project):
    """If a non-impacted activity ends later than the cascaded chain end,
    project completion does not move."""
    path, acts = chain_project
    # Bump Z to finish after D+5 by 10 days
    z_new = replace(acts["z"], ef_date=date(2026, 7, 30))
    db.update_activity(path, z_new)
    result = analyze_delay_impact(path, acts["a"].activity_id, 5)
    assert result["completion_delta_days"] == 0
    assert result["projected_completion_date"] == "2026-07-30"
