"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def ai_mode_toggle():
    """
    Render AI mode toggle at the TOP of the sidebar.
    Call this BEFORE any 'with st.sidebar:' block in each page.
    Returns current ai_mode value (bool).
    """
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = False

    # Use st.sidebar directly (not 'with') so it renders before other sidebar content
    mode = st.sidebar.toggle(
        "🤖 AI Mode",
        value=st.session_state["ai_mode"],
        key="ai_mode_toggle",
        help="Enable AI-powered insights on each page",
    )
    st.session_state["ai_mode"] = mode
    if mode:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()

    return mode
