"""MCP tool wrapper for delay-impact what-if analysis."""
from __future__ import annotations

from pathlib import Path

from core.delay_impact import analyze_delay_impact as _analyze


def analyze_delay_impact(
    project_path: str | Path,
    activity_id: str,
    delay_days: int,
) -> dict[str, object]:
    """Return a successor-cascade impact estimate for an activity slipping by N days.

    Estimate based on saved ES/EF dates — does not re-run CPM. Useful for
    quick "이 작업 일주일 늦으면?" what-if previews. Mark results as
    "예상치(estimate)" in user-facing copy.
    """
    return _analyze(project_path, activity_id, int(delay_days))
