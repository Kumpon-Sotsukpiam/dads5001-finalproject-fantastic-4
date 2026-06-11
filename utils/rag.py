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
    Search MongoDB for relevant complaints.
    Strategy:
      1. Try MongoDB $text search (works for Thai via whitespace tokenizer)
      2. If empty result, fall back to regex on all meaningful fields
      3. If still empty, return random sample so LLM has some context
    """
    import re
    col = get_mongo_collection()
    projection = {
        "_id": 0, "ticket_id": 1, "problem_type": 1,
        "district": 1, "subdistrict": 1, "state_en": 1,
        "comment": 1, "duration_minutes_total": 1,
        "star": 1, "timestamp": 1,
    }

    # Step 1: MongoDB $text search
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

    # Step 2: Regex fallback — split query into tokens (handles Thai)
    # Thai words don't have spaces so search whole query + individual words
    tokens = [query.strip()] + [t for t in query.replace("?", "").split() if len(t) > 1]
    tokens = list(dict.fromkeys(tokens))  # deduplicate, preserve order
    pattern = "|".join(re.escape(t) for t in tokens[:5])

    if pattern:
        fallback_filter = {
            "$or": [
                {"comment":      {"$regex": pattern, "$options": "i"}},
                {"problem_type": {"$regex": pattern, "$options": "i"}},
                {"district":     {"$regex": pattern, "$options": "i"}},
                {"subdistrict":  {"$regex": pattern, "$options": "i"}},
            ]
        }
        results = list(col.find(fallback_filter, projection, limit=top_k))
        if results:
            return results

    # Step 3: Return a random sample so LLM can still answer general questions
    results = list(col.find({}, projection, limit=top_k))
    return [dict(d, score=0.0) for d in results]


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
