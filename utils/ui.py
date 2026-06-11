"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def ai_mode_toggle():
    """
    Render AI mode toggle in the sidebar.
    Call this at the top of every page's sidebar block.
    Returns current ai_mode value (bool).
    """
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = False

    with st.sidebar:
        st.divider()
        mode = st.toggle(
            "🤖 AI Mode",
            value=st.session_state["ai_mode"],
            key="ai_mode_toggle",
            help="Enable AI-powered insights on each page",
        )
        st.session_state["ai_mode"] = mode
        if mode:
            st.caption("✅ AI mode ON")
        else:
            st.caption("AI mode OFF")
        st.divider()

    return mode
