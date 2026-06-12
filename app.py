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

p = inject_css()  # returns active colour palette

# ── Session state defaults ────────────────────────────────────────────────────
# ai_mode is managed by ai_mode_toggle() (persistent key + widget-key sync)
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

# ── Issues & Motivation / Objective ──────────────────────────────────────────
col_m, col_o = st.columns(2)

with col_m:
    st.subheader("🚨 Issues & Motivation")
    st.markdown(f"""
    <div style="background:{p['card']};border:1px solid {p['border']};
                border-left:4px solid #E74C3C;border-radius:10px;
                padding:1rem 1.3rem;height:230px;">
    <div style="color:{p['text']};font-size:0.88rem;line-height:1.7;">
    Bangkok citizens file <b>thousands of complaints daily</b> via Traffy Fondue —
    flooding, broken roads, noise, waste, and more. With 168,589 tickets across
    50 districts in just six months, BMA faces three challenges:
    <br>• <b>Where</b> are problems concentrated, and which districts underperform?
    <br>• <b>Which</b> problem types are slow to resolve or keep reopening?
    <br>• <b>How</b> can non-technical staff query this data without writing SQL?
    </div></div>
    """, unsafe_allow_html=True)

with col_o:
    st.subheader("🎯 Objective")
    st.markdown(f"""
    <div style="background:{p['card']};border:1px solid {p['border']};
                border-left:4px solid #27AE60;border-radius:10px;
                padding:1rem 1.3rem;height:230px;">
    <div style="color:{p['text']};font-size:0.88rem;line-height:1.7;">
    Build a <b>data-centric analytics app with an AI add-on</b> that helps
    BMA prioritize public service delivery:
    <br>• <b>Non-AI mode</b> — interactive dashboards, maps, and a raw-data
    explorer powered by Pandas + DuckDB over MongoDB and Snowflake
    <br>• <b>AI mode</b> — one-click AI insights on every page and a RAG
    chatbot that answers questions in Thai or English
    <br>• Deliver insights that turn 168K complaints into <b>actionable priorities</b>
    </div></div>
    """, unsafe_allow_html=True)

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
        background: {p['card']};
        border: 1px solid {p['border']};
        border-top: 4px solid #F5A623;
        border-radius: 10px;
        padding: 1rem;
        text-align: center;
        height: 160px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.07);
    ">
        <div style="font-size:2rem;">{icon}</div>
        <div style="font-weight:700; color:{p['heading']}; margin:0.3rem 0 0.4rem;">{title}</div>
        <div style="font-size:0.78rem; color:{p['text_muted']}; line-height:1.4;">{desc}</div>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ── Data pipeline ─────────────────────────────────────────────────────────────
st.subheader("⚙️ Data Pipeline")
st.markdown(f"""
<div style="background:{p['card']};border:1px solid {p['border']};border-radius:12px;padding:1.2rem 2rem;">
<span style="color:{p['text']};font-size:0.9rem;font-family:'Inter',sans-serif;font-weight:500;">
CSV files (Jul–Dec 2025) &nbsp;→&nbsp; Pandas + DuckDB &nbsp;→&nbsp; MongoDB Atlas &nbsp;→&nbsp; Snowflake &nbsp;→&nbsp; Streamlit + Plotly
</span>
</div>
""", unsafe_allow_html=True)

st.divider()

# ── AI mode status ────────────────────────────────────────────────────────────
st.subheader("🤖 AI Mode")
if st.session_state.get("ai_mode", False):
    st.success("AI mode **ON** — AI insight buttons are now active on every page.")
else:
    st.info("AI mode **OFF** — use the toggle in the sidebar to enable AI insights.")
