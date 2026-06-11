"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def ai_mode_toggle():
    """
    Render AI mode toggle in the sidebar.

    The ONLY pattern that works reliably in Streamlit multi-page apps:
    - Use key="ai_mode" directly on the widget
    - Call st.session_state.setdefault("ai_mode", False) ONCE before widget
    - NEVER write to st.session_state["ai_mode"] manually anywhere else
    - Streamlit owns this key — it persists across page navigation automatically
    """
    st.session_state.setdefault("ai_mode", False)

    st.sidebar.toggle(
        "🤖 AI Mode",
        key="ai_mode",
        help="Enable AI-powered insights on each page",
    )
    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
