"""Tests for report_parser — Excel 파싱, JSON 추출 헬퍼, 프로바이더 분기."""
from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from core.report_parser import (
    _parse_date,
    _parse_json_response,
    _call_claude_vision,
    _call_gemini_vision,
    parse_report_excel,
    parse_report_image,
)

# 샘플 Excel 파일 경로 (실제 파일 없으면 skip)
SAMPLE_EXCEL = Path(
    r"C:\Users\User\Documents\카카오톡 받은 파일\★표준 출력일보 샘플_설비팀_20240425.xlsx"
)


# ─── _parse_date ──────────────────────────────────────────────────────────────

class TestParseDate:
    def test_dot_format(self):
        assert _parse_date("2024.04.25") == "2024-04-25"

    def test_dot_format_with_weekday(self):
        assert _parse_date("2024.04.25 (목)") == "2024-04-25"

    def test_iso_format(self):
        assert _parse_date("2024-04-25") == "2024-04-25"

    def test_korean_format(self):
        assert _parse_date("2024년 4월 25일") == "2024-04-25"

    def test_none_input(self):
        assert _parse_date(None) is None

    def test_empty_string(self):
        assert _parse_date("") is None

    def test_unrecognized(self):
        assert _parse_date("팀 체크") is None


# ─── _parse_json_response ─────────────────────────────────────────────────────

class TestParseJsonResponse:
    def test_clean_json(self):
        raw = '{"work_date": "2024-04-25", "team_name": "설비팀", "work_items": [], "equipment": [], "supplies": [], "summary": "test"}'
        result = _parse_json_response(raw)
        assert result["work_date"] == "2024-04-25"
        assert result["team_name"] == "설비팀"

    def test_json_in_code_block(self):
        raw = '```json\n{"work_date": "2024.04.25", "summary": "작업"}\n```'
        result = _parse_json_response(raw)
        assert result["work_date"] == "2024-04-25"

    def test_date_normalization(self):
        raw = '{"work_date": "2024.04.25 (목)", "summary": ""}'
        result = _parse_json_response(raw)
        assert result["work_date"] == "2024-04-25"

    def test_defaults_filled(self):
        raw = '{"work_date": "2024-04-25"}'
        result = _parse_json_response(raw)
        assert result["work_items"] == []
        assert result["equipment"] == []
        assert result["supplies"] == []

    def test_broken_json_returns_empty(self):
        raw = "파싱 실패 메시지 (JSON 없음)"
        result = _parse_json_response(raw)
        assert isinstance(result, dict)
        assert len(result.get("warnings", [])) > 0


# ─── parse_report_excel ───────────────────────────────────────────────────────

@pytest.mark.skipif(not SAMPLE_EXCEL.exists(), reason="샘플 Excel 파일 없음")
class TestParseReportExcel:
    def test_returns_dict(self):
        data = parse_report_excel(SAMPLE_EXCEL.read_bytes())
        assert isinstance(data, dict)

    def test_work_date_parsed(self):
        data = parse_report_excel(SAMPLE_EXCEL.read_bytes())
        assert data["work_date"] == "2024-04-25"

    def test_work_items_non_empty(self):
        data = parse_report_excel(SAMPLE_EXCEL.read_bytes())
        assert len(data["work_items"]) > 0

    def test_equipment_non_empty(self):
        data = parse_report_excel(SAMPLE_EXCEL.read_bytes())
        assert len(data["equipment"]) > 0

    def test_no_critical_warnings(self):
        data = parse_report_excel(SAMPLE_EXCEL.read_bytes())
        # 날짜 파싱 실패 경고 없어야 함
        crit = [w for w in data.get("warnings", []) if "파싱 실패" in w]
        assert len(crit) == 0

    def test_summary_non_empty(self):
        data = parse_report_excel(SAMPLE_EXCEL.read_bytes())
        assert data.get("summary", "")


# ─── 프로바이더 분기 테스트 ──────────────────────────────────────────────────────

class TestProviderDispatch:
    _FAKE_RESPONSE = '{"work_date":"2024-04-25","team_name":"테스트","work_items":[],"equipment":[],"supplies":[],"summary":"ok"}'
    _DUMMY_IMG = b"\xff\xd8\xff"   # 최소 JPEG 헤더

    def test_dispatch_gemini(self, monkeypatch):
        """VISION_PROVIDER=gemini → _call_gemini_vision 호출."""
        monkeypatch.setenv("VISION_PROVIDER", "gemini")
        with patch("core.report_parser._call_gemini_vision") as mock_g:
            mock_g.return_value = {"work_date": "2024-04-25", "warnings": []}
            result = parse_report_image(self._DUMMY_IMG)
            mock_g.assert_called_once()
            assert result["work_date"] == "2024-04-25"

    def test_dispatch_claude(self, monkeypatch):
        """VISION_PROVIDER=claude → _call_claude_vision 호출."""
        monkeypatch.setenv("VISION_PROVIDER", "claude")
        with patch("core.report_parser._call_claude_vision") as mock_c:
            mock_c.return_value = {"work_date": "2024-04-25", "warnings": []}
            result = parse_report_image(self._DUMMY_IMG)
            mock_c.assert_called_once()
            assert result["work_date"] == "2024-04-25"

    def test_unknown_provider_raises(self, monkeypatch):
        """알 수 없는 프로바이더 → RuntimeError."""
        monkeypatch.setenv("VISION_PROVIDER", "openai")
        with pytest.raises(RuntimeError, match="지원하지 않는 VISION_PROVIDER"):
            parse_report_image(self._DUMMY_IMG)

    def test_gemini_missing_api_key_raises(self, monkeypatch):
        """GEMINI_API_KEY 없으면 RuntimeError."""
        monkeypatch.setenv("VISION_PROVIDER", "gemini")
        monkeypatch.delenv("GEMINI_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="GEMINI_API_KEY"):
            _call_gemini_vision(self._DUMMY_IMG, "image/jpeg")

    def test_claude_missing_api_key_raises(self, monkeypatch):
        """ANTHROPIC_API_KEY 없으면 RuntimeError."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        with pytest.raises(RuntimeError, match="ANTHROPIC_API_KEY"):
            _call_claude_vision(self._DUMMY_IMG, "image/jpeg")
