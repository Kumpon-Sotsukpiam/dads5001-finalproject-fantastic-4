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
    # Initialize persistent state key
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = False

    # Force-sync widget key to match persistent state BEFORE rendering
    # This is the key fix: Streamlit reads widget key at render time,
    # so we must pre-populate it with the correct value every page load.
    st.session_state["_sidebar_ai_toggle"] = st.session_state["ai_mode"]

    def _on_change():
        st.session_state["ai_mode"] = st.session_state["_sidebar_ai_toggle"]

    st.sidebar.toggle(
        "🤖 AI Mode",
        key="_sidebar_ai_toggle",
        on_change=_on_change,
        help="Enable AI-powered insights on each page",
    )
    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
