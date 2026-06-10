"""Streamlit panel for TSV bulk daily-record entry (A persona)."""
from __future__ import annotations

from pathlib import Path

from core.daily_record_bulk import apply_parsed_rows, parse_tsv


SAMPLE_TSV = """작업코드\t일자\t계획수량\t실적수량\t작업자수\t비고
A-001\t2026-06-10\t100\t90\t5\t오후 우천 1시간 지연
A-002\t2026-06-10\t50\t50\t3\t정상
"""


def render(project_path: str | Path) -> None:
    import streamlit as st

    st.subheader("📋 일일 보고 일괄 입력 (TSV)")
    st.caption(
        "엑셀에서 6개 열(작업코드 / 일자 / 계획수량 / 실적수량 / 작업자수 / 비고)을 "
        "복사 → 아래 상자에 붙여넣기 → [미리보기] → [저장]."
    )

    with st.expander("샘플 형식 보기", expanded=False):
        st.code(SAMPLE_TSV, language="text")

    text = st.text_area("TSV (탭 구분)", height=200, key="bulk_daily_tsv")
    col_preview, col_commit = st.columns(2)
    parsed = None
    if text.strip():
        parsed = parse_tsv(text)
        with col_preview:
            st.metric("파싱 성공", parsed.to_dict()["parsed_count"])
        with col_commit:
            st.metric("파싱 실패", parsed.to_dict()["failed_count"])
        if parsed.rows:
            st.success(f"{len(parsed.rows)}행이 파싱되었습니다. 아래 미리보기를 확인 후 저장하세요.")
            st.dataframe(parsed.to_dict()["rows"], use_container_width=True, hide_index=True)
        if parsed.failed_rows:
            st.warning(f"실패 {len(parsed.failed_rows)}건 — 사유 확인 후 수정해서 다시 붙여넣으세요.")
            st.dataframe(parsed.failed_rows, use_container_width=True, hide_index=True)

    if parsed and parsed.rows and st.button("💾 일괄 저장", type="primary"):
        result = apply_parsed_rows(project_path, parsed)
        st.success(f"✅ {result['created']}건 저장 완료")
        if result["skipped"]:
            st.warning(f"⚠ 건너뜀 {len(result['skipped'])}건 (작업 코드 미존재 등)")
            st.dataframe(result["skipped"], use_container_width=True, hide_index=True)
        if result["errors"]:
            st.error(f"❌ 오류 {len(result['errors'])}건")
            st.dataframe(result["errors"], use_container_width=True, hide_index=True)
