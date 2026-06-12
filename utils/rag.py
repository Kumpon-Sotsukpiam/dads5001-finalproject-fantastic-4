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


@st.cache_data(ttl=3600, show_spinner=False)
def _dataset_overview():
    """
    Compact, accurate dataset-level statistics (computed by DuckDB over ALL
    records, cached 1 h). Prepended to every chatbot prompt so aggregate
    questions ("which district has the most X?") are answered from real
    counts — not inferred from the handful of retrieved documents.
    """
    from utils.queries import (
        get_district_summary, get_top_problem_types, get_resolution_stats,
    )
    try:
        ds = get_district_summary()
        tp = get_top_problem_types(10)
        rs = get_resolution_stats()
    except Exception:
        return ""

    parts = []
    if not ds.empty:
        total    = int(ds["total_tickets"].sum())
        finished = int(ds["finished"].sum())
        parts.append(
            "Overall: {:,} complaints, {:,} finished ({:.1f}%).".format(
                total, finished, finished / total * 100 if total else 0))
        top5 = ds.head(5)
        parts.append("Top 5 districts by volume: " + "; ".join(
            "{} ({:,.0f} tickets, {:.2f}/5 satisfaction)".format(
                r["district"], r["total_tickets"], r["avg_satisfaction"])
            for _, r in top5.iterrows()))
        worst = ds.dropna(subset=["avg_satisfaction"]).nsmallest(3, "avg_satisfaction")
        parts.append("Lowest satisfaction districts: " + "; ".join(
            "{} ({:.2f}/5)".format(r["district"], r["avg_satisfaction"])
            for _, r in worst.iterrows()))
    if not tp.empty:
        parts.append("Top 10 problem types by volume: " + "; ".join(
            "{} ({:,.0f})".format(r["problem_type"], r["total"])
            for _, r in tp.iterrows()))
    if not rs.empty:
        slow = rs.head(5)
        parts.append("Slowest problem types to resolve: " + "; ".join(
            "{} ({:,.0f} hrs avg)".format(r["problem_type"], r["avg_hours"])
            for _, r in slow.iterrows()))
    return "\n".join(parts)


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
    "You receive two kinds of context:\n"
    "  1. DATASET STATISTICS — accurate aggregates computed over ALL 168K records.\n"
    "     ALWAYS use these for questions about 'most', 'least', 'average', "
    "rankings, or totals.\n"
    "  2. RETRIEVED DOCUMENTS — a small sample of individual complaints.\n"
    "     Use these only as concrete examples or for details; NEVER count or "
    "rank from them.\n"
    "Be specific and data-driven — cite real numbers from the statistics.\n"
    "If neither source contains enough information, say so clearly.\n"
)


@st.cache_data(ttl=3600, show_spinner=False)
def ai_insight(context_text, prompt):
    """
    One-shot AI insight from structured context (no retrieval).
    Used by Dashboard, Map, Explorer, Snowflake pages.
    Cached: identical data + prompt returns instantly without re-calling the API.
    """
    client = get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": (
                "You are an urban analytics assistant for Bangkok Metropolitan Administration.\n"
                "Analyze the data summary provided and give concise, actionable insights.\n"
                "Answer in the same language as the user's prompt (Thai or English).\n"
                "Be specific — cite numbers, name districts or problem types.\n"
                "Format your answer EXACTLY as:\n"
                "1. One bold headline stating the single most important finding.\n"
                "2. Up to 4 short bullet points, each citing a specific number.\n"
                "3. One final line starting with 'Recommendation:' giving one concrete action."
            )},
            {"role": "user", "content": "DATA:\n{}\n\nTASK: {}".format(context_text, prompt)},
        ],
        temperature=0.3,
        max_tokens=512,
    )
    return response.choices[0].message.content


def ask_rag(question, chat_history):
    """Retrieve relevant complaints + dataset statistics -> call Groq."""
    docs     = text_search(question, TOP_K)
    context  = build_context(docs)
    overview = _dataset_overview()

    history_text = ""
    for turn in chat_history[-6:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        history_text += "{}: {}\n".format(role, turn["content"])

    user_message = (
        "DATASET STATISTICS (accurate, computed over all records):\n{}\n\n"
        "RETRIEVED DOCUMENTS (sample of individual complaints):\n{}\n\n"
        "CONVERSATION HISTORY:\n{}"
        "User: {}"
    ).format(overview if overview else "(unavailable)", context,
             history_text, question)

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
