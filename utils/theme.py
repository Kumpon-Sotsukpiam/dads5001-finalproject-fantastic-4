"""
utils/theme.py
--------------
Modern clean theme — light background, navy accent, white cards.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

# ── Colour palette ────────────────────────────────────────────────────────────
COLORS = {
    "primary":   "#1B3A6B",
    "secondary": "#2E6CB8",
    "accent":    "#F5A623",
    "success":   "#27AE60",
    "warning":   "#E67E22",
    "danger":    "#E74C3C",
    "light":     "#F0F4FA",
    "muted":     "#8492A6",
    "white":     "#FFFFFF",
}

CHART_COLORS = [
    "#2E6CB8", "#F5A623", "#27AE60", "#E74C3C",
    "#8E44AD", "#16A085", "#E67E22", "#1B3A6B",
]


def _build_template():
    """Build and return the BKK Plotly template object."""
    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor="#FFFFFF",
        plot_bgcolor="#FAFBFD",
        font=dict(family="Inter, sans-serif", color="#2C3E50", size=12),
        title=dict(font=dict(color="#1B3A6B", size=15, family="Inter, sans-serif")),
        xaxis=dict(
            gridcolor="#E8EDF5", linecolor="#D0D9E8",
            tickcolor="#8492A6", tickfont=dict(color="#8492A6"),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor="#E8EDF5", linecolor="#D0D9E8",
            tickcolor="#8492A6", tickfont=dict(color="#8492A6"),
            zeroline=False,
        ),
        legend=dict(
            bgcolor="rgba(255,255,255,0.9)",
            bordercolor="#E8EDF5", borderwidth=1,
            font=dict(color="#2C3E50"),
        ),
        margin=dict(l=40, r=20, t=40, b=40),
        colorway=CHART_COLORS,
    )
    return t


# Exported template object — use this directly in chart calls instead of the
# string "bkk" so it works even if pio.templates hasn't been populated yet.
BKK_TEMPLATE = _build_template()

# Register once at import time (best-effort; re-registered in inject_css too)
pio.templates["bkk"] = BKK_TEMPLATE
pio.templates.default = "bkk"


def inject_css():
    # Re-register template every page load (Streamlit Cloud workers share nothing)
    pio.templates["bkk"] = BKK_TEMPLATE
    pio.templates.default = "bkk"

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300;0,14..32,400;0,14..32,500;0,14..32,600;0,14..32,700;1,14..32,400&display=swap');

    /* ── Global ── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
        background-color: #F0F4FA !important;
    }

    /* ── Main content area ── */
    .main .block-container {
        padding: 2rem 2.5rem 2rem 2.5rem !important;
        max-width: 1400px !important;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: #1B3A6B !important;
        border-right: none !important;
    }
    [data-testid="stSidebar"] > div {
        padding-top: 1.5rem;
    }
    /* Nav links */
    [data-testid="stSidebarNav"] a {
        color: #B8CCE8 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        padding: 0.4rem 0.8rem !important;
        transition: all 0.15s ease;
    }
    [data-testid="stSidebarNav"] a:hover,
    [data-testid="stSidebarNav"] a[aria-selected="true"] {
        background: rgba(245,166,35,0.18) !important;
        color: #F5A623 !important;
    }
    /* Sidebar text */
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {
        color: #B8CCE8 !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #F5A623 !important;
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.1) !important;
        margin: 0.8rem 0 !important;
    }

    /* ── Toggle ── */
    [data-testid="stToggle"] {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.15);
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
    }
    [data-testid="stToggle"] p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
    }

    /* ── Page titles ── */
    [data-testid="stHeadingWithActionElements"] h1 {
        color: #1B3A6B !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        letter-spacing: -0.02em;
        border-bottom: 3px solid #F5A623 !important;
        padding-bottom: 0.5rem !important;
        margin-bottom: 0.2rem !important;
    }
    [data-testid="stHeadingWithActionElements"] h2 {
        color: #1B3A6B !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
    }
    [data-testid="stHeadingWithActionElements"] h3 {
        color: #2E6CB8 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: #FFFFFF !important;
        border: 1px solid #E2EAF4 !important;
        border-top: 3px solid #F5A623 !important;
        border-radius: 12px !important;
        padding: 1.1rem 1.3rem !important;
        box-shadow: 0 1px 6px rgba(27,58,107,0.07) !important;
        transition: box-shadow 0.2s;
    }
    [data-testid="stMetric"]:hover {
        box-shadow: 0 4px 16px rgba(27,58,107,0.13) !important;
    }
    [data-testid="stMetricLabel"] > div {
        color: #8492A6 !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }
    [data-testid="stMetricValue"] > div {
        color: #1B3A6B !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background: linear-gradient(135deg, #1B3A6B, #2E6CB8) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        font-size: 0.88rem !important;
        padding: 0.5rem 1.4rem !important;
        box-shadow: 0 2px 8px rgba(27,58,107,0.2) !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button:hover {
        background: linear-gradient(135deg, #F5A623, #E8941A) !important;
        color: #1B3A6B !important;
        box-shadow: 0 4px 14px rgba(245,166,35,0.35) !important;
        transform: translateY(-1px) !important;
    }

    /* ── Alert boxes ── */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        border: none !important;
        font-size: 0.88rem !important;
    }
    div[data-baseweb="notification"] {
        border-radius: 10px !important;
    }

    /* ── Plotly chart wrapper ── */
    [data-testid="stPlotlyChart"] > div {
        border-radius: 14px !important;
        overflow: hidden !important;
        box-shadow: 0 1px 8px rgba(27,58,107,0.08) !important;
        background: #FFFFFF !important;
    }

    /* ── DataFrame ── */
    [data-testid="stDataFrame"] {
        border-radius: 12px !important;
        overflow: hidden !important;
        box-shadow: 0 1px 8px rgba(27,58,107,0.08) !important;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        background: #FFFFFF !important;
        border: 1px solid #E2EAF4 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 6px rgba(27,58,107,0.06) !important;
    }

    /* ── Multiselect tags ── */
    [data-baseweb="tag"] {
        background-color: #1B3A6B !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tag"] span {
        color: #FFFFFF !important;
    }

    /* ── Divider ── */
    hr {
        border-color: #E2EAF4 !important;
        margin: 1rem 0 !important;
    }

    /* ── Caption ── */
    [data-testid="stCaptionContainer"] p {
        color: #8492A6 !important;
        font-size: 0.78rem !important;
    }

    /* ── Spinner ── */
    .stSpinner > div {
        border-top-color: #2E6CB8 !important;
    }
    </style>
    """, unsafe_allow_html=True)
