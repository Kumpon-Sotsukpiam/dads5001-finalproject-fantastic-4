"""
utils/rag.py
------------
RAG (Retrieval-Augmented Generation) helpers.

  1. Query expansion  — LLM rewrites the user question into multiple search
                        terms that capture semantic intent, not just keywords
  2. Multi-term retrieval — run $text search + regex for each expanded term,
                            merge and deduplicate results
  3. Dataset statistics   — accurate aggregates prepended for aggregate questions
  4. Context-aware generation — system prompt understands intent types
                                (aggregate / example / explanation / comparison)
"""

import os
import re
import streamlit as st
from groq import Groq
from utils.db import get_mongo_collection, _get_secret
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL = "llama-3.1-8b-instant"
TOP_K      = 10   # slightly more docs after dedup


# ── Groq client ───────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Connecting to Groq ...")
def get_groq_client():
    api_key = _get_secret("GROQ_API_KEY")
    if not api_key:
        st.error("GROQ_API_KEY not set in secrets or .env")
        st.stop()
    return Groq(api_key=api_key)


# ── Query expansion ───────────────────────────────────────────────────────────

def _expand_query(question: str, chat_history: list) -> list[str]:
    """
    Use the LLM to rewrite the user question into 3-5 search terms that capture
    its semantic intent.  This bridges vocabulary gaps: "น้ำรั่ว" → ["ประปา",
    "น้ำท่วม", "ท่อแตก"], "traffic" → ["จราจร", "รถติด", "ถนน"].

    Returns a deduplicated list: [original_question, *expanded_terms].
    Falls back to [original_question] if the LLM call fails.
    """
    # Summarise recent turns so the LLM has conversational context
    recent = ""
    for turn in chat_history[-4:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        recent += f"{role}: {turn['content'][:200]}\n"

    prompt = (
        "You are a search query optimizer for a Bangkok complaint database.\n"
        "Given the conversation history and the user's latest question, "
        "generate 3-5 short search terms (Thai or English) that would retrieve "
        "the most relevant complaint records from MongoDB.\n\n"
        "Rules:\n"
        "- Include synonyms, related Thai words, and relevant district/problem-type names.\n"
        "- Each term should be 1-4 words only.\n"
        "- Output ONLY a JSON array of strings, nothing else.\n"
        "  Example: [\"น้ำท่วม\", \"น้ำรั่ว\", \"ท่อแตก\", \"flooding\"]\n\n"
        f"Conversation history:\n{recent}\n"
        f"Latest question: {question}"
    )

    try:
        client = get_groq_client()
        resp = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=120,
        )
        raw = resp.choices[0].message.content.strip()
        # Extract JSON array from response (LLM sometimes adds prose)
        m = re.search(r'\[.*?\]', raw, re.DOTALL)
        if m:
            import json
            terms = json.loads(m.group())
            if isinstance(terms, list) and terms:
                # Always include original question; deduplicate
                all_terms = list(dict.fromkeys([question] + [str(t) for t in terms]))
                return all_terms
    except Exception:
        pass

    return [question]


# ── Retrieval ─────────────────────────────────────────────────────────────────

def _search_one(query: str, col, projection: dict, limit: int) -> list:
    """Run $text search then regex fallback for a single query string."""
    # 1. MongoDB $text search
    try:
        cursor = col.find(
            {"$text": {"$search": query}},
            {**projection, "score": {"$meta": "textScore"}},
            limit=limit,
        ).sort([("score", {"$meta": "textScore"})])
        results = list(cursor)
        if results:
            return results
    except Exception:
        pass

    # 2. Regex fallback — whole query + individual tokens
    tokens = [query.strip()] + [t for t in query.replace("?", "").split() if len(t) > 1]
    tokens = list(dict.fromkeys(tokens))
    pattern = "|".join(re.escape(t) for t in tokens[:6])
    if pattern:
        try:
            results = list(col.find(
                {"$or": [
                    {"comment":      {"$regex": pattern, "$options": "i"}},
                    {"problem_type": {"$regex": pattern, "$options": "i"}},
                    {"district":     {"$regex": pattern, "$options": "i"}},
                    {"subdistrict":  {"$regex": pattern, "$options": "i"}},
                ]},
                projection,
                limit=limit,
            ))
            if results:
                return results
        except Exception:
            pass

    return []


