"""Reusable UI primitives for a consistent, modern look across all pages.

Design tokens (single source of truth):
- Primary:   #2E6BFF (코발트 블루)
- Success:   #16A34A
- Warning:   #F59E0B
- Danger:    #DC2626
- Surface:   #FFFFFF / #F7F9FC
- Border:    #E2E8F0
- Text:      #1A2540 / muted #64748B

All components are pure-streamlit (no external JS) and degrade gracefully
in print mode.
"""
from __future__ import annotations

from typing import Iterable, Literal


# --------------------------------------------------------------------------- #
# Global CSS — inject once per page via inject_global_css()
# --------------------------------------------------------------------------- #

_GLOBAL_CSS = """
<style>
/* ---- Typography & base layout ---- */
html, body, [class*="css"] {
  font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Malgun Gothic', sans-serif;
  letter-spacing: -0.01em;
}
.block-container {
  padding-top: 1.2rem;
  padding-bottom: 2rem;
  max-width: 1280px;
}
h1, h2, h3 { color: #1A2540; font-weight: 700; }
h1 { font-size: 1.65rem !important; }
h2 { font-size: 1.30rem !important; }
h3 { font-size: 1.10rem !important; }

/* ---- Streamlit metric polish ---- */
[data-testid="stMetric"] {
  background: #FFFFFF;
  padding: 14px 18px;
  border: 1px solid #E2E8F0;
  border-radius: 12px;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04);
  transition: transform .12s ease, box-shadow .12s ease;
}
[data-testid="stMetric"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 10px rgba(15,23,42,0.06);
}
[data-testid="stMetricLabel"] { color: #64748B !important; font-weight: 500; font-size: 0.85rem; }
[data-testid="stMetricValue"] { color: #1A2540 !important; font-weight: 700; font-size: 1.55rem; }
[data-testid="stMetricDelta"] { font-weight: 600; }

/* ---- Buttons ---- */
.stButton > button {
  border-radius: 10px;
  font-weight: 600;
  padding: 0.45rem 1.05rem;
  transition: all .15s ease;
}
.stButton > button[kind="primary"] {
  background: linear-gradient(180deg, #2E6BFF 0%, #1E4FCC 100%);
  border: none;
  box-shadow: 0 1px 2px rgba(46,107,255,0.25);
}
.stButton > button[kind="primary"]:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(46,107,255,0.35);
}

/* ---- Inputs ---- */
input, textarea, select {
  border-radius: 8px !important;
}
.stTextInput input, .stNumberInput input, .stTextArea textarea, .stSelectbox div[role="combobox"] {
  border-color: #CBD5E1 !important;
}

/* ---- Tabs ---- */
[data-baseweb="tab-list"] {
  gap: 4px;
  border-bottom: 1px solid #E2E8F0;
}
[data-baseweb="tab"] {
  padding: 10px 18px;
  border-radius: 10px 10px 0 0;
  font-weight: 500;
  color: #64748B;
}
[data-baseweb="tab"][aria-selected="true"] {
  background: #EFF4FF;
  color: #2E6BFF;
  font-weight: 700;
}

/* ---- Sidebar ---- */
section[data-testid="stSidebar"] {
  background: #FFFFFF;
  border-right: 1px solid #E2E8F0;
}
section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2 { font-size: 1.0rem !important; }

/* ---- Custom utility classes ---- */
.sns-card {
  background: #FFFFFF;
  border: 1px solid #E2E8F0;
  border-radius: 14px;
  padding: 18px 22px;
  box-shadow: 0 1px 2px rgba(15,23,42,0.04);
  margin-bottom: 14px;
}
.sns-card-header {
  display: flex; align-items: center; gap: 10px;
  font-weight: 700; color: #1A2540; font-size: 1.05rem;
  margin-bottom: 8px;
}
.sns-card-sub { color: #64748B; font-size: 0.85rem; margin-bottom: 12px; }

.sns-badge {
  display: inline-block;
  padding: 3px 12px;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 600;
  letter-spacing: 0.01em;
}
.sns-badge-green   { background: #DCFCE7; color: #15803D; }
.sns-badge-yellow  { background: #FEF3C7; color: #B45309; }
.sns-badge-red     { background: #FEE2E2; color: #B91C1C; }
.sns-badge-blue    { background: #DBEAFE; color: #1D4ED8; }
.sns-badge-gray    { background: #F1F5F9; color: #475569; }

.sns-hero {
  background: linear-gradient(135deg, #2E6BFF 0%, #1E4FCC 100%);
  color: white;
  padding: 28px 32px;
  border-radius: 18px;
  margin-bottom: 22px;
  box-shadow: 0 6px 20px rgba(46,107,255,0.20);
}
.sns-hero h1 { color: white !important; margin: 0 0 6px 0; font-size: 1.8rem !important; }
.sns-hero p { color: rgba(255,255,255,0.92); margin: 0; font-size: 0.95rem; }

.sns-section-divider {
  height: 1px;
  background: linear-gradient(90deg, transparent, #E2E8F0, transparent);
  margin: 22px 0;
}

.sns-callout {
  border-left: 4px solid #2E6BFF;
  background: #EFF4FF;
  padding: 12px 16px;
  border-radius: 8px;
  margin: 10px 0;
  color: #1A2540;
}
.sns-callout-warning { border-left-color: #F59E0B; background: #FFFBEB; }
.sns-callout-danger  { border-left-color: #DC2626; background: #FEF2F2; }
.sns-callout-success { border-left-color: #16A34A; background: #F0FDF4; }

/* ---- Mobile-friendly tweaks ---- */
@media (max-width: 768px) {
  .block-container { padding: 0.5rem !important; }
  .sns-hero { padding: 18px 20px; }
  .sns-hero h1 { font-size: 1.4rem !important; }
  [data-testid="stMetricValue"] { font-size: 1.3rem; }
}

/* ---- Print mode (A4 1매) ---- */
@media print {
  section[data-testid="stSidebar"], header, footer,
  [data-testid="stToolbar"], .stDeployButton { display: none !important; }
  .block-container { padding: 0 !important; max-width: 100% !important; }
  .sns-hero { background: #1E4FCC !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  .sns-card { box-shadow: none; break-inside: avoid; }
}
</style>
"""


