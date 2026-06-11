"""
pages/3_Explorer.py
--------------------
Raw data explorer - filter with DuckDB, display with Streamlit dataframe.
Source: MongoDB sample (cached).
"""

import streamlit as st
import pandas as pd
import duckdb
import plotly.express as px
from utils.queries import get_mongo_sample

st.set_page_config(page_title="Data Explorer", page_icon="🔍", layout="wide")
st.title("🔍 Data Explorer")
st.caption("Source: MongoDB · In-memory DuckDB filtering · 2,000-record sample")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Fetching records from MongoDB ..."):
    try:
        df = get_mongo_sample(limit=2000)
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

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")

    all_districts = sorted(df["district"].dropna().unique().tolist())
    sel_districts = st.multiselect("District", all_districts, default=[])

    all_types = sorted(df["problem_type"].dropna().unique().tolist())
    sel_types = st.multiselect("Problem Type", all_types, default=[])

    all_states = sorted(df["state_en"].dropna().unique().tolist())
    sel_states = st.multiselect("Status", all_states, default=[])

    month_min = int(df["month"].min()) if df["month"].notna().any() else 7
    month_max = int(df["month"].max()) if df["month"].notna().any() else 12
    month_min = max(month_min, 7)
    month_max = min(month_max, 12)
    if month_min > month_max:
        month_min, month_max = 7, 12
    month_range = st.slider("Month range", 7, 12, (month_min, month_max))

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
# Sort by month DESC (avoid None timestamp crash)
sql = "SELECT * FROM df WHERE {} ORDER BY month DESC".format(where_clause)

try:
    con = duckdb.connect()
    con.register("df", df)
    filtered = con.execute(sql).df()
    con.close()
except Exception as e:
    st.error("Filter error: {}".format(e))
    filtered = df.copy()

# ── Summary ───────────────────────────────────────────────────────────────────
st.metric("Matching records", "{:,} / {:,}".format(len(filtered), len(df)))

col1, col2 = st.columns(2)

with col1:
    if not filtered.empty and "state_en" in filtered.columns:
        state_counts = filtered["state_en"].value_counts().reset_index()
        state_counts.columns = ["status", "count"]
        fig = px.pie(state_counts, values="count", names="status",
                     title="Status Distribution", height=250)
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