def text_search(question: str, chat_history: list = None, top_k: int = TOP_K) -> list:
    """
    Context-aware retrieval:
      1. Expand question into multiple search terms via LLM
      2. Retrieve for each term, merge, deduplicate by ticket_id
      3. Return top_k most relevant unique documents
    """
    chat_history = chat_history or []
    col = get_mongo_collection()
    projection = {
        "_id": 0, "ticket_id": 1, "problem_type": 1,
        "district": 1, "subdistrict": 1, "state_en": 1,
        "comment": 1, "duration_minutes_total": 1,
        "star": 1, "timestamp": 1,
    }

    expanded = _expand_query(question, chat_history)

    seen_ids = set()
    merged   = []

    for term in expanded:
        results = _search_one(term, col, projection, limit=top_k)
        for doc in results:
            tid = doc.get("ticket_id")
            if tid not in seen_ids:
                seen_ids.add(tid)
                merged.append(doc)
        if len(merged) >= top_k:
            break

    return merged[:top_k]


# ── Dataset statistics ────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def _dataset_overview() -> str:
    """
    Accurate aggregates over ALL 168K records, cached 1 h.
    Used for aggregate questions: rankings, totals, averages.
    """
    from utils.queries import (
        get_district_summary, get_top_problem_types, get_resolution_stats,
    )
    try:
        ds = get_district_summary()
        tp = get_top_problem_types(15)
        rs = get_resolution_stats()
    except Exception:
        return ""

    parts = []
    if not ds.empty:
        total    = int(ds["total_tickets"].sum())
        finished = int(ds["finished"].sum())
        parts.append(
            "Overall: {:,} complaints, {:,} finished ({:.1f}%), period Jul-Dec 2025.".format(
                total, finished, finished / total * 100 if total else 0))
        top10 = ds.head(10)
        parts.append("Top 10 districts by complaint volume: " + "; ".join(
            "{} ({:,.0f} tickets, sat {:.2f}/5)".format(
                r["district"], r["total_tickets"], r["avg_satisfaction"])
            for _, r in top10.iterrows()))
        worst = ds.dropna(subset=["avg_satisfaction"]).nsmallest(5, "avg_satisfaction")
        parts.append("Bottom 5 districts by satisfaction: " + "; ".join(
            "{} ({:.2f}/5)".format(r["district"], r["avg_satisfaction"])
            for _, r in worst.iterrows()))
        best = ds.dropna(subset=["avg_satisfaction"]).nlargest(5, "avg_satisfaction")
        parts.append("Top 5 districts by satisfaction: " + "; ".join(
            "{} ({:.2f}/5)".format(r["district"], r["avg_satisfaction"])
            for _, r in best.iterrows()))
    if not tp.empty:
        parts.append("Top 15 problem types by volume: " + "; ".join(
            "{} ({:,.0f})".format(r["problem_type"], r["total"])
            for _, r in tp.iterrows()))
    if not rs.empty:
        parts.append("Slowest problem types to resolve (avg hours): " + "; ".join(
            "{} ({:.0f} hrs)".format(r["problem_type"], r["avg_hours"])
            for _, r in rs.head(10).iterrows()))
    return "\n".join(parts)


# ── Context builder ───────────────────────────────────────────────────────────

def build_context(docs: list) -> str:
    if not docs:
        return "No relevant complaint records found for this query."
    lines = []
    for i, d in enumerate(docs, 1):
        dur_min = d.get("duration_minutes_total")
        dur_str = "{:.0f} min".format(float(dur_min)) if dur_min else "N/A"
        lines.append(
            "[Doc {i}] ID:{tid} | Type: {pt} | District: {dist} | "
            "Status: {st} | Rating: {star}/5 | Duration: {dur} | "
            "Comment: {cmt}".format(
                i=i,
                tid=d.get("ticket_id", ""),
                pt=d.get("problem_type", ""),
                dist=d.get("district", ""),
                st=d.get("state_en", ""),
                star=d.get("star", "N/A"),
                dur=dur_str,
                cmt=str(d.get("comment", ""))[:350],
            )
        )
    return "\n".join(lines)


# ── System prompt ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are an intelligent urban analytics assistant for Bangkok Metropolitan Administration (BMA).
You help users understand public complaints submitted via Traffy Fondue (July–December 2025).

CONTEXT YOU RECEIVE
───────────────────
1. DATASET STATISTICS  — precise aggregates computed over ALL 168,589 records.
   Use for: rankings, totals, averages, comparisons across districts or problem types.

2. RETRIEVED DOCUMENTS — a small sample of individual complaint records relevant to the query.
   Use for: specific examples, citizen comments, individual case details.
   NEVER use these to count, rank, or compute percentages — the sample is too small.

3. CONVERSATION HISTORY — prior turns in this session.
   Use for: resolving pronouns ("it", "that district", "the same problem"), follow-up questions,
   and maintaining continuity. If the user asks "what about Watthana?" after asking about flooding,
   they mean flooding in Watthana.

HOW TO UNDERSTAND QUESTIONS
────────────────────────────
Identify the question intent before answering:

• AGGREGATE  — "which district has the most…", "what is the average…", "how many…"
  → Answer from DATASET STATISTICS only. Cite exact numbers.

