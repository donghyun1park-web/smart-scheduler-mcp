from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any, cast

from core import db
from core.models import Activity, Relationship


SEQUENCES_PATH = Path(__file__).resolve().parents[1] / "mep" / "sequences.json"


def apply_sequences(
    project_path: str | Path,
    discipline: str,
    sequence_key: str,
    zones: list[str],
    wbs_id: str,
    duration_overrides: dict[str, int] | None = None,
) -> dict[str, object]:
    """Generate activities + FS chain for each zone from a MEP sequence template.

    Reads ``mep/sequences.json`` keyed by ``(discipline, sequence_key)``.
    For each zone, expands ``steps`` into activities with code
    ``{SEQUENCE_KEY}-{ZONE}-{NN}`` and chains them with FS(0) relationships.
    ``duration_overrides`` maps a step ``key`` → days (replaces template default).
    """
    sequence = _load_sequence(discipline, sequence_key)
    duration_overrides = duration_overrides or {}
    added_activities = 0
    added_relationships = 0
    for zone in zones:
        previous_id: str | None = None
        steps = cast(list[dict[str, object]], sequence["steps"])
        for index, step in enumerate(steps, start=1):
            step_key = str(step["key"])
            activity_id = str(uuid.uuid4())
            code = f"{sequence_key.upper()}-{zone}-{index:02d}"
            db.add_activity(
                project_path,
                Activity(
                    activity_id=activity_id,
                    code=code,
                    name=str(step["name"]),
                    wbs_id=wbs_id,
                    discipline=discipline,
                    zone=zone,
                    duration=int(cast(str | int | float, duration_overrides.get(step_key, step["duration"]))),
                    cost=0.0,
                ),
            )
            added_activities += 1
            if previous_id is not None:
                db.add_relationship(
                    project_path,
                    Relationship(str(uuid.uuid4()), previous_id, activity_id, "FS", 0),
                )
                added_relationships += 1
            previous_id = activity_id
    return {
        "ok": True,
        "added_activities": added_activities,
        "added_relationships": added_relationships,
    }


def _load_sequence(discipline: str, sequence_key: str) -> dict[str, object]:
    data = json.loads(SEQUENCES_PATH.read_text(encoding="utf-8"))
    for sequence in cast(list[dict[str, Any]], data["sequences"]):
        if sequence["discipline"] == discipline and sequence["key"] == sequence_key:
            return cast(dict[str, object], sequence)
    raise ValueError(f"Unknown sequence: {discipline}/{sequence_key}")
