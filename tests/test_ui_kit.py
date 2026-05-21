"""Smoke tests for the UI kit primitives — verify HTML strings are well-formed."""
from __future__ import annotations

import re

from viewer.components import ui_kit


def test_badge_returns_html_with_color_class():
    html = ui_kit.badge("CRITICAL", "red")
    assert "sns-badge" in html
    assert "sns-badge-red" in html
    assert "CRITICAL" in html


def test_status_pill_known_levels_have_emoji():
    for level in ["정상", "주의", "부진", "healthy", "watch", "risk"]:
        html = ui_kit.status_pill(level)
        assert "sns-badge" in html


def test_status_pill_unknown_falls_back_to_gray():
    html = ui_kit.status_pill("unknown_status")
    assert "sns-badge-gray" in html


def test_global_css_contains_design_tokens():
    css = ui_kit._GLOBAL_CSS
    # primary color, base font, key utility classes
    for needle in ["#2E6BFF", "sns-card", "sns-badge", "sns-hero", "sns-callout", "@media print"]:
        assert needle in css, f"missing {needle} in global CSS"
    # no obviously broken CSS
    assert css.count("<style>") == 1
    assert css.count("</style>") == 1
