"""
pages/1_Dashboard.py
--------------------
Non-AI analytics dashboard powered by Snowflake + Plotly.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.queries import (
    get_district_summary,
    get_monthly_trend,
    get_weekly_trend,
    get_top_problem_types,
    get_resolution_stats,
)
from utils.rag import ai_insight

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
st.title("📊 Analytics Dashboard")
st.caption("Source: MongoDB + DuckDB · Data: Traffy Fondue Jul-Dec 2025")

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading data ..."):
    try:
        district_summary = get_district_summary()
        monthly_trend    = get_monthly_trend()
        weekly_trend     = get_weekly_trend()
        top_problems     = get_top_problem_types(15)
        resolution_stats = get_resolution_stats()
    except Exception as e:
        st.error("Failed to load data: {}".format(e))
        st.stop()

# ── KPI Row ───────────────────────────────────────────────────────────────────
if not district_summary.empty:
    total    = int(district_summary["total_tickets"].sum())
    finished = int(district_summary["finished"].sum())
    rate     = round(finished / total * 100, 1) if total else 0.0
    avg_sat  = round(pd.to_numeric(district_summary["avg_satisfaction"],
                                   errors="coerce").mean(), 2)
else:
    total = finished = 0
    rate  = avg_sat = 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Tickets",       "{:,}".format(total))
c2.metric("Finished",            "{:,}".format(finished))
c3.metric("Completion Rate",     "{}%".format(rate))
c4.metric("Avg Satisfaction ⭐", "{:.2f} / 5".format(avg_sat))

st.divider()

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    month_options = list(range(7, 13))
    sel_months = st.multiselect(
        "Month (2025)", month_options,
        default=month_options,
        format_func=lambda m: ["Jul","Aug","Sep","Oct","Nov","Dec"][m - 7],
    )
    if not sel_months:
        sel_months = month_options

    all_types = sorted(top_problems["problem_type"].dropna().tolist()) \
        if not top_problems.empty else []
    sel_types = st.multiselect(
        "Problem Types", all_types,
        default=[],
        placeholder="All types",
    )
    # Empty = show all types
    if not sel_types:
        sel_types = all_types

# ── Filter monthly trend ──────────────────────────────────────────────────────
if not monthly_trend.empty and sel_types:
    mt = monthly_trend[
        monthly_trend["month"].isin(sel_months) &
        monthly_trend["problem_type"].isin(sel_types)
    ]
elif not monthly_trend.empty:
    mt = monthly_trend[monthly_trend["month"].isin(sel_months)]
else:
    mt = pd.DataFrame()

col_left, col_right = st.columns(2)

# Chart 1: Weekly ticket volume
with col_left:
    st.subheader("Weekly Ticket Volume")
    if not weekly_trend.empty:
        wt = weekly_trend.copy()
        wt["week_start"] = pd.to_datetime(wt["week_start"], errors="coerce")
        wt = wt.dropna(subset=["week_start"]).sort_values("week_start")
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=wt["week_start"], y=wt["ticket_count"],
            name="Total", marker_color="#636EFA",
        ))
        fig.add_trace(go.Scatter(
            x=wt["week_start"], y=wt["finished_count"],
            name="Finished", mode="lines+markers",
            line=dict(color="#00CC96", width=2),
        ))
        fig.update_layout(
            xaxis_title="Week", yaxis_title="Tickets",
            legend=dict(orientation="h"), height=350,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No weekly data available.")

# Chart 2: Top Problem Types
with col_right:
    st.subheader("Top 15 Problem Types")
    if not top_problems.empty:
        tp = top_problems.copy()
        tp["total"] = pd.to_numeric(tp["total"], errors="coerce")
        fig2 = px.bar(
            tp.sort_values("total"),
            x="total", y="problem_type", orientation="h",
            color="total", color_continuous_scale="Blues",
            labels={"total": "Tickets", "problem_type": ""},
            height=350,
        )
        fig2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No data available.")

# Chart 3: Monthly trend by problem type
st.subheader("Monthly Ticket Trend by Problem Type")
if not mt.empty:
    mt_agg = mt.copy()
    mt_agg["ticket_count"] = pd.to_numeric(mt_agg["ticket_count"], errors="coerce")
    mt_agg = mt_agg.groupby(["month", "problem_type"])["ticket_count"].sum().reset_index()
    month_labels = {7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"}
    mt_agg["month_label"] = mt_agg["month"].map(month_labels)
    fig3 = px.line(
        mt_agg, x="month_label", y="ticket_count",
        color="problem_type", markers=True,
        labels={"ticket_count": "Tickets", "month_label": "Month",
                "problem_type": "Type"},
        height=400,
    )
    st.plotly_chart(fig3, use_container_width=True)
else:
    st.info("No data matches selected filters.")

col3_l, col3_r = st.columns(2)

# Chart 4: Top 20 Districts
with col3_l:
    st.subheader("Top 20 Districts by Ticket Count")
    if not district_summary.empty:
        ds = district_summary.copy()
        ds["total_tickets"]    = pd.to_numeric(ds["total_tickets"],    errors="coerce")
        ds["avg_satisfaction"] = pd.to_numeric(ds["avg_satisfaction"], errors="coerce")
        top20 = ds.head(20).sort_values("total_tickets")
        fig4 = px.bar(
            top20, x="total_tickets", y="district", orientation="h",
            color="avg_satisfaction",
            color_continuous_scale="RdYlGn", range_color=[1, 5],
            labels={"total_tickets": "Tickets", "district": "",
                    "avg_satisfaction": "Avg ⭐"},
            height=500,
        )
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No data available.")

# Chart 5: Resolution time by type
with col3_r:
    st.subheader("Avg Resolution Time (hours) by Problem Type")
    if not resolution_stats.empty:
        rs = resolution_stats.copy()
        rs["avg_hours"] = pd.to_numeric(rs["avg_hours"], errors="coerce").round(1)
        rs = rs.dropna(subset=["avg_hours"])
        fig5 = px.bar(
            rs.sort_values("avg_hours"),
            x="avg_hours", y="problem_type", orientation="h",
            color="avg_hours", color_continuous_scale="Reds",
            labels={"avg_hours": "Hours", "problem_type": ""},
            height=500,
        )
        fig5.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("No data available.")

# ── AI Insight (AI mode only) ─────────────────────────────────────────────────
st.divider()
if st.session_state.get("ai_mode", False):
    st.subheader("🤖 AI Insight")
    if st.button("✨ Analyze current dashboard data", use_container_width=True):
        if not district_summary.empty and not top_problems.empty:
            top5_dist = district_summary.head(5)[["district","total_tickets","avg_satisfaction"]].to_string(index=False)
            top5_type = top_problems.head(5)[["problem_type","total"]].to_string(index=False) if "total" in top_problems.columns else ""
            context = (
                "KPIs: Total={:,}, Finished={:,}, Completion={:.1f}%, Avg Satisfaction={:.2f}\n"
                "Top 5 Districts:\n{}\n"
                "Top 5 Problem Types:\n{}"
            ).format(total, finished, rate, avg_sat, top5_dist, top5_type)
            with st.spinner("Analyzing ..."):
                insight = ai_insight(context,
                    "Summarize key findings from this Bangkok complaints dashboard. "
                    "Highlight which districts and problem types need the most attention and why.")
            st.info(insight)
        else:
            st.warning("Not enough data to analyze.")
else:
    st.caption("💡 Enable **AI mode** on the Home page to get AI-powered insights on this dashboard.")
