"""
utils/theme.py
--------------
Dual-theme: Light = white bg / dark text. Dark = pure black bg / light text.
Sidebar always navy. Plotly charts match active theme.
"""

import streamlit as st
import plotly.graph_objects as go
import plotly.io as pio

CHART_COLORS = [
    "#2E6CB8", "#F5A623", "#27AE60", "#E74C3C",
    "#8E44AD", "#16A085", "#E67E22", "#4A90D9",
]

LIGHT = {
    "bg":          "#F0F4FA",
    "card":        "#FFFFFF",
    "border":      "#D0DAF0",
    "text":        "#0D1B2A",
    "text_muted":  "#4A5568",
    "heading":     "#1B3A6B",
    "subheading":  "#2E6CB8",
    "chart_paper": "#FFFFFF",
    "chart_plot":  "#F8FAFF",
    "chart_grid":  "#E2EAF4",
    "chart_tick":  "#6B7A99",
    "chart_font":  "#0D1B2A",
    "legend_bg":   "rgba(255,255,255,0.97)",
}

DARK = {
    "bg":          "#000000",
    "card":        "#111111",
    "border":      "#2A2A2A",
    "text":        "#F5F5F5",
    "text_muted":  "#AAAAAA",
    "heading":     "#90C4FF",
    "subheading":  "#6AAFF0",
    "chart_paper": "#111111",
    "chart_plot":  "#161616",
    "chart_grid":  "#2A2A2A",
    "chart_tick":  "#777777",
    "chart_font":  "#F5F5F5",
    "legend_bg":   "rgba(17,17,17,0.97)",
}


def _is_dark() -> bool:
    try:
        return getattr(st.context.theme, "base", "light") == "dark"
    except Exception:
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


_LIGHT_TEMPLATE = _build_plotly_template(LIGHT)
_DARK_TEMPLATE  = _build_plotly_template(DARK)

BKK_TEMPLATE = _LIGHT_TEMPLATE
pio.templates["bkk"] = BKK_TEMPLATE
pio.templates.default = "bkk"