def inject_global_css() -> None:
    """Apply the global stylesheet. Safe to call multiple times per page."""
    import streamlit as st

    st.markdown(_GLOBAL_CSS, unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Hero header — sits at the top of every primary page
# --------------------------------------------------------------------------- #

def hero(title: str, subtitle: str = "", icon: str = "🏗️") -> None:
    import streamlit as st

    st.markdown(
        f"""
        <div class="sns-hero">
          <h1>{icon}  {title}</h1>
          {f'<p>{subtitle}</p>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Section header — smaller, with icon + optional caption
# --------------------------------------------------------------------------- #

def section(title: str, caption: str = "", icon: str = "") -> None:
    import streamlit as st

    icon_html = f"<span style='margin-right:6px'>{icon}</span>" if icon else ""
    cap_html = f"<div class='sns-card-sub'>{caption}</div>" if caption else ""
    st.markdown(
        f"""
        <h2 style="margin:18px 0 4px 0; display:flex; align-items:center;">{icon_html}{title}</h2>
        {cap_html}
        """,
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Status badge (green / yellow / red / blue / gray)
# --------------------------------------------------------------------------- #

BadgeColor = Literal["green", "yellow", "red", "blue", "gray"]


def badge(text: str, color: BadgeColor = "blue") -> str:
    """Return an inline HTML span — pair with st.markdown(..., unsafe_allow_html=True)."""
    return f'<span class="sns-badge sns-badge-{color}">{text}</span>'


def status_pill(level: str) -> str:
    """Map common status text → colored badge."""
    mapping = {
        "정상": ("green", "🟢 정상"),
        "ok": ("green", "🟢 OK"),
        "healthy": ("green", "🟢 양호"),
        "주의": ("yellow", "🟡 주의"),
        "watch": ("yellow", "🟡 주의"),
        "warning": ("yellow", "🟡 주의"),
        "부진": ("red", "🔴 부진"),
        "risk": ("red", "🔴 위험"),
        "error": ("red", "🔴 오류"),
        "danger": ("red", "🔴 위험"),
        "critical": ("red", "🔴 임계"),
    }
    key = (level or "").strip().lower()
    color, label = mapping.get(key, ("gray", level or "-"))
    return badge(label, color)


# --------------------------------------------------------------------------- #
# Callout — info / warning / danger / success
# --------------------------------------------------------------------------- #

CalloutKind = Literal["info", "warning", "danger", "success"]


def callout(kind: CalloutKind, message: str, *, title: str | None = None) -> None:
    import streamlit as st

    suffix = {"info": "", "warning": "-warning", "danger": "-danger", "success": "-success"}[kind]
    title_html = f"<strong>{title}</strong><br>" if title else ""
    st.markdown(
        f'<div class="sns-callout sns-callout{suffix}">{title_html}{message}</div>',
        unsafe_allow_html=True,
    )


# --------------------------------------------------------------------------- #
# Card container — use as a context manager
# --------------------------------------------------------------------------- #

class Card:
    def __init__(self, title: str | None = None, icon: str = "", subtitle: str = "") -> None:
        self.title = title
        self.icon = icon
        self.subtitle = subtitle

    def __enter__(self):
        import streamlit as st

        self._st = st
        st.markdown('<div class="sns-card">', unsafe_allow_html=True)
        if self.title:
            icon_html = f"{self.icon}  " if self.icon else ""
            st.markdown(
                f'<div class="sns-card-header">{icon_html}{self.title}</div>',
                unsafe_allow_html=True,
            )
        if self.subtitle:
            st.markdown(f'<div class="sns-card-sub">{self.subtitle}</div>', unsafe_allow_html=True)
        return self

    def __exit__(self, *_args):
        self._st.markdown("</div>", unsafe_allow_html=True)


def card(title: str | None = None, icon: str = "", subtitle: str = "") -> Card:
    """Convenience: ``with card("제목"): st.write(...)``."""
    return Card(title=title, icon=icon, subtitle=subtitle)


# --------------------------------------------------------------------------- #
# Divider
# --------------------------------------------------------------------------- #

def divider() -> None:
    import streamlit as st

    st.markdown('<div class="sns-section-divider"></div>', unsafe_allow_html=True)


# --------------------------------------------------------------------------- #
# Big stat row — 2-4 metrics with consistent spacing
# --------------------------------------------------------------------------- #

def stats_row(items: Iterable[tuple[str, str]] | Iterable[tuple[str, str, str]]) -> None:
    """Render a row of metrics from (label, value[, delta]) tuples."""
    import streamlit as st

    items = list(items)
    cols = st.columns(len(items))
    for col, item in zip(cols, items):
        if len(item) == 3:
            col.metric(item[0], item[1], item[2])
        else:
            col.metric(item[0], item[1])


# --------------------------------------------------------------------------- #
# Quick-action button row
# --------------------------------------------------------------------------- #

def action_row(actions: list[tuple[str, str, str]]) -> str | None:
    """Render a row of large action buttons.

    ``actions`` is a list of ``(icon, label, key)`` tuples.
    Returns the ``key`` of the clicked button (or None).
    """
    import streamlit as st

    cols = st.columns(len(actions))
    clicked: str | None = None
    for col, (icon, label, key) in zip(cols, actions):
        with col:
            if st.button(f"{icon}\n\n**{label}**", key=key, use_container_width=True):
                clicked = key
    return clicked
