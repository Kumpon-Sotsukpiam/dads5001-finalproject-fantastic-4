"""
utils/theme.py
--------------
Dual-theme design: detects Streamlit light/dark and applies matching styles.
Sidebar is always navy (brand identity).
Plotly charts adapt background to match the active theme.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

# ── Brand colours (theme-independent) ────────────────────────────────────────
CHART_COLORS = [
    "#2E6CB8", "#F5A623", "#27AE60", "#E74C3C",
    "#8E44AD", "#16A085", "#E67E22", "#4A90D9",
]

# ── Light theme palette ───────────────────────────────────────────────────────
LIGHT = {
    "bg":          "#F0F4FA",
    "card":        "#FFFFFF",
    "border":      "#E2EAF4",
    "text":        "#1A2233",
    "text_muted":  "#6B7A99",
    "heading":     "#1B3A6B",
    "subheading":  "#2E6CB8",
    "chart_paper": "#FFFFFF",
    "chart_plot":  "#FAFBFD",
    "chart_grid":  "#E8EDF5",
    "chart_tick":  "#8492A6",
    "chart_font":  "#2C3E50",
    "legend_bg":   "rgba(255,255,255,0.95)",
}

# ── Dark theme palette ────────────────────────────────────────────────────────
DARK = {
    "bg":          "#0E1117",
    "card":        "#1A1F2E",
    "border":      "#2A3248",
    "text":        "#E8EDF8",
    "text_muted":  "#8A9BBF",
    "heading":     "#7EB3F5",
    "subheading":  "#5A9FE8",
    "chart_paper": "#1A1F2E",
    "chart_plot":  "#1E2438",
    "chart_grid":  "#2A3248",
    "chart_tick":  "#5A6A8A",
    "chart_font":  "#C8D6E8",
    "legend_bg":   "rgba(26,31,46,0.95)",
}


def _is_dark() -> bool:
    """Detect if Streamlit is running in dark mode."""
    try:
        theme = st.context.theme  # Streamlit >= 1.35
        return getattr(theme, "base", "light") == "dark"
    except Exception:
        pass
    # Fallback: check query params / session state hint
    return st.session_state.get("_dark_mode", False)


def _build_plotly_template(p: dict) -> go.layout.Template:
    t = go.layout.Template()
    t.layout = go.Layout(
        paper_bgcolor=p["chart_paper"],
        plot_bgcolor=p["chart_plot"],
        font=dict(family="Inter, sans-serif", color=p["chart_font"], size=12),
        title=dict(font=dict(color=p["heading"], size=15, family="Inter, sans-serif")),
        xaxis=dict(
            gridcolor=p["chart_grid"], linecolor=p["chart_grid"],
            tickcolor=p["chart_tick"], tickfont=dict(color=p["chart_tick"]),
            zeroline=False,
        ),
        yaxis=dict(
            gridcolor=p["chart_grid"], linecolor=p["chart_grid"],
            tickcolor=p["chart_tick"], tickfont=dict(color=p["chart_tick"]),
            zeroline=False,
        ),
        legend=dict(
            bgcolor=p["legend_bg"], bordercolor=p["chart_grid"],
            borderwidth=1, font=dict(color=p["chart_font"]),
        ),
        margin=dict(l=40, r=20, t=40, b=40),
        colorway=CHART_COLORS,
    )
    return t


# Build both templates at import time
_LIGHT_TEMPLATE = _build_plotly_template(LIGHT)
_DARK_TEMPLATE  = _build_plotly_template(DARK)

# Default export (light) — updated each page load in inject_css()
BKK_TEMPLATE = _LIGHT_TEMPLATE
pio.templates["bkk"] = BKK_TEMPLATE
pio.templates.default = "bkk"


def inject_css():
    """Inject CSS + register Plotly template matching the active theme."""
    global BKK_TEMPLATE

    dark = _is_dark()
    p = DARK if dark else LIGHT

    # Update Plotly template to match theme
    BKK_TEMPLATE = _DARK_TEMPLATE if dark else _LIGHT_TEMPLATE
    pio.templates["bkk"] = BKK_TEMPLATE
    pio.templates.default = "bkk"

    accent  = "#F5A623"
    navy    = "#1B3A6B"
    navy2   = "#2E6CB8"

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    /* ── Font ── */
    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', sans-serif !important;
    }}

    /* ── App background ── */
    .stApp {{
        background-color: {p["bg"]} !important;
    }}

    /* ── Main content layout ── */
    .main .block-container {{
        padding: 2rem 2.5rem !important;
        max-width: 1400px !important;
    }}

    /* ── Default text color ── */
    .main p, .main span, .main div, .main label {{
        color: {p["text"]} !important;
    }}

    /* ════════════════════════════════════
       SIDEBAR — always navy (both themes)
    ════════════════════════════════════ */
    [data-testid="stSidebar"] {{
        background: {navy} !important;
        border-right: none !important;
    }}
    [data-testid="stSidebar"] > div {{ padding-top: 1.5rem; }}
    [data-testid="stSidebarNav"] a {{
        color: #B8CCE8 !important;
        font-size: 0.88rem !important;
        font-weight: 500 !important;
        border-radius: 8px !important;
        padding: 0.4rem 0.8rem !important;
        transition: all 0.15s ease;
    }}
    [data-testid="stSidebarNav"] a:hover,
    [data-testid="stSidebarNav"] a[aria-selected="true"] {{
        background: rgba(245,166,35,0.18) !important;
        color: {accent} !important;
    }}
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {{ color: #B8CCE8 !important; }}
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3 {{
        color: {accent} !important;
        font-size: 0.7rem !important;
        font-weight: 700 !important;
        letter-spacing: 0.1em !important;
        text-transform: uppercase !important;
    }}
    [data-testid="stSidebar"] hr {{
        border-color: rgba(255,255,255,0.1) !important;
        margin: 0.8rem 0 !important;
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] {{
        background: rgba(255,255,255,0.08);
        border: 1px solid rgba(255,255,255,0.2);
        border-radius: 10px;
        padding: 0.5rem 0.8rem;
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] p {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}

    /* ════════════════════════════════════
       HEADINGS
    ════════════════════════════════════ */
    [data-testid="stHeadingWithActionElements"] h1 {{
        color: {p["heading"]} !important;
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        letter-spacing: -0.02em;
        border-bottom: 3px solid {accent} !important;
        padding-bottom: 0.5rem !important;
        margin-bottom: 0.2rem !important;
    }}
    [data-testid="stHeadingWithActionElements"] h2 {{
        color: {p["heading"]} !important;
        font-weight: 600 !important;
        font-size: 1.15rem !important;
    }}
    [data-testid="stHeadingWithActionElements"] h3 {{
        color: {p["subheading"]} !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }}

    /* ════════════════════════════════════
       METRIC CARDS
    ════════════════════════════════════ */
    [data-testid="stMetric"] {{
        background: {p["card"]} !important;
        border: 1px solid {p["border"]} !important;
        border-top: 3px solid {accent} !important;
        border-radius: 12px !important;
        padding: 1.1rem 1.3rem !important;
        box-shadow: 0 1px 6px rgba(0,0,0,0.08) !important;
        transition: box-shadow 0.2s;
    }}
    [data-testid="stMetricLabel"] > div {{
        color: {p["text_muted"]} !important;
        font-size: 0.72rem !important;
        font-weight: 600 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.06em !important;
    }}
    [data-testid="stMetricValue"] > div {{
        color: {p["text"]} !important;
        font-size: 1.75rem !important;
        font-weight: 700 !important;
        letter-spacing: -0.02em !important;
    }}

    /* ════════════════════════════════════
       BUTTONS
    ════════════════════════════════════ */
    .stButton > button {{
        background: linear-gradient(135deg, {navy}, {navy2}) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.4rem !important;
        box-shadow: 0 2px 8px rgba(27,58,107,0.2) !important;
        transition: all 0.2s ease !important;
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {accent}, #E8941A) !important;
        color: {navy} !important;
        box-shadow: 0 4px 14px rgba(245,166,35,0.35) !important;
        transform: translateY(-1px) !important;
    }}

    /* ════════════════════════════════════
       CARDS / EXPANDER
    ════════════════════════════════════ */
    [data-testid="stExpander"] {{
        background: {p["card"]} !important;
        border: 1px solid {p["border"]} !important;
        border-radius: 12px !important;
    }}

    /* ════════════════════════════════════
       PLOTLY CHART WRAPPER
    ════════════════════════════════════ */
    [data-testid="stPlotlyChart"] > div {{
        border-radius: 14px !important;
        overflow: hidden !important;
        background: {p["chart_paper"]} !important;
        box-shadow: 0 1px 8px rgba(0,0,0,0.1) !important;
    }}

    /* ════════════════════════════════════
       DATAFRAME
    ════════════════════════════════════ */
    [data-testid="stDataFrame"] {{
        border-radius: 12px !important;
        overflow: hidden !important;
    }}

    /* ════════════════════════════════════
       MULTISELECT TAGS
    ════════════════════════════════════ */
    [data-baseweb="tag"] {{
        background-color: {navy2} !important;
        border-radius: 6px !important;
    }}
    [data-baseweb="tag"] span {{ color: #FFFFFF !important; }}

    /* ════════════════════════════════════
       TOGGLE (main content)
    ════════════════════════════════════ */
    .main [data-testid="stToggle"] {{
        background: {p["card"]};
        border: 1.5px solid {p["border"]};
        border-radius: 10px;
        padding: 0.6rem 1rem;
    }}
    .main [data-testid="stToggle"] p,
    .main [data-testid="stToggle"] label,
    .main [data-testid="stToggle"] span {{
        color: {p["text"]} !important;
        font-weight: 600 !important;
        font-size: 0.95rem !important;
    }}

    /* ════════════════════════════════════
       MISC
    ════════════════════════════════════ */
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
        font-size: 0.88rem !important;
    }}
    [data-testid="stCaptionContainer"] p {{
        color: {p["text_muted"]} !important;
        font-size: 0.78rem !important;
    }}
    .stSpinner > div {{ border-top-color: {navy2} !important; }}
    hr {{ margin: 1rem 0 !important; }}
    </style>
    """, unsafe_allow_html=True)

    return p  # return palette so pages can use it for inline HTML