• EXAMPLE    — "show me a complaint about…", "give an example of…", "what do people say about…"
  → Answer from RETRIEVED DOCUMENTS. Quote the comment field directly.

• EXPLANATION — "why is…", "what causes…", "how does…"
  → Combine statistics with document examples. Reason explicitly.

• COMPARISON  — "compare X and Y", "which is worse…", "difference between…"
  → Pull both sides from statistics. Structure the answer as a side-by-side.

• FOLLOW-UP   — "what about…", "and for…", "same question but for…"
  → Carry the topic/filter from the previous turn. Do not ask for clarification
    if context makes the intent clear.

LANGUAGE
─────────
- Reply in the same language as the user's latest message (Thai or English).
- If the user mixes languages, match the dominant one.

GROUNDING RULES
───────────────
- Every number, district name, and problem type you state MUST appear in the provided context.
- Do NOT add facts from outside knowledge or training data.
- If neither STATISTICS nor DOCUMENTS contain enough information, say so honestly:
  Thai:    "ขออภัยครับ ข้อมูลในชุดข้อมูล Traffy Fondue (ก.ค.–ธ.ค. 2568) ไม่มีรายละเอียดในส่วนนี้"
  English: "I don't have enough data in the Traffy Fondue dataset (Jul–Dec 2025) to answer this precisely."
- Do NOT refuse to answer just because the question is broad — do your best with available data.
- Questions unrelated to Bangkok complaints: politely note this is outside dataset scope.

RESPONSE STYLE
──────────────
- Be conversational and helpful, not robotic.
- For aggregate answers: lead with the direct answer, then supporting numbers.
- For comparisons: use a short table or parallel structure.
- Keep responses concise (3-6 sentences or bullet points) unless a detailed breakdown is needed.
- Never repeat the question back to the user.
"""


# ── One-shot AI insight (Dashboard / Map / Explorer / Snowflake pages) ────────

@st.cache_data(ttl=3600, show_spinner=False)
def ai_insight(context_text: str, prompt: str) -> str:
    """
    Structured insight from pre-aggregated context (no retrieval).
    Called by analytics pages with their current filtered data as context.
    Result is cached — same data + prompt returns instantly.
    """
    client = get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": (
                "You are an urban analytics assistant for Bangkok Metropolitan Administration.\n"
                "Analyze the data summary and give concise, actionable insights.\n"
                "Answer in the same language as the TASK instruction (Thai or English).\n\n"
                "Rules:\n"
                "- Use ONLY numbers and names that appear in the DATA section.\n"
                "- Never guess, extrapolate, or add outside knowledge.\n"
                "- If the data is insufficient for the task, say so briefly.\n\n"
                "Format your answer as:\n"
                "**[One-sentence headline — the single most important finding]**\n"
                "• Bullet 1 with a specific number\n"
                "• Bullet 2 with a specific number\n"
                "• Bullet 3 with a specific number (optional)\n"
                "• Bullet 4 with a specific number (optional)\n"
                "Recommendation: [one concrete action BMA should take]"
            )},
            {"role": "user", "content": "DATA:\n{}\n\nTASK: {}".format(context_text, prompt)},
        ],
        temperature=0.3,
        max_tokens=512,
    )
    return response.choices[0].message.content


# ── RAG chatbot ───────────────────────────────────────────────────────────────

def ask_rag(question: str, chat_history: list) -> tuple[str, list]:
    """
    Full RAG pipeline:
      1. Expand query semantically
      2. Retrieve relevant complaint documents
      3. Prepend dataset-level statistics
      4. Generate context-aware answer via Groq
    """
    docs     = text_search(question, chat_history)
    context  = build_context(docs)
    overview = _dataset_overview()

    # Format recent conversation turns for the LLM
    history_lines = []
    for turn in chat_history[-6:]:
        role = "User" if turn["role"] == "user" else "Assistant"
        history_lines.append("{}: {}".format(role, turn["content"][:400]))
    history_text = "\n".join(history_lines)

    user_message = (
        "=== DATASET STATISTICS (all 168,589 records) ===\n"
        "{stats}\n\n"
        "=== RETRIEVED COMPLAINT DOCUMENTS ===\n"
        "{docs}\n\n"
        "=== CONVERSATION HISTORY ===\n"
        "{history}\n\n"
        "=== CURRENT QUESTION ===\n"
        "{question}"
    ).format(
        stats    = overview if overview else "(statistics unavailable)",
        docs     = context,
        history  = history_text if history_text else "(no prior conversation)",
        question = question,
    )

    client = get_groq_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.1,   # slight creativity while staying grounded
        max_tokens=1024,
    )
    return response.choices[0].message.content, docs
