"""
app.py  –  Home / Landing page
Bangkok Complaints Analytics  (Traffy Fondue, Jul–Dec 2025)

Run:
    streamlit run app.py
"""

import streamlit as st
from utils.theme import inject_css
from utils.ui import ai_mode_toggle

st.set_page_config(
    page_title="Bangkok Complaints Analytics",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

inject_css()

# ── Session state defaults ────────────────────────────────────────────────────
if "ai_mode" not in st.session_state:
    st.session_state["ai_mode"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

ai_mode_toggle()

# ── Hero section ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="
    background: linear-gradient(135deg, #1B3A6B 0%, #2E6CB8 100%);
    border-radius: 16px;
    padding: 2.5rem 3rem;
    margin-bottom: 1.5rem;
    box-shadow: 0 4px 20px rgba(27,58,107,0.2);
">
    <div style="color:#FFFFFF; font-size:2.2rem; font-weight:800; line-height:1.2; margin-bottom:0.5rem;">
        🏙️ Bangkok Complaints Analytics
    </div>
    <div style="color:#B0D0F0; font-size:1.05rem;">
        Traffy Fondue Dataset &nbsp;·&nbsp; July – December 2025 &nbsp;·&nbsp; 168,589 complaints
    </div>
</div>
""", unsafe_allow_html=True)

# ── KPI cards ─────────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)
c1.metric("🎫 Total Tickets",     "168,589")
c2.metric("🏘️ Districts Covered", "50")
c3.metric("✅ Completion Rate",   "66.2%")
c4.metric("⭐ Avg Satisfaction",  "3.8 / 5")

st.divider()

# ── Story flow ────────────────────────────────────────────────────────────────
st.subheader("📖 How to explore this app")

cols = st.columns(5)
pages = [
    ("📊", "Dashboard",          "Start here — KPIs, monthly trends, and district overview"),
    ("🗺️", "Map",                "See where complaints are concentrated geographically"),
    ("🔍", "Explorer",           "Filter and drill into raw complaint records"),
    ("❄️", "Snowflake Analytics","Deep-dive performance: resolution time, reopen rates, scorecard"),
    ("🤖", "AI Assistant",       "Ask questions about Bangkok complaints in natural language"),
]
for col, (icon, title, desc) in zip(cols, pages):
    col.markdown(f"""
    <div style="
        background:#FFFFFF;
        border:1px solid #D6E4F0;
        border-top:4px solid #F5A623;
        border-radius:10px;
        padding:1rem;
        text-align:center;
        height:160px;
        box-shadow:0 2px 8px rgba(27,58,107,0.06);
    ">
        <div style="font-size:2rem;">{icon}</div>
        <div style="font-weight:700;color:#1B3A6B;margin:0.3rem 0 0.4rem;">{title}</div>
        <div style="font-size:0.78rem;color:#7F8C8D;line-height:1.4;">{desc}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Data pipeline ─────────────────────────────────────────────────────────────
st.subheader("⚙️ Data Pipeline")
st.markdown("""
<div style="background:#FFFFFF;border:1px solid #D6E4F0;border-radius:12px;padding:1.2rem 2rem;">
<code style="color:#1B3A6B;font-size:0.9rem;">
CSV files (Jul–Dec 2025) &nbsp;→&nbsp; Pandas + DuckDB &nbsp;→&nbsp; MongoDB Atlas &nbsp;→&nbsp; Snowflake &nbsp;→&nbsp; Streamlit + Plotly
</code>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── AI mode toggle ────────────────────────────────────────────────────────────
st.subheader("🤖 AI Mode")
st.markdown("""
<div style="
    background:#FFFFFF;
    border:1px solid #D6E4F0;
    border-radius:12px;
    padding:1.2rem 1.5rem;
    box-shadow:0 2px 8px rgba(27,58,107,0.06);
    margin-bottom:0.5rem;
">
""", unsafe_allow_html=True)
def _sync_ai_mode():
    st.session_state["ai_mode"] = st.session_state["_home_ai_toggle"]

st.toggle(
    "Enable AI Mode",
    value=st.session_state.get("ai_mode", False),
    key="_home_ai_toggle",
    on_change=_sync_ai_mode,
)
if st.session_state.get("ai_mode", False):
    st.success("AI mode **ON** — AI insight buttons are now active on every page.")
else:
    st.info("AI mode **OFF** — analytics-only. Toggle ON to unlock AI insights on each page.")
st.markdown("</div>", unsafe_allow_html=True)
