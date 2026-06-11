"""
utils/rag.py
------------
RAG (Retrieval-Augmented Generation) helpers.

  1. MongoDB text search to retrieve relevant complaints
  2. Build context string from top-K retrieved documents
  3. Call Groq (llama-3.1-8b-instant) with context + user question
"""

import os
import streamlit as st
from groq import Groq
from utils.db import get_mongo_collection, _get_secret
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "llama-3.1-8b-instant"
TOP_K      = 8


@st.cache_resource(show_spinner="Connecting to Groq ...")
def get_groq_client():
    api_key = _get_secret("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not set in secrets or .env")
        st.stop()
    return Groq(api_key=api_key)


def text_search(query, top_k=TOP_K):
    """
    MongoDB text search on comment + problem_type + district fields.
    Falls back to a simple regex search if text index not available.
    """
    col = get_mongo_collection()
    projection = {
        "_id": 0, "ticket_id": 1, "problem_type": 1,
        "district": 1, "subdistrict": 1, "state_en": 1,
        "comment": 1, "duration_minutes_total": 1,
        "star": 1, "timestamp": 1,
    }

    try:
        cursor = col.find(
            {"$text": {"$search": query}},
            {**projection, "score": {"$meta": "textScore"}},
            limit=top_k,
        ).sort([("score", {"$meta": "textScore"})])
        results = list(cursor)
        if results:
            return results
    except Exception:
        pass

    # Fallback: regex search
    keywords = query.replace("?", "").split()[:3]
    fallback_filter = {}
    if keywords:
        import re
        pattern = "|".join(re.escape(k) for k in keywords)
        fallback_filter = {
            "$or": [
                {"comment":      {"$regex": pattern, "$options": "i"}},
                {"problem_type": {"$regex": pattern, "$options": "i"}},
                {"district":     {"$regex": pattern, "$options": "i"}},
            ]
        }
    cursor = col.find(fallback_filter, projection, limit=top_k)
    return [dict(d, score=0.0) for d in cursor]


def build_context(docs):
    if not docs:
        return "No relevant documents found."
    lines = []
    for i, d in enumerate(docs, 1):
        lines.append(
            "[{}] Ticket: {} | Type: {} | District: {} | "
            "Status: {} | Stars: {} | Duration: {} min | "
            "Comment: {}".format(
                i,
                d.get("ticket_id", ""),
                d.get("problem_type", ""),
                d.get("district", ""),
                d.get("state_en", ""),
                d.get("star", ""),
                d.get("duration_minutes_total", ""),
                str(d.get("comment", ""))[:300],
            )
        )
    return "\n".join(lines)


SYSTEM_PROMPT = (
    "You are an urban analytics assistant for Bangkok Metropolitan Administration.\n"
    "You help analyze public complaints submitted via Traffy Fondue (Jul-Dec 2025).\n"
    "Answer in English or Thai based on the user's language.\n"
    "Base your answers on the CONTEXT provided. Be specific and data-driven.\n"
    "If the context does not contain enough information, say so clearly.\n"
)


def ask_rag(question, chat_history):
    """Retrieve relevant complaints -> build context -> call Groq."""
    docs    = text_search(question, TOP_K)
    context = build_context(docs)

    history_text = ""
    for turn in chat_history[-6:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        history_text += "{}: {}\n".format(role, turn["content"])

    user_message = (
        "CONTEXT (retrieved from Bangkok complaints database):\n{}\n\n"
        "CONVERSATION HISTORY:\n{}"
        "User: {}"
    ).format(context, history_text, question)

    client = get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1024,
    )
    return response.choices[0].message.content, docs
