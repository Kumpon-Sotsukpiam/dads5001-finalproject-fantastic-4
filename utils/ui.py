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

    Pattern: use st.sidebar.checkbox (not toggle) with explicit value= and
    write result directly back to ai_mode — no widget key needed.
    """
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = False

    new_val = st.sidebar.checkbox(
        "🤖 AI Mode",
        value=st.session_state["ai_mode"],
        help="Enable AI-powered insights on each page",
    )
    # Write back every render — this is safe because checkbox has no key
    st.session_state["ai_mode"] = new_val

    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
