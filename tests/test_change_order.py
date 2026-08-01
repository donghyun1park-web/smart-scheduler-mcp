"""Tests for core.change_order and tools.change_order_tools."""
from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from core import db
from core.change_order import (
    add_co_item_to_db,
    apply_change_order_in_db,
    calculate_co_impact,
    create_change_order_in_db,
    get_co_summary,
    list_change_orders_from_db,
    update_co_status_in_db,
)
from core.models import Activity, Calendar, Project, WBS


@pytest.fixture
def co_db(tmp_path: Path) -> Path:
    """Create a DB with activities for change order testing."""
    db_path = tmp_path / "co_test.scheduler"
    db.initialize_database(db_path)
    db.create_calendar(db_path, Calendar("cal-1", "Test", "1111100"))
    db.create_project(db_path, Project("proj-1", "Test Project", date(2028, 1, 1), "cal-1"))
    db.create_wbs(db_path, WBS("wbs-root", None, "ROOT", "Root"))

    db.create_activity(
        db_path,
        Activity(
            activity_id="act-001", code="A-001", name="골조공사",
            wbs_id="wbs-root", discipline="건축", zone="", duration=180,
        ),
    )
    db.create_activity(
        db_path,
        Activity(
            activity_id="act-002", code="A-002", name="배관공사",
            wbs_id="wbs-root", discipline="기계설비", zone="", duration=210,
        ),
    )
    return db_path


# ---------------------------------------------------------------------------
# Create change order
# ---------------------------------------------------------------------------


class TestCreateChangeOrder:
    def test_dry_run(self, co_db):
        result = create_change_order_in_db(
            co_db, "설계변경 #1",
            co_type="design_change",
            direct_cost=50_000_000,
            markup_pct=10.0,
            dry_run=True,
        )
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["total_cost"] == 55_000_000
        # Should NOT be in DB
        orders = db.list_change_orders(co_db)
        assert len(orders) == 0

    def test_persist(self, co_db):
        result = create_change_order_in_db(
            co_db, "범위추가 #1",
            co_type="scope_addition",
            direct_cost=30_000_000,
            markup_pct=15.0,
            requested_by="현장소장",
            request_date=date(2028, 3, 15),
            dry_run=False,
        )
        assert result["ok"] is True
        assert result["dry_run"] is False
        orders = db.list_change_orders(co_db)
        assert len(orders) == 1
        assert orders[0].title == "범위추가 #1"
        assert orders[0].status == "draft"

    def test_invalid_type(self, co_db):
        result = create_change_order_in_db(
            co_db, "Test", co_type="invalid_type", dry_run=True,
        )
        assert result["ok"] is False
        assert "유효하지 않은 CO 유형" in result["error"]

    def test_markup_calculation(self, co_db):
        result = create_change_order_in_db(
            co_db, "Test",
            direct_cost=100_000_000,
            markup_pct=12.5,
            dry_run=True,
        )
        assert result["total_cost"] == 112_500_000

    def test_korean_labels(self, co_db):
        result = create_change_order_in_db(
            co_db, "Test", co_type="design_change", dry_run=True,
        )
        assert result["co_type_kr"] == "설계변경"
        assert result["status_kr"] == "초안"

    def test_schedule_impact(self, co_db):
        result = create_change_order_in_db(
            co_db, "Test",
            schedule_impact_days=30,
            dry_run=True,
        )
        assert result["schedule_impact_days"] == 30


# ---------------------------------------------------------------------------
# Add CO item
# ---------------------------------------------------------------------------


