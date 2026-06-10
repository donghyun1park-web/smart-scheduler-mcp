"""Tests for v2.9 Quick Wins: context, baseline, alerts."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.models import (
    Activity,
    Calendar,
    ChangeOrder,
    CostItem,
    MaterialRecord,
    Project,
    WBS,
)


@pytest.fixture
def site_db(tmp_path: Path) -> Path:
    db_path = tmp_path / "qw_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "테스트현장", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    db.create_activity(
        db_path,
        Activity(
            activity_id="act-001", code="A-001", name="3층 골조",
            wbs_id="wbs-root", discipline="건축", zone="3F", duration=30,
            es_date=date(2028, 2, 1), ef_date=date(2028, 3, 1),
        ),
    )
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-002", code="A-002", name="배관공사",
            wbs_id="wbs-root", discipline="기계설비", zone="B1", duration=20,
            es_date=date(2028, 3, 1), ef_date=date(2028, 3, 21),
        ),
    )
    return db_path


# ---------------------------------------------------------------------------
# Context (아이디어 1-A)
# ---------------------------------------------------------------------------


class TestContext:
    @pytest.fixture(autouse=True)
    def _isolate_context(self, tmp_path, monkeypatch):
        """Redirect context file into tmp so tests don't touch real home."""
        import core.context as ctx
        fake_dir = tmp_path / ".smart_scheduler"
        monkeypatch.setattr(ctx, "_CONTEXT_DIR", fake_dir)
        monkeypatch.setattr(ctx, "_CONTEXT_FILE", fake_dir / "active_context.json")

    def test_set_and_get(self, site_db):
        from core.context import get_active_project, set_active_project

        r = set_active_project(site_db, "proj-1", label="테스트현장")
        assert r["ok"] is True

        got = get_active_project()
        assert got["active"] is True
        assert got["project_id"] == "proj-1"
        assert got["label"] == "테스트현장"
        assert got["file_exists"] is True

    def test_set_nonexistent_file(self, tmp_path):
        from core.context import set_active_project

        r = set_active_project(tmp_path / "nope.scheduler")
        assert r["ok"] is False

    def test_get_when_unset(self):
        from core.context import get_active_project

        got = get_active_project()
        assert got["active"] is False

    def test_resolve_prefers_explicit(self, site_db):
        from core.context import resolve_db_path, set_active_project

        set_active_project(site_db, "proj-1")
        # explicit path wins
        assert resolve_db_path("C:/explicit/path.scheduler") == "C:/explicit/path.scheduler"

    def test_resolve_falls_back_to_active(self, site_db):
        from core.context import resolve_db_path, set_active_project

        set_active_project(site_db, "proj-1")
        assert resolve_db_path("") == str(site_db)
        assert resolve_db_path(None) == str(site_db)

    def test_resolve_raises_without_context(self):
        from core.context import resolve_db_path

        with pytest.raises(ValueError):
            resolve_db_path("")

    def test_clear(self, site_db):
        from core.context import clear_active_project, get_active_project, set_active_project

        set_active_project(site_db, "proj-1")
        cleared = clear_active_project()
        assert cleared["cleared"] is True
        assert get_active_project()["active"] is False


# ---------------------------------------------------------------------------
# Baseline (아이디어 6)
# ---------------------------------------------------------------------------


class TestBaseline:
    def test_establish_dry_run(self, site_db):
        from core.baseline import establish_baseline

        r = establish_baseline(site_db, label="착공 기준", dry_run=True)
        assert r["ok"] is True
        assert r["dry_run"] is True
        assert r["activity_count"] == 2
        # nothing persisted
        assert db.list_baseline_snapshots(site_db) == []

    def test_establish_persist(self, site_db):
        from core.baseline import establish_baseline

        r = establish_baseline(site_db, label="착공 기준", approved_by="소장", dry_run=False)
        assert r["ok"] is True
        snaps = db.list_baseline_snapshots(site_db)
        assert len(snaps) == 2
        assert r["project_finish"] == "2028-03-21"

    def test_establish_empty(self, tmp_path):
        from core.baseline import establish_baseline

        empty = tmp_path / "empty.scheduler"
        db.initialize_database(empty)
        r = establish_baseline(empty, dry_run=False)
        assert r["ok"] is False

    def test_list_baselines(self, site_db):
        from core.baseline import establish_baseline, list_baselines

        establish_baseline(site_db, label="기준1", dry_run=False)
        r = list_baselines(site_db)
        assert r["count"] == 1
        assert r["baselines"][0]["label"] == "기준1"
        assert r["baselines"][0]["activity_count"] == 2

    def test_compare_detects_delay(self, site_db):
        from core.baseline import compare_to_baseline, establish_baseline

        establish_baseline(site_db, label="기준", dry_run=False)

        # Slip act-001 finish by 10 days
        act = next(a for a in db.list_activities(site_db) if a.activity_id == "act-001")
        from dataclasses import replace
        db.update_activity(site_db, replace(act, ef_date=date(2028, 3, 11), duration=40))

        r = compare_to_baseline(site_db)
        assert r["ok"] is True
        assert r["delayed_count"] == 1
        top = r["activities"][0]
        assert top["activity_id"] == "act-001"
        assert top["finish_drift_days"] == 10
        assert top["duration_drift_days"] == 10

    def test_compare_no_baseline(self, site_db):
        from core.baseline import compare_to_baseline

        r = compare_to_baseline(site_db)
        assert r["ok"] is False


