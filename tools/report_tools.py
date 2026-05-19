from __future__ import annotations

from pathlib import Path


def generate_report(project_path: str | Path, output_path: str | Path | None = None) -> dict[str, object]:
    return {
        "ok": False,
        "project_path": str(project_path),
        "output_path": str(output_path) if output_path else None,
        "error": "generate_report is not implemented in v0.1 Week 2; Excel report generation is Week 4 scope.",
    }
