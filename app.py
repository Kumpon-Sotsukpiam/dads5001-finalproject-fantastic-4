"""
app.py  –  Home / Landing page
Bangkok Complaints Analytics  (Traffy Fondue, Jul–Dec 2025)

Run:
    streamlit run app.py
"""

import streamlit as st

st.set_page_config(
    page_title="Bangkok Complaints Analytics",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Session state defaults ────────────────────────────────────────────────────
if "ai_mode" not in st.session_state:
    st.session_state["ai_mode"] = False
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ── Page ──────────────────────────────────────────────────────────────────────
st.title("🏙️ Bangkok Complaints Analytics")
st.subheader("Traffy Fondue Dataset · July – December 2025")

st.markdown("""
This application analyses **168,000+ public complaints** reported to Bangkok Metropolitan Administration
via [Traffy Fondue](https://traffy.in.th/) in the second half of 2025.

**Data pipeline:**
```
CSV files (Jul–Dec 2025)
  → Pandas + DuckDB  (clean & transform)
  → MongoDB Atlas    (raw storage + vector embeddings)
  → Snowflake        (analytics warehouse)
  → Streamlit + Plotly (this app)
```

**Navigate using the sidebar** to explore:
| Page | Description |
|------|-------------|
| 📊 Dashboard | KPIs, trends, and district breakdowns (MongoDB + DuckDB) |
| 🗺️ Map | Geographic distribution of complaints |
| 🔍 Explorer | Filter and inspect raw records |
| ❄️ Snowflake Analytics | Pre-aggregated analytics from Snowflake warehouse |
| 🤖 AI Assistant | RAG-powered Q&A about Bangkok complaints |
""")

col1, col2, col3 = st.columns(3)
col1.metric("Total Tickets (Jul–Dec)", "168,589")
col2.metric("Districts Covered", "50")
col3.metric("Completion Rate", "66.2%")

st.divider()

mode = st.toggle("🤖 Enable AI Mode (RAG Assistant)", value=st.session_state["ai_mode"])
st.session_state["ai_mode"] = mode
if mode:
    st.success("AI mode ON — navigate to **🤖 AI Assistant** in the sidebar.")
else:
    st.info("AI mode OFF — all pages show analytics without LLM calls.")
