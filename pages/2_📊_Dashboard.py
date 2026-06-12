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
from utils.theme import inject_css, get_template
from utils.ui import ai_mode_toggle

st.set_page_config(page_title="Dashboard", page_icon="📊", layout="wide")
p = inject_css()
t = get_template()
ai_mode_toggle()
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

# ── Sidebar filters (defined BEFORE the KPIs so the cards react to them) ─────
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

    all_districts = sorted(monthly_trend["district"].dropna().unique().tolist()) \
        if not monthly_trend.empty and "district" in monthly_trend.columns else []
    sel_districts = st.multiselect(
        "District", all_districts,
        default=[],
        placeholder="All districts",
    )

    all_types = sorted(monthly_trend["problem_type"].dropna().unique().tolist()) \
        if not monthly_trend.empty else []
    sel_types = st.multiselect(
        "Problem Types", all_types,
        default=[],
        placeholder="All types",
    )
    # Empty selection == no filter applied (all districts / all types)

# ── Filtered slice — drives the KPI cards and the monthly trend chart ────────
if not monthly_trend.empty:
    mt = monthly_trend[monthly_trend["month"].isin(sel_months)]
    if sel_districts and "district" in mt.columns:
        mt = mt[mt["district"].isin(sel_districts)]
    if sel_types:
        mt = mt[mt["problem_type"].isin(sel_types)]
else:
    mt = pd.DataFrame()

# ── KPI Row — follows the sidebar filters ────────────────────────────────────
if not mt.empty:
    total    = int(pd.to_numeric(mt["ticket_count"], errors="coerce").sum())
    finished = int(pd.to_numeric(mt.get("finished_count"), errors="coerce").sum()) \
        if "finished_count" in mt.columns else 0
    rate     = round(finished / total * 100, 1) if total else 0.0
    # Correct WEIGHTED satisfaction: total stars / number of rated tickets
    # (the old version averaged per-district averages, which over-weighted
    #  small districts)
    _ss = pd.to_numeric(mt.get("star_sum"),   errors="coerce").sum() \
        if "star_sum" in mt.columns else 0.0
    _sc = pd.to_numeric(mt.get("star_count"), errors="coerce").sum() \
        if "star_count" in mt.columns else 0
    avg_sat = round(_ss / _sc, 2) if _sc else 0.0
else:
    total = finished = 0
    rate  = avg_sat = 0.0

c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Tickets",       "{:,}".format(total))
c2.metric("Finished",            "{:,}".format(finished))
c3.metric("Completion Rate",     "{}%".format(rate))
c4.metric("Avg Satisfaction ⭐", "{:.2f} / 5".format(avg_sat))
st.caption("ตัวเลขทั้ง 4 การ์ดเปลี่ยนตาม filter เดือน/เขต/ประเภทปัญหาใน sidebar")

st.divider()

col_left, col_right = st.columns(2)

# Chart 1: Weekly ticket volume
with col_left:
    st.subheader("📈 Which weeks saw the highest complaint volume?")
    if not weekly_trend.empty:
        wt = weekly_trend.copy()
        wt["week_start"] = pd.to_datetime(wt["week_start"], errors="coerce")
        wt = wt.dropna(subset=["week_start"]).sort_values("week_start")
        wt = wt[wt["week_start"].dt.month.isin(sel_months)]
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=wt["week_start"], y=wt["ticket_count"],
            name="Total", marker_color="#2E6CB8",
        ))
        fig.add_trace(go.Scatter(
            x=wt["week_start"], y=wt["finished_count"],
            name="Finished", mode="lines+markers",
            line=dict(color="#27AE60", width=2),
        ))
        fig.update_layout(template=t,
            xaxis_title="Week", yaxis_title="Tickets",
            legend=dict(orientation="h"), height=350,
        )
        st.plotly_chart(fig, use_container_width=True)
        if not wt.empty:
            _peak = wt.loc[wt["ticket_count"].idxmax()]
            st.caption("➡️ Peak: week of {:%d %b} with {:,.0f} tickets.".format(
                _peak["week_start"], _peak["ticket_count"]))
    else:
        st.info("No weekly data available.")

# Chart 2: Top Problem Types — derived from the filtered slice so it follows
# both the month and type filters (consistent with the KPI cards)
with col_right:
    st.subheader("🏷️ What do citizens complain about most?")
    if not mt.empty:
        tp = (mt.groupby("problem_type", observed=True)["ticket_count"]
                .sum().reset_index()
                .rename(columns={"ticket_count": "total"})
                .nlargest(15, "total"))
        tp["total"] = pd.to_numeric(tp["total"], errors="coerce")
        fig2 = px.bar(
            tp.sort_values("total"),
            x="total", y="problem_type", orientation="h",
            color="total", color_continuous_scale="Blues",
            labels={"total": "Tickets", "problem_type": ""},
            height=350,
        )
        fig2.update_layout(template=t, coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)
        if not tp.empty and total:
            _top = tp.loc[tp["total"].idxmax()]
            st.caption("➡️ \"{}\" leads with {:,.0f} tickets ({:.1f}% of all complaints).".format(
                _top["problem_type"], _top["total"], _top["total"] / total * 100))
    else:
        st.info("No data available.")

col3_l, col3_r = st.columns(2)

# Chart 4: Top 20 Districts — derived from the filtered slice (follows filters)
with col3_l:
    st.subheader("🏘️ Which districts generate the most complaints?")
    if not mt.empty and "district" in mt.columns:
        ds = mt.groupby("district", observed=True).agg(
            total_tickets=("ticket_count", "sum"),
        ).reset_index()
        ds["total_tickets"] = pd.to_numeric(ds["total_tickets"], errors="coerce")
        ds = ds.sort_values("total_tickets", ascending=False)
        top20 = ds.head(20).sort_values("total_tickets")
        fig4 = px.bar(
            top20, x="total_tickets", y="district", orientation="h",
            color="total_tickets", color_continuous_scale="Blues",
            labels={"total_tickets": "Tickets", "district": ""},
            template=t,
            height=500,
        )
        fig4.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig4, use_container_width=True)
        _top_d = ds.iloc[0]
        st.caption("➡️ {} tops the list with {:,.0f} tickets.".format(
            _top_d["district"], _top_d["total_tickets"]))
    else:
        st.info("No data available.")

# Chart 5: Resolution time by type
with col3_r:
    st.subheader("🐢 Which problems take longest to resolve?")
    if not resolution_stats.empty:
        rs = resolution_stats.copy()
        rs["avg_hours"] = pd.to_numeric(rs["avg_hours"], errors="coerce").round(1)
        rs = rs.dropna(subset=["avg_hours"])
        if sel_types:
            rs = rs[rs["problem_type"].isin(sel_types)]
        fig5 = px.bar(
            rs.sort_values("avg_hours"),
            x="avg_hours", y="problem_type", orientation="h",
            color="avg_hours", color_continuous_scale="Reds",
            labels={"avg_hours": "Hours", "problem_type": ""},
            height=500,
        )
        fig5.update_layout(template=t, coloraxis_showscale=False)
        st.plotly_chart(fig5, use_container_width=True)
        if not rs.empty:
            _slow = rs.loc[rs["avg_hours"].idxmax()]
            st.caption("➡️ \"{}\" is the slowest: {:,.0f} hours (≈ {:.0f} days) on average.".format(
                _slow["problem_type"], _slow["avg_hours"], _slow["avg_hours"] / 24))
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
