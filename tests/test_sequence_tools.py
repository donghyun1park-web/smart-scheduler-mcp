from __future__ import annotations

from core import db
from core.models import WBS
from tools.project_tools import create_project
from tools.sequence_tools import apply_sequences


def test_apply_sequence_creates_zone_activities_and_relationships(tmp_path):
    project = create_project(
        "Sequence Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    db.add_wbs(project["project_path"], WBS("wbs-hvac", None, "HVAC", "HVAC", 1))

    result = apply_sequences(
        project["project_path"],
        "공조",
        "hvac_duct_standard",
        ["1F", "2F"],
        "wbs-hvac",
    )

    activities = db.list_activities(project["project_path"])
    relationships = db.list_relationships(project["project_path"])
    assert result["ok"] is True
    assert result["added_activities"] == 10
    assert result["added_relationships"] == 8
    assert {activity.zone for activity in activities} == {"1F", "2F"}
    assert all(rel.rel_type == "FS" for rel in relationships)


def test_sequence_library_covers_all_five_disciplines(tmp_path):
    """Sprint-1 안건 1: 전기·자동제어가 라이브러리에 포함되어 있어야 한다."""
    import json
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[1]
    data = json.loads((repo_root / "mep" / "sequences.json").read_text(encoding="utf-8"))
    disciplines = {seq["discipline"] for seq in data["sequences"]}
    assert disciplines == {"위생", "공조", "소방", "전기", "자동제어"}
    counts = {d: 0 for d in disciplines}
    for seq in data["sequences"]:
        counts[seq["discipline"]] += 1
    # Each MEP discipline should have at least 4 standard sequences after sprint 1.
    for discipline, count in counts.items():
        assert count >= 4, f"{discipline} has only {count} sequences (expected ≥4)"


def test_apply_electrical_sequence_creates_activities(tmp_path):
    """전기 매립 전선관 시퀀스가 zone에 정상 적용되어야 한다."""
    project = create_project(
        "Electrical Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    db.add_wbs(project["project_path"], WBS("wbs-elec", None, "ELEC", "Electrical", 1))

    result = apply_sequences(
        project["project_path"],
        "전기",
        "electrical_conduit_standard",
        ["1F"],
        "wbs-elec",
    )

    assert result["ok"] is True
    assert result["added_activities"] == 5  # 5-step sequence
    assert result["added_relationships"] == 4  # FS chain


def test_apply_sequence_does_not_create_inter_zone_relationships(tmp_path):
    project = create_project(
        "Sequence Pilot",
        "2026-01-05",
        {"calendar_id": "cal", "name": "Korean 5-day", "weekmask": "1111100"},
        projects_dir=tmp_path,
    )
    db.add_wbs(project["project_path"], WBS("wbs-plumbing", None, "PL", "Plumbing", 1))

    apply_sequences(project["project_path"], "위생", "plumbing_sanitary_standard", ["1F", "2F"], "wbs-plumbing")
    relationships = db.list_relationships(project["project_path"])

    assert len(relationships) == 6
