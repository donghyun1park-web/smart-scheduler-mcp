"""한눈에 보는 임포트 결과 카드 (A·D 페르소나).

``tools.import_tools.import_schedule_excel`` / ``import_budget_excel`` /
``import_excel`` 가 반환하는 결과 dict를 받아 카드 형태로 표시한다.

호환되는 키 (있을 때만 표시):
- ``imported.activities`` / ``imported.wbs`` / ``imported.cost_items`` /
  ``imported.relationships``
- ``added_activities`` / ``added_relationships`` (구 임포터)
- ``warnings`` 리스트
- ``failed_rows`` / ``errors``
- ``backup_path`` / ``dry_run``
"""
from __future__ import annotations

from typing import Any, Mapping


def summarize_import_result(result: Mapping[str, Any]) -> dict[str, Any]:
    """Normalize various importer outputs into a single rendering shape."""
    imported = dict(result.get("imported") or {})
    activities = int(imported.get("activities") or result.get("added_activities") or 0)
    wbs = int(imported.get("wbs") or 0)
    cost_items = int(imported.get("cost_items") or 0)
    relationships = int(imported.get("relationships") or result.get("added_relationships") or 0)
    warnings = list(result.get("warnings") or [])
    failed_rows = list(result.get("failed_rows") or [])
    errors = list(result.get("errors") or [])
    return {
        "ok": bool(result.get("ok", not (errors or failed_rows))),
        "dry_run": bool(result.get("dry_run")),
        "activities": activities,
        "wbs": wbs,
        "cost_items": cost_items,
        "relationships": relationships,
        "warnings": warnings,
        "failed_rows": failed_rows,
        "errors": errors,
        "backup_path": result.get("backup_path"),
    }


def render_import_result_card(result: Mapping[str, Any]) -> None:
    import streamlit as st

    from viewer.components import ui_kit

    summary = summarize_import_result(result)

    icon = "✅" if summary["ok"] else "⚠️"
    dry = " (미리보기)" if summary["dry_run"] else ""
    title = f"{icon} 가져오기 결과{dry}"

    with ui_kit.card(title, icon="📥"):
        cols = st.columns(4)
        cols[0].metric("🧱 활동(Activity)", f"{summary['activities']:,}건")
        cols[1].metric("📊 WBS", f"{summary['wbs']:,}건")
        cols[2].metric("💰 비용 항목", f"{summary['cost_items']:,}건")
        cols[3].metric("🔗 선후행 관계", f"{summary['relationships']:,}건")

        if summary["backup_path"]:
            st.caption(f"🛡️ 백업: `{summary['backup_path']}`")

        if summary["warnings"]:
            with st.expander(f"⚠ 경고 {len(summary['warnings'])}건", expanded=False):
                for w in summary["warnings"][:50]:
                    st.write(f"- {w}")

        if summary["failed_rows"]:
            with st.expander(f"❌ 실패 행 {len(summary['failed_rows'])}건", expanded=True):
                st.dataframe(summary["failed_rows"], use_container_width=True, hide_index=True)

        if summary["errors"]:
            with st.expander(f"❌ 오류 {len(summary['errors'])}건", expanded=True):
                for e in summary["errors"][:20]:
                    st.error(str(e))
