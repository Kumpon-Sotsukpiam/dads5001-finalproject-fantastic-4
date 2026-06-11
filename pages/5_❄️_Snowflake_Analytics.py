"""
pages/5_Snowflake_Analytics.py
-------------------------------
Deep-dive analytics powered by Snowflake pre-aggregated tables.
Focus: resolution performance, reopen rates, satisfaction trends,
       and district scorecard — insights not easily visible on the main dashboard.
"""

import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
from utils.db import get_snowflake_conn
from utils.rag import ai_insight

st.set_page_config(page_title="Snowflake Analytics", page_icon="❄️", layout="wide")
st.title("❄️ Snowflake Deep-Dive Analytics")
st.caption("Source: Snowflake warehouse · Pre-aggregated from 168,589 complaints · Traffy Fondue Jul–Dec 2025")


# ── Helper ────────────────────────────────────────────────────────────────────
def _sf_query(sql):
    """Execute SQL against Snowflake and return a DataFrame."""
    conn = get_snowflake_conn()
    cur  = conn.cursor()
    cur.execute(sql)
    cols = [d[0].lower() for d in cur.description]
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return pd.DataFrame(rows, columns=cols)


# ── Cached loaders ────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner="Querying Snowflake ...")
def load_district_type():
    df = _sf_query("""
        SELECT year, month, district, problem_type, state_en,
               ticket_count, avg_resolution_minutes, avg_star, total_reopens
        FROM AGG_DISTRICT_TYPE
        ORDER BY year, month, district
    """)
    for c in ["ticket_count", "avg_resolution_minutes", "avg_star", "total_reopens", "month"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


@st.cache_data(ttl=3600, show_spinner="Querying Snowflake ...")
def load_weekly():
    df = _sf_query("""
        SELECT year, week_num, week_start, problem_type, ticket_count, finished_count
        FROM AGG_WEEKLY
        ORDER BY year, week_num
    """)
    df["week_start"]     = pd.to_datetime(df["week_start"], errors="coerce")
    df["ticket_count"]   = pd.to_numeric(df["ticket_count"],   errors="coerce")
    df["finished_count"] = pd.to_numeric(df["finished_count"], errors="coerce")
    return df


@st.cache_data(ttl=3600, show_spinner="Querying Snowflake ...")
def load_district_summary():
    df = _sf_query("""
        SELECT district, total_tickets, finished, in_progress_count,
               avg_resolution_minutes, avg_satisfaction
        FROM AGG_DISTRICT_SUMMARY
        ORDER BY total_tickets DESC
    """)
    for c in ["total_tickets", "finished", "in_progress_count",
              "avg_resolution_minutes", "avg_satisfaction"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df


# ── Load ──────────────────────────────────────────────────────────────────────
try:
    df_dt      = load_district_type()
    df_weekly  = load_weekly()
    df_summary = load_district_summary()
except Exception as e:
    import traceback
    st.error("❌ Snowflake connection failed: {}".format(e))
    st.code(traceback.format_exc())
    st.stop()

MONTH_MAP = {7:"Jul", 8:"Aug", 9:"Sep", 10:"Oct", 11:"Nov", 12:"Dec"}

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Filters")
    avail_months = sorted(df_dt["month"].dropna().unique().astype(int).tolist())
    sel_months = st.multiselect(
        "Month (2025)", avail_months, default=avail_months,
        format_func=lambda m: MONTH_MAP.get(m, str(m)),
    )
    if not sel_months:
        sel_months = avail_months

    types_in_months = sorted(
        df_dt[df_dt["month"].isin(sel_months)]["problem_type"].dropna().unique().tolist()
    )
    sel_types = st.multiselect(
        "Problem Types", types_in_months, default=[], placeholder="All types",
    )
    if not sel_types:
        sel_types = types_in_months

    top_n = st.slider("Top N Districts (scorecard)", 5, 50, 20, 5)

    st.divider()
    # Min complaints threshold — default = actual minimum in filtered data
    if not df_dt.empty:
        type_counts = df_dt.groupby("problem_type")["ticket_count"].sum()
        min_possible = max(1, int(type_counts.min()))
        max_possible = int(type_counts.max())
        default_min  = min_possible
    else:
        min_possible, max_possible, default_min = 1, 1000, 1
    min_tickets = st.slider(
        "Min. complaints to qualify (problem type filters)",
        min_value=min_possible,
        max_value=min(max_possible, 500),
        value=default_min,
        step=max(1, (min(max_possible, 500) - min_possible) // 20),
        help="Problem types with fewer tickets than this are excluded from 'Worst Performing' charts",
    )

# ── Filtered base ─────────────────────────────────────────────────────────────
dff = df_dt[
    df_dt["month"].isin(sel_months) &
    df_dt["problem_type"].isin(sel_types)
].copy()

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — Problem Severity Matrix
# ══════════════════════════════════════════════════════════════════════════════
st.header("🔴 Problem Severity Matrix")
st.caption("Problem types ranked by volume AND resolution time — upper-right quadrant = highest priority")

if not dff.empty:
    severity = dff.groupby("problem_type").agg(
        total_tickets        = ("ticket_count",           "sum"),
        avg_resolution_hours = ("avg_resolution_minutes", "mean"),
        avg_star             = ("avg_star",               "mean"),
        total_reopens        = ("total_reopens",          "sum"),
    ).reset_index()
    severity["avg_resolution_hours"] = (severity["avg_resolution_hours"] / 60).round(1)
    severity["reopen_rate"] = (
        severity["total_reopens"] / severity["total_tickets"] * 100
    ).round(1)

    fig_matrix = px.scatter(
        severity.nlargest(40, "total_tickets"),
        x="avg_resolution_hours",
        y="total_tickets",
        size="total_reopens",
        color="avg_star",
        color_continuous_scale="RdYlGn",
        range_color=[1, 5],
        hover_name="problem_type",
        hover_data={
            "avg_resolution_hours": ":.1f",
            "total_tickets": ":,",
            "reopen_rate": ":.1f",
            "avg_star": ":.2f",
        },
        labels={
            "avg_resolution_hours": "Avg Resolution Time (hours)",
            "total_tickets": "Total Tickets",
            "avg_star": "Avg ⭐",
        },
        height=500,
    )
    # Add quadrant lines
    med_x = severity["avg_resolution_hours"].median()
    med_y = severity["total_tickets"].median()
    fig_matrix.add_vline(x=med_x, line_dash="dash", line_color="gray", opacity=0.5)
    fig_matrix.add_hline(y=med_y, line_dash="dash", line_color="gray", opacity=0.5)
    fig_matrix.add_annotation(
        x=severity["avg_resolution_hours"].max() * 0.95,
        y=severity["total_tickets"].max() * 0.95,
        text="⚠️ High Volume<br>Slow Resolution",
        showarrow=False, font=dict(color="red", size=11),
    )
    fig_matrix.add_annotation(
        x=med_x * 0.1,
        y=severity["total_tickets"].max() * 0.95,
        text="✅ High Volume<br>Fast Resolution",
        showarrow=False, font=dict(color="green", size=11),
    )
    st.plotly_chart(fig_matrix, use_container_width=True)
    st.caption("Bubble size = total reopens · Color = avg satisfaction (red=low, green=high)")
else:
    st.info("No data.")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — Reopen Rate & Resolution Time Trends
# ══════════════════════════════════════════════════════════════════════════════
st.header("📈 Resolution & Reopen Trends Over Time")

col_l, col_r = st.columns(2)

with col_l:
    st.subheader("Avg Resolution Time by Month")
    if not dff.empty:
        rt = dff.groupby("month").agg(
            avg_hours=("avg_resolution_minutes", "mean")
        ).reset_index()
        rt["avg_hours"] = (rt["avg_hours"] / 60).round(1)
        rt["month_label"] = rt["month"].map(lambda m: MONTH_MAP.get(int(m), str(m)))
        rt = rt.sort_values("month")
        fig_rt = px.bar(
            rt, x="month_label", y="avg_hours",
            color="avg_hours", color_continuous_scale="Reds",
            labels={"avg_hours": "Avg Hours", "month_label": "Month"},
            text="avg_hours", height=350,
        )
        fig_rt.update_traces(texttemplate="%{text}h", textposition="outside")
        fig_rt.update_layout(coloraxis_showscale=False, yaxis_title="Hours")
        st.plotly_chart(fig_rt, use_container_width=True)
    else:
        st.info("No data.")

with col_r:
    st.subheader("Reopen Rate by Month (%)")
    if not dff.empty:
        rr = dff.groupby("month").agg(
            tickets=("ticket_count", "sum"),
            reopens=("total_reopens", "sum"),
        ).reset_index()
        rr["reopen_pct"] = (rr["reopens"] / rr["tickets"] * 100).round(2)
        rr["month_label"] = rr["month"].map(lambda m: MONTH_MAP.get(int(m), str(m)))
        rr = rr.sort_values("month")
        fig_rr = px.line(
            rr, x="month_label", y="reopen_pct",
            markers=True,
            labels={"reopen_pct": "Reopen Rate (%)", "month_label": "Month"},
            height=350,
        )
        fig_rr.update_traces(line=dict(color="#EF553B", width=3), marker=dict(size=8))
        fig_rr.update_layout(yaxis_ticksuffix="%")
        st.plotly_chart(fig_rr, use_container_width=True)
    else:
        st.info("No data.")

# Weekly completion rate trend
st.subheader("Weekly Completion Rate Trend")
if not df_weekly.empty:
    wk = df_weekly.groupby("week_start").agg(
        tickets=("ticket_count", "sum"),
        finished=("finished_count", "sum"),
    ).reset_index()
    wk["completion_pct"] = (wk["finished"] / wk["tickets"] * 100).round(1)
    wk = wk.sort_values("week_start")

    fig_wk = go.Figure()
    fig_wk.add_trace(go.Bar(
        x=wk["week_start"], y=wk["tickets"],
        name="Total Tickets", marker_color="#636EFA", opacity=0.6,
    ))
    fig_wk.add_trace(go.Scatter(
        x=wk["week_start"], y=wk["completion_pct"],
        name="Completion Rate (%)", yaxis="y2",
        mode="lines+markers",
        line=dict(color="#00CC96", width=2),
    ))
    fig_wk.update_layout(
        yaxis=dict(title="Tickets"),
        yaxis2=dict(title="Completion %", overlaying="y", side="right",
                    ticksuffix="%", range=[0, 100]),
        legend=dict(orientation="h"),
        height=380,
    )
    st.plotly_chart(fig_wk, use_container_width=True)
else:
    st.info("No weekly data.")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — Satisfaction Heatmap
# ══════════════════════════════════════════════════════════════════════════════
st.header("⭐ Satisfaction Score Heatmap")
st.caption("Average citizen satisfaction (1–5) per district per month — red = low, green = high")

if not dff.empty:
    top20_dist = (
        dff.groupby("district")["ticket_count"].sum()
        .nlargest(20).index.tolist()
    )
    heat = dff[dff["district"].isin(top20_dist)].groupby(["district", "month"]).agg(
        avg_star=("avg_star", "mean")
    ).reset_index()
    heat["month_label"] = heat["month"].map(lambda m: MONTH_MAP.get(int(m), str(m)))
    pivot = heat.pivot(index="district", columns="month_label", values="avg_star")
    col_order = [MONTH_MAP[m] for m in sorted(MONTH_MAP) if MONTH_MAP[m] in pivot.columns]
    pivot = pivot[col_order]

    fig_heat = px.imshow(
        pivot,
        color_continuous_scale="RdYlGn",
        zmin=1, zmax=5,
        text_auto=".2f",
        labels={"color": "Avg ⭐"},
        aspect="auto",
        height=550,
    )
    fig_heat.update_layout(xaxis_title="Month", yaxis_title="District")
    st.plotly_chart(fig_heat, use_container_width=True)
else:
    st.info("No data.")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — District Performance Scorecard
# ══════════════════════════════════════════════════════════════════════════════
st.header("🏆 District Performance Scorecard")
st.caption("All KPIs per district — sortable. Color = performance tier.")

if not df_summary.empty:
    scorecard = df_summary.head(top_n).copy()
    scorecard["avg_resolution_hours"] = (scorecard["avg_resolution_minutes"] / 60).round(1)
    scorecard["completion_rate_%"]    = (
        scorecard["finished"] / scorecard["total_tickets"] * 100
    ).round(1)

    # Add reopen data from AGG_DISTRICT_TYPE
    if not df_dt.empty:
        reopen_by_dist = df_dt.groupby("district").agg(
            total_reopens=("total_reopens", "sum"),
            total_tickets_dt=("ticket_count", "sum"),
        ).reset_index()
        reopen_by_dist["reopen_rate_%"] = (
            reopen_by_dist["total_reopens"] / reopen_by_dist["total_tickets_dt"] * 100
        ).round(2)
        scorecard = scorecard.merge(
            reopen_by_dist[["district", "reopen_rate_%"]], on="district", how="left"
        )

    display_cols = {
        "district":             "District",
        "total_tickets":        "Total Tickets",
        "completion_rate_%":    "Completion %",
        "avg_resolution_hours": "Avg Resolution (hrs)",
        "avg_satisfaction":     "Avg ⭐",
        "reopen_rate_%":        "Reopen Rate %",
        "in_progress_count":    "In Progress",
    }
    sc_display = scorecard[[c for c in display_cols if c in scorecard.columns]].copy()
    sc_display = sc_display.rename(columns=display_cols)
    sc_display = sc_display.sort_values("Total Tickets", ascending=False).reset_index(drop=True)

    def color_completion(val):
        if pd.isna(val): return ""
        if val >= 80:   return "background-color: #c6efce; color: #276221"
        if val >= 60:   return "background-color: #ffeb9c; color: #9c6500"
        return "background-color: #ffc7ce; color: #9c0006"

    def color_sat(val):
        if pd.isna(val): return ""
        if val >= 4.0:  return "background-color: #c6efce; color: #276221"
        if val >= 3.0:  return "background-color: #ffeb9c; color: #9c6500"
        return "background-color: #ffc7ce; color: #9c0006"

    def color_reopen(val):
        if pd.isna(val): return ""
        if val <= 5:    return "background-color: #c6efce; color: #276221"
        if val <= 15:   return "background-color: #ffeb9c; color: #9c6500"
        return "background-color: #ffc7ce; color: #9c0006"

    styled = sc_display.style \
        .map(color_completion, subset=["Completion %"]) \
        .map(color_sat,        subset=["Avg ⭐"]) \
        .format({
            "Total Tickets":         "{:,.0f}",
            "Completion %":          "{:.1f}%",
            "Avg Resolution (hrs)":  "{:.1f}",
            "Avg ⭐":                "{:.2f}",
            "In Progress":           "{:,.0f}",
        })
    if "Reopen Rate %" in sc_display.columns:
        styled = styled \
            .map(color_reopen, subset=["Reopen Rate %"]) \
            .format({"Reopen Rate %": "{:.2f}%"})

    st.dataframe(styled, use_container_width=True, height=600)

    # Legend
    st.caption(
        "🟢 Green = good performance  🟡 Yellow = moderate  🔴 Red = needs attention  |  "
        "Completion: 🟢 ≥80%  🟡 60–79%  🔴 <60%  |  "
        "Satisfaction: 🟢 ≥4.0  🟡 3.0–3.9  🔴 <3.0  |  "
        "Reopen: 🟢 ≤5%  🟡 5–15%  🔴 >15%"
    )

    # Bottom 5 districts highlight
    st.subheader("⚠️ Districts Needing Attention")
    bottom5 = scorecard.nsmallest(5, "avg_satisfaction")[
        ["district", "total_tickets", "completion_rate_%",
         "avg_resolution_hours", "avg_satisfaction"]
    ].copy()
    bottom5.columns = ["District", "Tickets", "Completion %", "Avg Resolution (hrs)", "Avg ⭐"]
    st.dataframe(bottom5.reset_index(drop=True), use_container_width=True)

else:
    st.info("No district summary data.")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — Worst Problem Types (slowest + most reopened)
# ══════════════════════════════════════════════════════════════════════════════
st.header("🐢 Worst Performing Problem Types")

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Slowest to Resolve (Top 10)")
    if not dff.empty:
        slow = dff.groupby("problem_type").agg(
            avg_hours=("avg_resolution_minutes", "mean"),
            tickets=("ticket_count", "sum"),
        ).reset_index()
        slow["avg_hours"] = (slow["avg_hours"] / 60).round(1)
        slow = slow[slow["tickets"] >= min_tickets].nlargest(10, "avg_hours").sort_values("avg_hours")
        fig_slow = px.bar(
            slow, x="avg_hours", y="problem_type", orientation="h",
            color="avg_hours", color_continuous_scale="Reds",
            text="avg_hours",
            labels={"avg_hours": "Avg Hours", "problem_type": ""},
            height=380,
        )
        fig_slow.update_traces(texttemplate="%{text}h", textposition="outside")
        fig_slow.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_slow, use_container_width=True)
        st.caption("Min. {:,} complaints to qualify (adjust in sidebar)".format(min_tickets))
    else:
        st.info("No data.")

with col_b:
    st.subheader("Most Reopened Problem Types (Top 10)")
    if not dff.empty:
        reopen = dff.groupby("problem_type").agg(
            total_reopens=("total_reopens", "sum"),
            tickets=("ticket_count", "sum"),
        ).reset_index()
        reopen["reopen_rate"] = (reopen["total_reopens"] / reopen["tickets"] * 100).round(1)
        reopen = reopen[reopen["tickets"] >= min_tickets].nlargest(10, "reopen_rate").sort_values("reopen_rate")
        fig_reopen = px.bar(
            reopen, x="reopen_rate", y="problem_type", orientation="h",
            color="reopen_rate", color_continuous_scale="Oranges",
            text="reopen_rate",
            labels={"reopen_rate": "Reopen Rate (%)", "problem_type": ""},
            height=380,
        )
        fig_reopen.update_traces(texttemplate="%{text}%", textposition="outside")
        fig_reopen.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig_reopen, use_container_width=True)
        st.caption("Min. {:,} complaints to qualify (adjust in sidebar)".format(min_tickets))
    else:
        st.info("No data.")

# ── AI Insight (AI mode only) ─────────────────────────────────────────────────
st.divider()
if st.session_state.get("ai_mode", False):
    st.subheader("🤖 AI Insight")
    if st.button("✨ Analyze Snowflake performance data", use_container_width=True):
        if not df_summary.empty and not dff.empty:
            # Worst 3 districts by satisfaction
            worst_sat = df_summary.nsmallest(3, "avg_satisfaction")[
                ["district", "total_tickets", "avg_satisfaction", "avg_resolution_minutes"]
            ].copy()
            worst_sat["avg_resolution_hours"] = (worst_sat["avg_resolution_minutes"] / 60).round(1)

            # Slowest problem types
            slow_types = dff.groupby("problem_type").agg(
                avg_hours=("avg_resolution_minutes", "mean"),
                tickets=("ticket_count", "sum"),
            ).reset_index()
            slow_types["avg_hours"] = (slow_types["avg_hours"] / 60).round(1)
            slow_types = slow_types[slow_types["tickets"] >= min_tickets].nlargest(3, "avg_hours")

            # Most reopened
            reopen_types = dff.groupby("problem_type").agg(
                reopens=("total_reopens", "sum"),
                tickets=("ticket_count", "sum"),
            ).reset_index()
            reopen_types["reopen_pct"] = (reopen_types["reopens"] / reopen_types["tickets"] * 100).round(1)
            reopen_types = reopen_types[reopen_types["tickets"] >= min_tickets].nlargest(3, "reopen_pct")

            context = (
                "Districts with lowest satisfaction:\n{}\n\n"
                "Slowest problem types to resolve:\n{}\n\n"
                "Most reopened problem types:\n{}"
            ).format(
                worst_sat[["district", "avg_satisfaction", "avg_resolution_hours"]].to_string(index=False),
                slow_types[["problem_type", "avg_hours", "tickets"]].to_string(index=False),
                reopen_types[["problem_type", "reopen_pct", "tickets"]].to_string(index=False),
            )
            with st.spinner("Analyzing ..."):
                insight = ai_insight(context,
                    "Based on this Snowflake performance data for Bangkok complaints, "
                    "identify the most critical service delivery problems. "
                    "Which districts and problem types need urgent intervention and why?")
            st.info(insight)
        else:
            st.warning("Not enough data to analyze.")
else:
    st.caption("💡 Enable **AI mode** on the Home page to get AI-powered performance analysis.")
