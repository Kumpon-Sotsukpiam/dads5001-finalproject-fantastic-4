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


def _build_template(dark=False):
    """Build and return the BKK Plotly template object."""
    if dark:
        paper_bg, plot_bg = "#1E2330", "#252B3B"
        font_color, grid_color, tick_color = "#C8D6E8", "#2E3A50", "#6A7F9A"
        legend_bg = "rgba(30,35,48,0.9)"
    else:
        paper_bg, plot_bg = "#FFFFFF", "#FAFBFD"
        font_color, grid_color, tick_color = "#2C3E50", "#E8EDF5", "#8492A6"
        legend_bg = "rgba(255,255,255,0.9)"

    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor=paper_bg,
        plot_bgcolor=plot_bg,
        font=dict(family="Inter, sans-serif", color=font_color, size=12),
        title=dict(font=dict(color="#4A90D9", size=15, family="Inter, sans-serif")),
        xaxis=dict(
            gridcolor=grid_color, linecolor=grid_color,
            tickcolor=tick_color, tickfont=dict(color=tick_color),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=grid_color, linecolor=grid_color,
            tickcolor=tick_color, tickfont=dict(color=tick_color),
            zeroline=False,
        ),
        legend=dict(
            bgcolor=legend_bg,
            bordercolor=grid_color, borderwidth=1,
            font=dict(color=font_color),
        ),
        margin=dict(l=40, r=20, t=40, b=40),
        colorway=CHART_COLORS,
    )
    return t


# Exported template object — always light (Plotly charts use white bg)
BKK_TEMPLATE = _build_template(dark=False)

# Register once at import time (best-effort; re-registered in inject_css too)
pio.templates["bkk"] = BKK_TEMPLATE
pio.templates.default = "bkk"


def inject_css():
    # Re-register template every page load (Streamlit Cloud workers share nothing)
    pio.templates["bkk"] = BKK_TEMPLATE
    pio.templates.default = "bkk"

    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Font ── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', sans-serif !important;
    }

    /* ── Layout ── */
    .main .block-container {
        padding: 2rem 2.5rem !important;
        max-width: 1400px !important;
    }

    /* ════════════════════════════════════════════════════
       SIDEBAR — always navy (brand color, both themes)
    ════════════════════════════════════════════════════ */
    [data-testid="stSidebar"] {
        background: #1B3A6B !important;
        border-right: none !important;
    }
    [data-testid="stSidebar"] > div { padding-top: 1.5rem; }

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
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div { color: #B8CCE8 !important; }
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
    [data-testid="stSidebar"] [data-testid="stToggle"] {
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
    }
    [data-testid="stSidebar"] [data-testid="stToggle"] p {
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }

    /* ════════════════════════════════════════════════════
       MAIN CONTENT — use Streamlit CSS variables
       so colours adapt automatically to light/dark theme
    ════════════════════════════════════════════════════ */

    /* Page titles — accent amber underline, text follows theme */
    [data-testid="stHeadingWithActionElements"] h1 {
        color: var(--text-color) !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        letter-spacing: -0.02em;
        border-bottom: 3px solid #F5A623 !important;
        padding-bottom: 0.5rem !important;
        margin-bottom: 0.2rem !important;
    }
    [data-testid="stHeadingWithActionElements"] h2 {
        color: var(--text-color) !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
    }
    [data-testid="stHeadingWithActionElements"] h3 {
        color: var(--text-color) !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    /* Metric cards — border follows theme bg */
    [data-testid="stMetric"] {
        border-top: 3px solid #F5A623 !important;
        border-radius: 12px !important;
        padding: 1.1rem 1.3rem !important;
        background: var(--background-color) !important;
        border-left: 1px solid rgba(128,128,128,0.2) !important;
        border-right: 1px solid rgba(128,128,128,0.2) !important;
        border-bottom: 1px solid rgba(128,128,128,0.2) !important;
        transition: box-shadow 0.2s;
    }
    [data-testid="stMetricLabel"] > div {
        color: var(--text-color) !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
        opacity: 0.65;
    }
    [data-testid="stMetricValue"] > div {
        color: var(--text-color) !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }

    /* Toggle in main content */
    .main [data-testid="stToggle"] {
        border-radius: 10px;
        padding: 0.6rem 1rem;
        border: 1.5px solid rgba(128,128,128,0.25);
        background: var(--background-color);
    }

    /* Buttons */
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

    /* Alert boxes */
    [data-testid="stAlert"] {
        border-radius: 10px !important;
        font-size: 0.88rem !important;
    }

    /* Plotly chart wrapper */
    [data-testid="stPlotlyChart"] > div {
        border-radius: 14px !important;
        overflow: hidden !important;
        box-shadow: 0 1px 8px rgba(0,0,0,0.1) !important;
    }

    /* DataFrame & Expander */
    [data-testid="stDataFrame"],
    [data-testid="stExpander"] {
        border-radius: 12px !important;
        overflow: hidden !important;
    }

    /* Multiselect tags */
    [data-baseweb="tag"] {
        background-color: #2E6CB8 !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tag"] span { color: #FFFFFF !important; }

    /* Caption */
    [data-testid="stCaptionContainer"] p {
        font-size: 0.78rem !important;
        opacity: 0.7;
    }

    /* Spinner */
    .stSpinner > div { border-top-color: #2E6CB8 !important; }

    /* Divider */
    hr { margin: 1rem 0 !important; }
    </style>
    """, unsafe_allow_html=True)
