from __future__ import annotations

from pathlib import Path


def calculate_cpm(project_path: str | Path) -> dict[str, object]:
    """Placeholder CPM entrypoint.

    v0.1 will prefer a verified pyCritical adapter, then fall back to the
    deterministic NetworkX implementation.
    """
    from core.cpm_networkx import calculate_cpm_with_networkx

    return calculate_cpm_with_networkx(project_path)
