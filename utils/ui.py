"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def ai_mode_toggle():
    """
    Render AI mode toggle in the sidebar.
    Persists across page navigation.

    The only reliable pattern in Streamlit:
    - Use a FIXED key ("ai_mode") directly as the widget key
    - Never manually assign st.session_state["ai_mode"] after widget is rendered
    - Initialize with setdefault BEFORE the widget is ever created
    """
    # setdefault only sets if key doesn't exist — safe to call every page load
    st.session_state.setdefault("ai_mode", False)

    st.sidebar.toggle(
        "🤖 AI Mode",
        key="ai_mode",          # widget IS the state — same key, same value
        help="Enable AI-powered insights on each page",
    )
    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