class TestAddCoItem:
    def test_dry_run(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id

        result = add_co_item_to_db(
            co_db, co_id, "act-001",
            cost_change=10_000_000, duration_change=5,
            dry_run=True,
        )
        assert result["ok"] is True
        assert result["dry_run"] is True

    def test_persist(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id

        result = add_co_item_to_db(
            co_db, co_id, "act-001",
            cost_change=10_000_000, duration_change=5,
            dry_run=False,
        )
        assert result["ok"] is True
        items = db.list_change_order_items(co_db, co_id)
        assert len(items) == 1

    def test_invalid_co(self, co_db):
        result = add_co_item_to_db(co_db, "nonexistent", "act-001", dry_run=True)
        assert result["ok"] is False
        assert "변경지시를 찾을 수 없습니다" in result["error"]

    def test_invalid_activity(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id

        result = add_co_item_to_db(co_db, co_id, "nonexistent", dry_run=True)
        assert result["ok"] is False
        assert "활동을 찾을 수 없습니다" in result["error"]

    def test_cannot_add_to_approved(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        # Move to pending then approved
        update_co_status_in_db(co_db, co_id, "pending", dry_run=False)
        update_co_status_in_db(co_db, co_id, "approved", approved_by="PM", dry_run=False)

        result = add_co_item_to_db(co_db, co_id, "act-001", dry_run=True)
        assert result["ok"] is False
        assert "수정 불가 상태" in result["error"]


# ---------------------------------------------------------------------------
# Status transitions
# ---------------------------------------------------------------------------


class TestUpdateCoStatus:
    def test_draft_to_pending(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id

        result = update_co_status_in_db(co_db, co_id, "pending", dry_run=False)
        assert result["ok"] is True
        assert result["new_status"] == "pending"
        assert result["new_status_kr"] == "검토중"

    def test_pending_to_approved(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        update_co_status_in_db(co_db, co_id, "pending", dry_run=False)

        result = update_co_status_in_db(
            co_db, co_id, "approved",
            approved_by="본부장",
            approval_date=date(2028, 4, 1),
            dry_run=False,
        )
        assert result["ok"] is True
        assert result["new_status_kr"] == "승인"

    def test_invalid_transition(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        # draft → approved directly is invalid
        result = update_co_status_in_db(co_db, co_id, "approved", dry_run=True)
        assert result["ok"] is False
        assert "전환 불가" in result["error"]

    def test_invalid_status(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        result = update_co_status_in_db(co_db, co_id, "invalid", dry_run=True)
        assert result["ok"] is False

    def test_reject_and_reopen(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        update_co_status_in_db(co_db, co_id, "pending", dry_run=False)
        update_co_status_in_db(co_db, co_id, "rejected", dry_run=False)
        # rejected → draft is allowed
        result = update_co_status_in_db(co_db, co_id, "draft", dry_run=False)
        assert result["ok"] is True

    def test_nonexistent_co(self, co_db):
        result = update_co_status_in_db(co_db, "nonexistent", "pending", dry_run=True)
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# CO impact
# ---------------------------------------------------------------------------


class TestCoImpact:
    def test_with_items(self, co_db):
        create_change_order_in_db(
            co_db, "CO-1",
            direct_cost=50_000_000, markup_pct=10.0,
            schedule_impact_days=20, dry_run=False,
        )
        co_id = db.list_change_orders(co_db)[0].co_id

        add_co_item_to_db(
            co_db, co_id, "act-001",
            cost_change=30_000_000, duration_change=10, dry_run=False,
        )
        add_co_item_to_db(
            co_db, co_id, "act-002",
            cost_change=20_000_000, duration_change=15, dry_run=False,
        )

        result = calculate_co_impact(co_db, co_id)
        assert result["ok"] is True
        assert result["items_count"] == 2
        assert result["items_total_cost_change"] == 50_000_000
        assert result["items_total_duration_change"] == 25
        assert result["header_total_cost"] == 55_000_000

    def test_nonexistent(self, co_db):
        result = calculate_co_impact(co_db, "nonexistent")
        assert result["ok"] is False

    def test_empty_items(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        result = calculate_co_impact(co_db, co_id)
        assert result["ok"] is True
        assert result["items_count"] == 0


# ---------------------------------------------------------------------------
# List change orders
# ---------------------------------------------------------------------------


class TestListChangeOrders:
    def test_empty(self, co_db):
        result = list_change_orders_from_db(co_db)
        assert result["ok"] is True
        assert result["count"] == 0

    def test_with_orders(self, co_db):
        create_change_order_in_db(co_db, "CO-1", co_type="design_change", dry_run=False)
        create_change_order_in_db(co_db, "CO-2", co_type="scope_addition", dry_run=False)
        result = list_change_orders_from_db(co_db)
        assert result["count"] == 2

    def test_filter_by_type(self, co_db):
        create_change_order_in_db(co_db, "CO-1", co_type="design_change", dry_run=False)
        create_change_order_in_db(co_db, "CO-2", co_type="scope_addition", dry_run=False)
        result = list_change_orders_from_db(co_db, co_type="design_change")
        assert result["count"] == 1

    def test_filter_by_status(self, co_db):
        create_change_order_in_db(co_db, "CO-1", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        update_co_status_in_db(co_db, co_id, "pending", dry_run=False)

        create_change_order_in_db(co_db, "CO-2", dry_run=False)

        result = list_change_orders_from_db(co_db, status="draft")
        assert result["count"] == 1
        result = list_change_orders_from_db(co_db, status="pending")
        assert result["count"] == 1


# ---------------------------------------------------------------------------
# CO summary
# ---------------------------------------------------------------------------


class TestCoSummary:
    def test_empty(self, co_db):
        result = get_co_summary(co_db)
        assert result["ok"] is True
        assert result["total_count"] == 0

    def test_with_orders(self, co_db):
        create_change_order_in_db(
            co_db, "CO-1", co_type="design_change",
            direct_cost=50_000_000, markup_pct=10.0, dry_run=False,
        )
        create_change_order_in_db(
            co_db, "CO-2", co_type="scope_addition",
            direct_cost=30_000_000, markup_pct=15.0,
            schedule_impact_days=10, dry_run=False,
        )

        result = get_co_summary(co_db)
        assert result["total_count"] == 2
        assert result["total_direct_cost"] == 80_000_000
        assert result["total_schedule_impact_days"] == 10
        assert "draft" in result["by_status"]
        assert result["by_status"]["draft"]["count"] == 2

    def test_by_type(self, co_db):
        create_change_order_in_db(
            co_db, "CO-1", co_type="design_change",
            direct_cost=50_000_000, dry_run=False,
        )
        create_change_order_in_db(
            co_db, "CO-2", co_type="design_change",
            direct_cost=30_000_000, dry_run=False,
        )
        result = get_co_summary(co_db)
        assert result["by_type"]["design_change"]["count"] == 2
        assert result["by_type"]["design_change"]["direct_cost"] == 80_000_000


# ---------------------------------------------------------------------------
# Apply change order
# ---------------------------------------------------------------------------


def _make_approved_co(db_path, *, cost_change=10_000_000, duration_change=15):
    """Helper: create CO → add item → approve through full status chain."""
    create_change_order_in_db(
        db_path, "적용 테스트 CO",
        co_type="design_change",
        direct_cost=cost_change,
        schedule_impact_days=duration_change,
        dry_run=False,
    )
    co_id = db.list_change_orders(db_path)[0].co_id

    add_co_item_to_db(
        db_path, co_id, "act-001",
        cost_change=cost_change,
        duration_change=duration_change,
        dry_run=False,
    )
    update_co_status_in_db(db_path, co_id, "pending", dry_run=False)
    update_co_status_in_db(db_path, co_id, "approved", dry_run=False)
    return co_id


class TestApplyChangeOrder:
    def test_dry_run_returns_preview(self, co_db):
        co_id = _make_approved_co(co_db)
        result = apply_change_order_in_db(co_db, co_id, dry_run=True)
        assert result["ok"] is True
        assert result["dry_run"] is True
        assert result["items_processed"] == 1
        # Status not changed
        co = db.get_change_order(co_db, co_id)
        assert co.status == "approved"

    def test_apply_updates_activity_duration(self, co_db):
        co_id = _make_approved_co(co_db, duration_change=20)
        before = next(a for a in db.list_activities(co_db) if a.activity_id == "act-001")
        assert before.duration == 180

        result = apply_change_order_in_db(co_db, co_id, applied_by="공무팀장", dry_run=False)
        assert result["ok"] is True

        after = next(a for a in db.list_activities(co_db) if a.activity_id == "act-001")
        assert after.duration == 200  # 180 + 20

    def test_apply_updates_activity_cost(self, co_db):
        co_id = _make_approved_co(co_db, cost_change=5_000_000)
        result = apply_change_order_in_db(co_db, co_id, dry_run=False)
        assert result["ok"] is True

        after = next(a for a in db.list_activities(co_db) if a.activity_id == "act-001")
        assert after.cost == 5_000_000  # was 0.0, +5_000_000

    def test_apply_sets_status_to_applied(self, co_db):
        co_id = _make_approved_co(co_db)
        apply_change_order_in_db(co_db, co_id, dry_run=False)
        co = db.get_change_order(co_db, co_id)
        assert co.status == "applied"

    def test_cannot_apply_draft(self, co_db):
        create_change_order_in_db(co_db, "초안 CO", dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        result = apply_change_order_in_db(co_db, co_id, dry_run=False)
        assert result["ok"] is False
        assert "승인" in result["error"]

    def test_cannot_apply_twice(self, co_db):
        co_id = _make_approved_co(co_db)
        apply_change_order_in_db(co_db, co_id, dry_run=False)
        # Try again — status is now "applied"
        result = apply_change_order_in_db(co_db, co_id, dry_run=False)
        assert result["ok"] is False

    def test_nonexistent_co(self, co_db):
        result = apply_change_order_in_db(co_db, "nonexistent", dry_run=False)
        assert result["ok"] is False

    def test_no_items_rejected(self, co_db):
        """CO without items should return error."""
        create_change_order_in_db(co_db, "빈 CO", direct_cost=1_000_000, dry_run=False)
        co_id = db.list_change_orders(co_db)[0].co_id
        update_co_status_in_db(co_db, co_id, "pending", dry_run=False)
        update_co_status_in_db(co_db, co_id, "approved", dry_run=False)
        result = apply_change_order_in_db(co_db, co_id, dry_run=False)
        assert result["ok"] is False
        assert "세부항목" in result["error"]

    def test_item_detail_in_response(self, co_db):
        co_id = _make_approved_co(co_db, cost_change=8_000_000, duration_change=10)
        result = apply_change_order_in_db(co_db, co_id, dry_run=True)
        item = result["items"][0]
        assert item["activity_id"] == "act-001"
        assert item["duration_change"] == 10
        assert item["cost_change"] == 8_000_000
        assert item["duration_before"] == 180
        assert item["duration_after"] == 190
