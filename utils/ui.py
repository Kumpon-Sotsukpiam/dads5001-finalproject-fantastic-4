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

    Correct Streamlit pattern:
    - 'ai_mode' is the canonical session_state key (bool)
    - '_ai_toggle' is the widget key (separate, never written directly)
    - Before render: copy ai_mode → _ai_toggle so widget shows correct value
    - on_change: copy _ai_toggle → ai_mode
    - The pre-seed line MUST come before st.sidebar.toggle()
    """
    # 1. Initialize canonical key
    if "ai_mode" not in st.session_state:
        st.session_state["ai_mode"] = False

    # 2. Pre-seed widget key every page load so toggle shows current value
    #    This is safe to do BEFORE the widget is rendered (not after)
    if "_ai_toggle" not in st.session_state:
        st.session_state["_ai_toggle"] = st.session_state["ai_mode"]
    else:
        # Sync widget → canonical on every page navigation
        # (widget key persists in session but canonical may have been changed)
        st.session_state["_ai_toggle"] = st.session_state["ai_mode"]

    # 3. on_change: user flipped the toggle → update canonical key
    def _sync():
        st.session_state["ai_mode"] = st.session_state["_ai_toggle"]

    # 4. Render toggle — NO value= param, widget reads from session_state["_ai_toggle"]
    st.sidebar.toggle(
        "🤖 AI Mode",
        key="_ai_toggle",
        on_change=_sync,
        help="Enable AI-powered insights on each page",
    )

    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
