"""
pages/4_AI_Assistant.py
-----------------------
RAG-powered chatbot using MongoDB Text Search + Google Gemini 1.5 Flash.
Requires AI mode to be enabled (set on the Home page).
"""

import streamlit as st
from utils.rag import ask_rag

st.set_page_config(page_title="AI Assistant", page_icon="🤖", layout="wide")
st.title("🤖 AI Assistant (RAG Mode)")
st.caption("MongoDB Text Search + Groq llama-3.1-8b · Data: Traffy Fondue Jul-Dec 2025")

# ── Guard: AI mode must be ON ─────────────────────────────────────────────────
if not st.session_state.get("ai_mode", False):
    st.warning("AI mode is currently **OFF**. Enable it on the 🏠 Home page.")
    if st.button("Enable AI Mode now"):
        st.session_state["ai_mode"] = True
        st.rerun()
    st.stop()

# ── Session state ─────────────────────────────────────────────────────────────
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []

# ── Sidebar: example questions ────────────────────────────────────────────────
with st.sidebar:
    st.header("💡 Example Questions")
    examples = [
        "Which district has the most traffic violation complaints?",
        "What problem types take the longest to resolve?",
        "Which areas have the most flooding complaints?",
        "What is the average resolution time for electrical issues?",
        "เขตไหนมีปัญหาเรื่องเสียงดังมากที่สุด?",
        "ปัญหาประเภทใดได้รับคะแนนความพึงพอใจสูงสุด?",
    ]
    for ex in examples:
        if st.button(ex, key="ex_{}".format(ex[:20]), use_container_width=True):
            st.session_state["pending_question"] = ex

    st.divider()
    if st.button("🗑️ Clear chat history", use_container_width=True):
        st.session_state["chat_history"] = []
        st.rerun()

# ── Display chat history ──────────────────────────────────────────────────────
for msg in st.session_state["chat_history"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg["role"] == "assistant" and msg.get("sources"):
            with st.expander("📄 Retrieved documents"):
                for s in msg["sources"]:
                    st.markdown(
                        "**[{}]** {} · {}  \n_{}_".format(
                            s.get("ticket_id", ""),
                            s.get("problem_type", ""),
                            s.get("district", ""),
                            str(s.get("comment", ""))[:200],
                        )
                    )

# ── Handle pre-filled question from sidebar ───────────────────────────────────
prefill = st.session_state.pop("pending_question", None)

# ── Chat input ────────────────────────────────────────────────────────────────
user_input = st.chat_input("Ask about Bangkok complaints ...") or prefill

if user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)

    with st.chat_message("assistant"):
        with st.spinner("Searching complaints and generating answer ..."):
            try:
                answer, docs = ask_rag(
                    user_input,
                    st.session_state["chat_history"][:-1],
                )
            except Exception as e:
                answer = "⚠️ Error: {}".format(e)
                docs   = []

        st.markdown(answer)

        if docs:
            with st.expander("📄 Retrieved documents"):
                for s in docs:
                    st.markdown(
                        "**[{}]** {} · {}  \n_{}_".format(
                            s.get("ticket_id", ""),
                            s.get("problem_type", ""),
                            s.get("district", ""),
                            str(s.get("comment", ""))[:200],
                        )
                    )

    st.session_state["chat_history"].append({
        "role":    "assistant",
        "content": answer,
        "sources": docs,
    })
