"""
pages/3_Explorer.py
--------------------
Raw data explorer — filter with cascading dropdowns + DuckDB.
- Default: show ALL records (month 7-12, no other filters)
- Cascading filters: Month → District → Problem Type → Status
- "Matching records" shows only filtered count, not total
Source: MongoDB (all records, cached).
"""

import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from utils.queries import get_mongo_sample
from utils.rag import ai_insight
from utils.ui import ai_mode_toggle

st.set_page_config(page_title="Data Explorer", page_icon="🔍", layout="wide")
st.title("🔍 Data Explorer")
st.caption("Source: MongoDB · In-memory DuckDB filtering · All records")

# ── Load ALL data (no limit) ──────────────────────────────────────────────────
with st.spinner("Fetching records from MongoDB ..."):
    try:
        df = get_mongo_sample()
    except Exception as e:
        st.error("Failed to connect to MongoDB: {}".format(e))
        st.stop()

if df.empty:
    st.warning("No data returned from MongoDB. Check your connection.")
    st.stop()

# Ensure month column is numeric
if "month" in df.columns:
    df["month"] = pd.to_numeric(df["month"], errors="coerce").fillna(0).astype(int)

# Fill missing columns to avoid KeyError
for col in ["district", "problem_type", "state_en", "comment", "timestamp"]:
    if col not in df.columns:
        df[col] = None

ai_mode_toggle()

# ── Sidebar: cascading filters ────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    # Month range — default เดือน 7 เพื่อให้โหลดเร็ว
    month_range = st.slider("Month range", 7, 12, (7, 7))

    # Dataset after month filter (used to build downstream options)
    df_after_month = df[df["month"].between(month_range[0], month_range[1])]

    # Filter 1: District — options from month-filtered dataset
    all_districts = sorted(df_after_month["district"].dropna().unique().tolist())
    sel_districts = st.multiselect(
        "District",
        options=all_districts,
        default=[],
        placeholder="All districts",
    )

    # Dataset after month + district
    if sel_districts:
        df_after_district = df_after_month[df_after_month["district"].isin(sel_districts)]
    else:
        df_after_district = df_after_month

    # Filter 2: Problem Type — only types in selected districts
    available_types = sorted(df_after_district["problem_type"].dropna().unique().tolist())
    sel_types = st.multiselect(
        "Problem Type",
        options=available_types,
        default=[],
        placeholder="All types",
    )

    # Dataset after month + district + type
    if sel_types:
        df_after_type = df_after_district[df_after_district["problem_type"].isin(sel_types)]
    else:
        df_after_type = df_after_district

    # Filter 3: Status — only statuses in selected district + type
    available_states = sorted(df_after_type["state_en"].dropna().unique().tolist())
    sel_states = st.multiselect(
        "Status",
        options=available_states,
        default=[],
        placeholder="All statuses",
    )

    # Keyword search
    keyword = st.text_input("Keyword in comment", "")

# ── Build DuckDB filter query ─────────────────────────────────────────────────
conditions = ["month >= {} AND month <= {}".format(month_range[0], month_range[1])]

if sel_districts:
    district_list = ", ".join("'{}'".format(d.replace("'", "''")) for d in sel_districts)
    conditions.append("district IN ({})".format(district_list))

if sel_types:
    type_list = ", ".join("'{}'".format(t.replace("'", "''")) for t in sel_types)
    conditions.append("problem_type IN ({})".format(type_list))

if sel_states:
    state_list = ", ".join("'{}'".format(s.replace("'", "''")) for s in sel_states)
    conditions.append("state_en IN ({})".format(state_list))

if keyword.strip():
    kw = keyword.strip().replace("'", "''")
    conditions.append("LOWER(COALESCE(comment, '')) LIKE '%{}%'".format(kw.lower()))

where_clause = " AND ".join(conditions)
sql = "SELECT * FROM df WHERE {} ORDER BY month DESC".format(where_clause)

try:
    con = duckdb.connect()
    con.register("df", df)
    filtered = con.execute(sql).df()
    con.close()
except Exception as e:
    st.error("Filter error: {}".format(e))
    filtered = df_after_month.copy()

# ── Summary — show filtered count only ───────────────────────────────────────
total_in_range = len(df_after_month)
st.metric("Matching records", "{:,} / {:,}".format(len(filtered), total_in_range))

col1, col2 = st.columns(2)

with col1:
    if not filtered.empty and "state_en" in filtered.columns:
        state_counts = filtered["state_en"].value_counts().reset_index()
        state_counts.columns = ["status", "count"]
        fig = px.pie(
            state_counts, values="count", names="status",
            title="Status Distribution", height=250,
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    if not filtered.empty and "problem_type" in filtered.columns:
        type_counts = filtered["problem_type"].value_counts().head(10).reset_index()
        type_counts.columns = ["type", "count"]
        fig2 = px.bar(
            type_counts, x="count", y="type", orientation="h",
            title="Top Problem Types", height=250,
            labels={"count": "", "type": ""},
            color="count", color_continuous_scale="Blues",
        )
        fig2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)

# ── Table ─────────────────────────────────────────────────────────────────────
display_cols = [
    "ticket_id", "problem_type", "district", "subdistrict",
    "state_en", "star", "duration_minutes_total", "month", "comment",
]
available_cols = [c for c in display_cols if c in filtered.columns]

if available_cols:
    rename_map = {
        "ticket_id":              "Ticket",
        "problem_type":           "Type",
        "district":               "District",
        "subdistrict":            "Sub-district",
        "state_en":               "Status",
        "star":                   "⭐",
        "duration_minutes_total": "Duration (min)",
        "month":                  "Month",
        "comment":                "Comment",
    }
    st.dataframe(
        filtered[available_cols].rename(columns=rename_map),
        use_container_width=True,
        height=500,
    )

    csv = filtered[available_cols].to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Download filtered data (CSV)",
        data=csv,
        file_name="bangkok_complaints_filtered.csv",
        mime="text/csv",
    )
else:
    st.info("No data columns available to display.")

# ── AI Insight (AI mode only) ─────────────────────────────────────────────────
st.divider()
if st.session_state.get("ai_mode", False):
    st.subheader("🤖 AI Insight")
    if st.button("✨ Summarize filtered records", use_container_width=True):
        if not filtered.empty:
            top_types    = filtered["problem_type"].value_counts().head(5).to_dict() if "problem_type" in filtered.columns else {}
            top_districts = filtered["district"].value_counts().head(5).to_dict()    if "district"     in filtered.columns else {}
            top_status   = filtered["state_en"].value_counts().to_dict()             if "state_en"     in filtered.columns else {}
            avg_star     = round(pd.to_numeric(filtered.get("star", pd.Series()), errors="coerce").mean(), 2)
            avg_dur      = round(pd.to_numeric(filtered.get("duration_minutes_total", pd.Series()), errors="coerce").mean() / 60, 1)
            context = (
                "Filtered records: {:,}\n"
                "Top problem types: {}\n"
                "Top districts: {}\n"
                "Status breakdown: {}\n"
                "Avg satisfaction: {}\n"
                "Avg resolution time: {} hrs"
            ).format(len(filtered), top_types, top_districts, top_status, avg_star, avg_dur)
            with st.spinner("Analyzing ..."):
                insight = ai_insight(context,
                    "Summarize what these filtered Bangkok complaint records reveal. "
                    "What are the main issues, which areas are affected, and what should be prioritized?")
            st.info(insight)
        else:
            st.warning("No filtered data to analyze.")
else:
    st.caption("💡 Enable **AI mode** on the Home page to get AI-powered summaries of filtered records.")
