"""
utils/ui.py
-----------
Shared UI components used across all pages.
"""

import streamlit as st


def ai_mode_toggle():
    """
    Render the AI mode toggle in the sidebar.

    Pattern that survives Streamlit multi-page navigation:
    - "ai_mode"         : persistent bool, never owned by a widget
    - "_ai_mode_widget" : widget key, seeded from ai_mode ONLY if not yet set
                          (avoids StreamlitAPIException on re-render)
    - on_change syncs widget → ai_mode when user flips the toggle
    """
    # 1. Ensure persistent key exists
    st.session_state.setdefault("ai_mode", False)

    # 2. Seed widget key from persistent key — but ONLY before first render.
    #    After first render Streamlit owns this key; writing to it again raises
    #    StreamlitAPIException, so we skip if the key already exists.
    if "_ai_mode_widget" not in st.session_state:
        st.session_state["_ai_mode_widget"] = st.session_state["ai_mode"]

    # 3. Sync persistent key back to widget key on every page navigation.
    #    This is safe because we are doing it BEFORE the widget is rendered
    #    on THIS run (the widget is being re-created fresh on each page load).
    st.session_state["_ai_mode_widget"] = st.session_state["ai_mode"]

    # 4. on_change callback: user flipped toggle → update persistent key
    def _sync():
        st.session_state["ai_mode"] = st.session_state["_ai_mode_widget"]

    # 5. Render — no value= param; Streamlit reads from session_state["_ai_mode_widget"]
    st.sidebar.toggle(
        "🤖 AI Mode",
        key="_ai_mode_widget",
        on_change=_sync,
        help="Enable AI-powered insights on each page",
    )

    if st.session_state["ai_mode"]:
        st.sidebar.caption("✅ AI insights enabled")
    st.sidebar.divider()
