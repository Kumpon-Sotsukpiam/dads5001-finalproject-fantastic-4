"""
app.py  –  Entrypoint (defines navigation, keeps deploy config stable)
Bangkok Complaints Analytics  (Traffy Fondue, Jul–Dec 2025)

The main file stays `app.py` so Streamlit Cloud deployments never break.
Page labels/icons are set explicitly via st.navigation — this is also
what makes the sidebar show "Home" instead of the filename.

Run:
    streamlit run app.py
"""

import streamlit as st

pages = [
    st.Page("home.py",                            title="Home",                icon="🏠", default=True),
    st.Page("pages/2_📊_Dashboard.py",            title="Dashboard",           icon="📊"),
    st.Page("pages/3_🗺️_Map.py",                  title="Map",                 icon="🗺️"),
    st.Page("pages/4_🔍_Explorer.py",             title="Explorer",            icon="🔍"),
    st.Page("pages/5_❄️_Snowflake_Analytics.py",  title="Snowflake Analytics", icon="❄️"),
    st.Page("pages/6_🤖_AI_Assistant.py",         title="AI Assistant",        icon="🤖"),
]

st.navigation(pages).run()