# ---------------------------------------------------------------------------
# Alerts (아이디어 4-A)
# ---------------------------------------------------------------------------


class TestAlerts:
    def test_no_alerts_clean_project(self, site_db):
        from core.alerts import scan_alerts

        r = scan_alerts(site_db, as_of=date(2028, 1, 15))
        assert r["ok"] is True
        # No materials, no COs, schedule not started → expect 0 or only progress
        assert r["critical_count"] == 0

    def test_overdue_material_alert(self, site_db):
        from core.alerts import scan_alerts

        db.create_material_record(
            site_db,
            MaterialRecord(
                material_id="mat-1", activity_id="act-002",
                material_name="냉동기 200RT",
                expected_date=date(2028, 2, 1), status="ordered",
            ),
        )
        r = scan_alerts(site_db, as_of=date(2028, 2, 10))
        codes = [a["code"] for a in r["alerts"]]
        assert "material_overdue" in codes
        assert r["critical_count"] >= 1

    def test_delivered_material_no_alert(self, site_db):
        from core.alerts import scan_alerts

        db.create_material_record(
            site_db,
            MaterialRecord(
                material_id="mat-2", activity_id="act-002",
                material_name="밸브",
                expected_date=date(2028, 2, 1), status="delivered",
            ),
        )
        r = scan_alerts(site_db, as_of=date(2028, 2, 10))
        codes = [a["code"] for a in r["alerts"]]
        assert "material_overdue" not in codes

    def test_pending_co_alert(self, site_db):
        from core.alerts import scan_alerts

        db.create_change_order(
            site_db,
            ChangeOrder(
                co_id="co-1", title="설계변경", status="pending",
                direct_cost=10_000_000, total_cost=11_000_000,
            ),
        )
        r = scan_alerts(site_db, as_of=date(2028, 2, 10))
        codes = [a["code"] for a in r["alerts"]]
        assert "co_pending" in codes

    def test_unapplied_co_alert(self, site_db):
        from core.alerts import scan_alerts

        db.create_change_order(
            site_db,
            ChangeOrder(
                co_id="co-2", title="승인된 변경", status="approved",
                direct_cost=5_000_000, total_cost=5_500_000,
            ),
        )
        r = scan_alerts(site_db, as_of=date(2028, 2, 10))
        codes = [a["code"] for a in r["alerts"]]
        assert "co_unapplied" in codes

    def test_alerts_sorted_critical_first(self, site_db):
        from core.alerts import scan_alerts

        db.create_material_record(
            site_db,
            MaterialRecord(
                material_id="mat-3", activity_id="act-002",
                material_name="장비", expected_date=date(2028, 2, 1), status="ordered",
            ),
        )
        db.create_change_order(
            site_db,
            ChangeOrder(co_id="co-3", title="CO", status="pending", total_cost=1_000_000),
        )
        r = scan_alerts(site_db, as_of=date(2028, 2, 10))
        levels = [a["level"] for a in r["alerts"]]
        # 🔴 must come before 🟡
        if "🔴" in levels and "🟡" in levels:
            assert levels.index("🔴") < levels.index("🟡")


# ---------------------------------------------------------------------------
# Briefing integration
# ---------------------------------------------------------------------------


class TestBriefingAlertsIntegration:
    def test_briefing_includes_alerts(self, site_db):
        from core.dashboard import generate_site_briefing

        db.create_change_order(
            site_db,
            ChangeOrder(co_id="co-x", title="CO", status="pending", total_cost=1_000_000),
        )
        brief = generate_site_briefing(site_db, as_of=date(2028, 2, 10))
        assert "alerts" in brief
        assert "alert_summary" in brief

    def test_briefing_no_recursion(self, site_db):
        """_include_alerts=False must not attach alerts (used by alert engine)."""
        from core.dashboard import generate_site_briefing

        brief = generate_site_briefing(site_db, as_of=date(2028, 2, 10), _include_alerts=False)
        assert "alerts" not in brief
