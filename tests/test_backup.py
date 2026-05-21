from __future__ import annotations

from core.backup import create_backup, restore_backup


def test_create_backup_copies_file_and_rotates_old_backups(tmp_path):
    source = tmp_path / "site.scheduler"
    source.write_text("current", encoding="utf-8")
    backup_dir = tmp_path / "backups"

    for idx in range(4):
        source.write_text(f"version-{idx}", encoding="utf-8")
        create_backup(source, backup_dir=backup_dir, reason="report", keep=3)

    backups = sorted(backup_dir.glob("site_*.scheduler"))

    assert len(backups) == 3
    assert backups[-1].read_text(encoding="utf-8") == "version-3"


def test_restore_backup_returns_new_restore_path(tmp_path):
    source = tmp_path / "site.scheduler"
    source.write_text("current", encoding="utf-8")
    backup = create_backup(source, backup_dir=tmp_path / "backups", reason="baseline", keep=30)
    restore_target = tmp_path / "restored.scheduler"

    restored = restore_backup(backup.backup_path, restore_target)

    assert restored == restore_target
    assert restore_target.read_text(encoding="utf-8") == "current"
