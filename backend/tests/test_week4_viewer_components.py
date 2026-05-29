from __future__ import annotations

from viewer.components.gantt_panel import render as render_gantt
from viewer.components.report_panel import generate_report_from_viewer
from viewer.components.s_curve_panel import render as render_s_curve


def test_week4_viewer_components_are_importable():
    assert callable(render_gantt)
    assert callable(render_s_curve)
    assert callable(generate_report_from_viewer)