def inject_css():
    global BKK_TEMPLATE

    dark = _is_dark()
    p = DARK if dark else LIGHT
    BKK_TEMPLATE = _DARK_TEMPLATE if dark else _LIGHT_TEMPLATE
    pio.templates["bkk"] = BKK_TEMPLATE
    pio.templates.default = "bkk"

    accent = "#F5A623"
    navy   = "#1B3A6B"
    navy2  = "#2E6CB8"

    # Background + text — full override for dark, lighter touch for light
    if dark:
        bg_css = f"""
        :root {{ color-scheme: dark; }}
        html {{ background-color: {p["bg"]} !important; }}
        body {{ background-color: {p["bg"]} !important; color: {p["text"]} !important; }}
        .stApp {{ background-color: {p["bg"]} !important; }}
        [data-testid="stAppViewContainer"] {{ background-color: {p["bg"]} !important; }}
        [data-testid="stAppViewContainer"] > section {{ background-color: {p["bg"]} !important; }}
        [data-testid="stMain"] {{ background-color: {p["bg"]} !important; }}
        [data-testid="stMain"] > div {{ background-color: {p["bg"]} !important; }}
        .main {{ background-color: {p["bg"]} !important; }}
        .block-container {{ background-color: {p["bg"]} !important; }}
        section[data-testid="stSidebar"] + div {{ background-color: {p["bg"]} !important; }}
        /* Text contrast */
        .stApp p, .stApp span, .stApp div, .stApp label,
        .stApp li, .stApp td, .stApp th, .stApp h1, .stApp h2, .stApp h3 {{
            color: {p["text"]} !important;
        }}
        """
    else:
        bg_css = f"""
        :root {{ color-scheme: light; }}
        .stApp p, .stApp span, .stApp label,
        .stApp li, .stApp td, .stApp th {{
            color: {p["text"]} !important;
        }}
        """

    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stApp {{
        font-family: 'Inter', sans-serif !important;
    }}

    {bg_css}

    .main .block-container {{
        padding: 2rem 2.5rem !important;
        max-width: 1400px !important;
    }}

    /* ── SIDEBAR (always navy) ── */
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
    }}
    [data-testid="stSidebarNav"] a:hover,
    [data-testid="stSidebarNav"] a[aria-selected="true"] {{
        background: rgba(245,166,35,0.2) !important;
        color: {accent} !important;
    }}
    [data-testid="stSidebar"] label,
    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] span,
    [data-testid="stSidebar"] div {{ color: #C8D8F0 !important; }}
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
        border-color: rgba(255,255,255,0.12) !important;
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] {{
        background: rgba(255,255,255,0.1) !important;
        border: 1px solid rgba(255,255,255,0.25) !important;
        border-radius: 10px !important;
        padding: 0.5rem 0.8rem !important;
    }}
    [data-testid="stSidebar"] [data-testid="stToggle"] p,
    [data-testid="stSidebar"] [data-testid="stToggle"] span,
    [data-testid="stSidebar"] [data-testid="stToggle"] label {{
        color: #FFFFFF !important;
        font-weight: 600 !important;
    }}

    /* ── HEADINGS ── */
    h1, h2, h3,
    [data-testid="stHeadingWithActionElements"] h1,
    [data-testid="stHeadingWithActionElements"] h2,
    [data-testid="stHeadingWithActionElements"] h3 {{
        color: {p["heading"]} !important;
    }}
    [data-testid="stHeadingWithActionElements"] h1 {{
        font-weight: 700 !important;
        font-size: 1.8rem !important;
        border-bottom: 3px solid {accent} !important;
        padding-bottom: 0.5rem !important;
    }}

    /* ── METRIC CARDS ── */
    [data-testid="stMetric"] {{
        background: {p["card"]} !important;
        border: 1px solid {p["border"]} !important;
        border-top: 3px solid {accent} !important;
        border-radius: 12px !important;
        padding: 1.1rem 1.3rem !important;
        box-shadow: 0 1px 6px rgba(0,0,0,0.08) !important;
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
    }}

    /* ── BUTTONS ── */
    .stButton > button {{
        background: linear-gradient(135deg, {navy}, {navy2}) !important;
        color: #FFFFFF !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
        padding: 0.5rem 1.4rem !important;
    }}
    .stButton > button:hover {{
        background: linear-gradient(135deg, {accent}, #E8941A) !important;
        color: {navy} !important;
    }}

    /* ── EXPANDER ── */
    [data-testid="stExpander"] {{
        background: {p["card"]} !important;
        border: 1px solid {p["border"]} !important;
        border-radius: 12px !important;
    }}
    [data-testid="stExpander"] summary span,
    [data-testid="stExpander"] p {{
        color: {p["text"]} !important;
    }}

    /* ── PLOTLY WRAPPER ── */
    [data-testid="stPlotlyChart"] > div {{
        border-radius: 14px !important;
        overflow: hidden !important;
        background: {p["chart_paper"]} !important;
        box-shadow: 0 1px 8px rgba(0,0,0,0.1) !important;
    }}

    /* ── DATAFRAME ── */
    [data-testid="stDataFrame"] {{
        border-radius: 12px !important;
        overflow: hidden !important;
    }}

    /* ── MULTISELECT TAGS ── */
    [data-baseweb="tag"] {{
        background-color: {navy2} !important;
        border-radius: 6px !important;
    }}
    [data-baseweb="tag"] span {{ color: #FFFFFF !important; }}

    /* ── SELECT / INPUT text ── */
    [data-baseweb="select"] div,
    [data-baseweb="input"] input {{
        color: {p["text"]} !important;
    }}

    /* ── CAPTION ── */
    [data-testid="stCaptionContainer"] p {{
        color: {p["text_muted"]} !important;
        font-size: 0.78rem !important;
    }}

    /* ── ALERT ── */
    [data-testid="stAlert"] {{
        border-radius: 10px !important;
    }}
    [data-testid="stAlert"] p {{
        color: inherit !important;
    }}

    .stSpinner > div {{ border-top-color: {navy2} !important; }}
    </style>
    """, unsafe_allow_html=True)

    return p


def get_template():
    return BKK_TEMPLATE
