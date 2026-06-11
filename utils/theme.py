"""
utils/theme.py
--------------
Bangkok city theme — navy/dark blue primary, amber accent.
Call inject_css() at the top of every page.
"""

import streamlit as st

# Plotly colour palette (use these for charts)
COLORS = {
    "primary":    "#1B3A6B",   # navy blue
    "secondary":  "#2E6CB8",   # mid blue
    "accent":     "#F5A623",   # amber/gold
    "success":    "#27AE60",   # green
    "warning":    "#E67E22",   # orange
    "danger":     "#C0392B",   # red
    "light":      "#EBF2FB",   # pale blue bg
    "text":       "#1A1A2E",   # near-black
    "muted":      "#7F8C8D",   # grey
}

PLOTLY_TEMPLATE = "plotly_white"

CHART_COLORS = [
    "#1B3A6B", "#2E6CB8", "#F5A623", "#27AE60",
    "#E67E22", "#8E44AD", "#16A085", "#C0392B",
]


def inject_css():
    """Inject global CSS into the Streamlit app."""
    st.markdown("""
    <style>
    /* ── Google Font ── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }

    /* ── Main background ── */
    .stApp {
        background-color: #F7F9FC;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1B3A6B 0%, #16305A 100%);
    }
    [data-testid="stSidebar"] * {
        color: #E8EEF8 !important;
    }
    [data-testid="stSidebar"] .stMarkdown p {
        color: #B0BFD8 !important;
        font-size: 0.82rem;
    }
    [data-testid="stSidebar"] hr {
        border-color: #2E4F80 !important;
    }
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {
        color: #F5A623 !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }

    /* ── Page title ── */
    h1 {
        color: #1B3A6B !important;
        font-weight: 700 !important;
        border-bottom: 3px solid #F5A623;
        padding-bottom: 0.4rem;
        margin-bottom: 0.2rem;
    }
    h2 { color: #1B3A6B !important; font-weight: 600 !important; }
    h3 { color: #2E6CB8 !important; font-weight: 600 !important; }

    /* ── Metric cards ── */
    [data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #D6E4F0;
        border-left: 4px solid #F5A623;
        border-radius: 10px;
        padding: 1rem 1.2rem !important;
        box-shadow: 0 2px 8px rgba(27,58,107,0.07);
    }
    [data-testid="stMetricLabel"] {
        color: #7F8C8D !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
    }
    [data-testid="stMetricValue"] {
        color: #1B3A6B !important;
        font-weight: 700 !important;
        font-size: 1.6rem !important;
    }

    /* ── Buttons ── */
    .stButton > button {
        background-color: #1B3A6B !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.2rem !important;
        transition: background 0.2s ease;
    }
    .stButton > button:hover {
        background-color: #F5A623 !important;
        color: #1B3A6B !important;
    }

    /* ── Info/success/warning boxes ── */
    .stInfo {
        background-color: #EBF2FB !important;
        border-left: 4px solid #2E6CB8 !important;
        border-radius: 8px !important;
        color: #1B3A6B !important;
    }
    .stSuccess {
        background-color: #EAFAF1 !important;
        border-left: 4px solid #27AE60 !important;
        border-radius: 8px !important;
    }
    .stWarning {
        background-color: #FEF9E7 !important;
        border-left: 4px solid #F5A623 !important;
        border-radius: 8px !important;
    }

    /* ── Divider ── */
    hr {
        border-color: #D6E4F0 !important;
    }

    /* ── Expander ── */
    [data-testid="stExpander"] {
        border: 1px solid #D6E4F0 !important;
        border-radius: 10px !important;
        background: #FFFFFF !important;
    }

    /* ── Dataframe / table ── */
    [data-testid="stDataFrame"] {
        border-radius: 10px !important;
        overflow: hidden;
        box-shadow: 0 2px 8px rgba(27,58,107,0.07);
    }

    /* ── Caption ── */
    .stCaption {
        color: #7F8C8D !important;
        font-size: 0.78rem !important;
    }

    /* ── Toggle (AI mode) ── */
    [data-testid="stToggle"] label {
        font-weight: 600 !important;
    }

    /* ── Plotly chart container ── */
    [data-testid="stPlotlyChart"] {
        background: #FFFFFF;
        border-radius: 12px;
        padding: 0.5rem;
        box-shadow: 0 2px 8px rgba(27,58,107,0.06);
    }

    /* ── Selectbox / multiselect ── */
    [data-testid="stMultiSelect"] > div,
    [data-testid="stSelectbox"] > div {
        border-radius: 8px !important;
    }
    </style>
    """, unsafe_allow_html=True)
