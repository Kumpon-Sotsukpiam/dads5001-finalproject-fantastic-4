"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def _sync_ai_mode():
    """Copy widget value into the persistent (non-widget) session key."""
    st.session_state["ai_mode"] = st.session_state["_ai_mode_widget"]


def ai_mode_toggle():
    """
    Render the AI mode toggle in the sidebar.

    Why this pattern:
    Streamlit deletes widget-owned session keys when the widget is not
    rendered on a rerun, so binding the widget directly to key="ai_mode"
    loses the value on every page change. Instead we:
      1. Keep the real state in a persistent key ("ai_mode") that no
         widget owns.
      2. Give the widget its own throwaway key ("_ai_mode_widget"),
         seed it with value=st.session_state["ai_mode"], and sync back
         via on_change.
      3. Call this function on EVERY page so the toggle is always
         visible and the state survives navigation.
    """
    st.session_state.setdefault("ai_mode", False)

    st.sidebar.toggle(
        "🤖 AI Mode",
        value=st.session_state["ai_mode"],
        key="_ai_mode_widget",
        on_change=_sync_ai_mode,
        help="Enable AI-powered insights on each page",
    )
    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
