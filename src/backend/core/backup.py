from __future__ import annotations

import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path


@dataclass(frozen=True)
class BackupResult:
    source_path: Path
    backup_path: Path
    reason: str
    created_at: str


def create_backup(
    source_path: str | Path,
    *,
    backup_dir: str | Path | None = None,
    reason: str = "manual",
    keep: int = 30,
) -> BackupResult:
    source = Path(source_path)
    if not source.is_file():
        raise FileNotFoundError(f"Backup source does not exist or is not a file: {source}")
    destination_dir = Path(backup_dir) if backup_dir is not None else source.parent / "backups"
    destination_dir.mkdir(parents=True, exist_ok=True)
    created_at = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    reason_slug = _slug(reason)
    backup_path = destination_dir / f"{source.stem}_{created_at}_{reason_slug}{source.suffix}"
    shutil.copy2(source, backup_path)
    _rotate_backups(destination_dir, source.stem, source.suffix, keep)
    return BackupResult(
        source_path=source,
        backup_path=backup_path,
        reason=reason,
        created_at=created_at,
    )


def restore_backup(backup_path: str | Path, restore_path: str | Path) -> Path:
    backup = Path(backup_path)
    target = Path(restore_path)
    if not backup.is_file():
        raise FileNotFoundError(f"Backup file does not exist: {backup}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup, target)
    return target


def _rotate_backups(backup_dir: Path, source_stem: str, suffix: str, keep: int) -> None:
    if keep <= 0:
        return
    backups = sorted(backup_dir.glob(f"{source_stem}_*{suffix}"), key=lambda path: path.name)
    for old_backup in backups[:-keep]:
        old_backup.unlink()


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_-]+", "-", value.strip()).strip("-").lower()
    return slug or "backup"
