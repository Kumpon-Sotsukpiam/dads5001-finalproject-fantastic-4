"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def ai_mode_toggle():
    """
    Render AI mode toggle at the TOP of the sidebar.
    Uses key='ai_mode' directly so it stays in sync with the Home page toggle.
    """
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = False

    st.sidebar.toggle(
        "🤖 AI Mode",
        key="ai_mode",   # same key as Home page — Streamlit syncs automatically
        help="Enable AI-powered insights on each page",
    )
    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
