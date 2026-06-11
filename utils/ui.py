"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def ai_mode_toggle():
    """
    Render AI mode toggle in the sidebar.
    Persists state across page navigation via session_state.
    """
    # Always initialize before any widget touches the key
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = False

    def _on_change():
        # Explicitly persist the value so it survives page changes
        st.session_state["ai_mode"] = st.session_state["_sidebar_ai_toggle"]

    st.sidebar.toggle(
        "🤖 AI Mode",
        value=st.session_state["ai_mode"],  # always restore last known value
        key="_sidebar_ai_toggle",
        on_change=_on_change,
        help="Enable AI-powered insights on each page",
    )
    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
