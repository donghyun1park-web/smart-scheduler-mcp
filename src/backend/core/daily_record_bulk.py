"""TSV bulk parser for DailyRecord entries (A persona).

Senior 공무 wants to paste 100 rows from Excel into one box and have the
app create DailyRecord rows. Format (tab-separated, one record per line):

    작업코드	일자	계획수량	실적수량	[작업자수]	[비고]

- Header row is optional; the parser auto-detects and skips it.
- Empty lines and lines starting with '#' are ignored.
- Each row is validated independently; failures are surfaced per row
  with a Korean reason. The caller can run a dry-run preview then commit.

Reuses ``core.validation`` helpers for consistent error messages.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from core import db
from core.models import DailyRecord
from core.validation import (
    ValidationError,
    optional_text,
    require_iso_date,
    require_text,
)


HEADER_TOKENS = {"작업코드", "코드", "code", "activity_code"}


@dataclass(frozen=True)
class ParsedRow:
    row_number: int
    activity_code: str
    work_date: date
    planned_qty: float
    actual_qty: float
    workers: int
    remarks: str


@dataclass(frozen=True)
class BulkParseResult:
    rows: list[ParsedRow]
    failed_rows: list[dict[str, Any]]

    def to_dict(self) -> dict[str, Any]:
        return {
            "parsed_count": len(self.rows),
            "failed_count": len(self.failed_rows),
            "rows": [
                {
                    "row_number": r.row_number,
                    "activity_code": r.activity_code,
                    "work_date": r.work_date.isoformat(),
                    "planned_qty": r.planned_qty,
                    "actual_qty": r.actual_qty,
                    "workers": r.workers,
                    "remarks": r.remarks,
                }
                for r in self.rows
            ],
            "failed_rows": list(self.failed_rows),
        }


def parse_tsv(text: str) -> BulkParseResult:
    """Parse a TSV blob into validated rows + per-row failure list."""
    rows: list[ParsedRow] = []
    failed: list[dict[str, Any]] = []
    for line_number, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        cells = [c.strip() for c in line.split("\t")]
        # Skip a leading header row if the first cell looks like a label.
        if line_number == 1 and cells and cells[0].lower() in HEADER_TOKENS:
            continue
        if len(cells) < 4:
            failed.append({
                "row": line_number,
                "reason": "필수 열이 부족합니다 (작업코드/일자/계획수량/실적수량 이상 필요).",
                "raw": line,
            })
            continue
        try:
            row = _parse_cells(line_number, cells)
        except ValidationError as exc:
            failed.append({"row": line_number, "reason": str(exc), "raw": line})
            continue
        rows.append(row)
    return BulkParseResult(rows=rows, failed_rows=failed)


def apply_parsed_rows(
    db_path: str | Path,
    parsed: BulkParseResult,
) -> dict[str, Any]:
    """Insert each parsed row as a DailyRecord; activity-code → activity_id resolved here.

    Returns ``{"created": int, "skipped": [...], "errors": [...]}``.
    """
    activities_by_code = {a.code: a.activity_id for a in db.list_activities(db_path)}
    created = 0
    skipped: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    for row in parsed.rows:
        activity_id = activities_by_code.get(row.activity_code)
        if activity_id is None:
            skipped.append({
                "row": row.row_number,
                "activity_code": row.activity_code,
                "reason": f"작업 코드 '{row.activity_code}'에 해당하는 활동이 없습니다.",
            })
            continue
        try:
            db.create_daily_record(
                db_path,
                DailyRecord(
                    record_id=str(uuid.uuid4()),
                    activity_id=activity_id,
                    work_date=row.work_date,
                    planned_qty=row.planned_qty,
                    actual_qty=row.actual_qty,
                    workers=row.workers,
                    remarks=row.remarks,
                ),
            )
            created += 1
        except Exception as exc:  # noqa: BLE001 - persist per-row errors
            errors.append({
                "row": row.row_number,
                "activity_code": row.activity_code,
                "reason": str(exc),
            })
    return {"created": created, "skipped": skipped, "errors": errors}


def _parse_cells(row_number: int, cells: list[str]) -> ParsedRow:
    activity_code = require_text(cells[0], "작업코드")
    work_date = require_iso_date(cells[1], "일자")
    planned_qty = _parse_qty(cells[2], "계획수량")
    actual_qty = _parse_qty(cells[3], "실적수량")
    workers = _parse_int(cells[4] if len(cells) >= 5 else "0", "작업자수", default=0)
    remarks = optional_text(cells[5] if len(cells) >= 6 else "")
    return ParsedRow(
        row_number=row_number,
        activity_code=activity_code,
        work_date=work_date,
        planned_qty=planned_qty,
        actual_qty=actual_qty,
        workers=workers,
        remarks=remarks,
    )


def _parse_qty(value: str, field: str) -> float:
    text = (value or "").strip()
    if not text:
        return 0.0
    try:
        # Allow commas in numbers like "1,200.5".
        return float(text.replace(",", ""))
    except ValueError as exc:
        raise ValidationError(f"{field}는 숫자여야 합니다 (입력값: {value!r}).") from exc


def _parse_int(value: str, field: str, *, default: int = 0) -> int:
    text = (value or "").strip()
    if not text:
        return default
    try:
        return int(float(text.replace(",", "")))
    except ValueError as exc:
        raise ValidationError(f"{field}는 정수여야 합니다 (입력값: {value!r}).") from exc
