from __future__ import annotations

from pathlib import Path


def calculate_cpm_with_networkx(project_path: str | Path) -> dict[str, object]:
    """NetworkX fallback skeleton for the upcoming CPM implementation."""
    return {
        "project_path": str(project_path),
        "engine": "networkx",
        "total_duration_days": 0,
        "critical_count": 0,
        "completion_date": None,
        "cycles_detected": [],
    }
