from __future__ import annotations

from pathlib import Path

from core.reporting import create_excel_report


def generate_report(project_path: str | Path, output_path: str | Path | None = None) -> dict[str, object]:
    return create_excel_report(project_path, output_path)
