"""
pages/2_Map.py
--------------
Geographic distribution of complaints.
- Loads all data once (cached via get_map_data)
- Cascading filters: selecting Month narrows Problem Type options
- Default: show ALL records (no pre-filter)
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from utils.queries import get_map_data

st.set_page_config(page_title="Map", page_icon="🗺️", layout="wide")
st.title("🗺️ Geographic Distribution")
st.caption("Source: MongoDB · GPS coordinates from Traffy Fondue reports")

# ── Load ALL data once (cached) ───────────────────────────────────────────────
with st.spinner("Loading map data from MongoDB ..."):
    try:
        df_all = get_map_data(month=None, problem_type=None, limit=10000)
    except Exception as e:
        st.error("Failed to load map data: {}".format(e))
        st.stop()

if df_all.empty:
    st.warning("No data found in MongoDB.")
    st.stop()

# Clean coordinates on full dataset
df_all = df_all.copy()
df_all["latitude"]  = pd.to_numeric(df_all.get("latitude"),  errors="coerce")
df_all["longitude"] = pd.to_numeric(df_all.get("longitude"), errors="coerce")
df_all = df_all.dropna(subset=["latitude", "longitude"])
df_all = df_all[
    df_all["latitude"].between(13.4, 14.1) &
    df_all["longitude"].between(100.3, 101.0)
]

# ── Sidebar: cascading filters ────────────────────────────────────────────────
with st.sidebar:
    st.header("Map Filters")

    # Filter 1: Month
    month_map = {7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"}
    available_months = sorted(
        [m for m in df_all["month"].dropna().unique() if m in month_map]
    ) if "month" in df_all.columns else []
    month_options = [None] + available_months
    sel_month = st.selectbox(
        "Month (2025)",
        options=month_options,
        format_func=lambda m: "All months" if m is None else month_map.get(int(m), str(m)),
    )

    # Filter 2: Problem Type — options depend on selected month
    if sel_month is not None and "month" in df_all.columns:
        df_month_filtered = df_all[df_all["month"] == sel_month]
    else:
        df_month_filtered = df_all

    if "problem_type" in df_month_filtered.columns:
        available_types = sorted(df_month_filtered["problem_type"].dropna().unique().tolist())
    else:
        available_types = []

    type_options = ["All"] + available_types
    sel_type = st.selectbox("Problem Type", type_options)

    max_pts = st.slider("Max points on map", 500, 10000, 5000, step=500)

# ── Apply filters ─────────────────────────────────────────────────────────────
df = df_all.copy()

if sel_month is not None and "month" in df.columns:
    df = df[df["month"] == sel_month]

if sel_type != "All" and "problem_type" in df.columns:
    df = df[df["problem_type"] == sel_type]

# Limit points for map rendering
df = df.head(max_pts)

if df.empty:
    st.warning("No valid GPS coordinates in filtered data.")
    st.stop()

st.metric("Showing", "{:,} complaints on map".format(len(df)))

# ── Color map by state ────────────────────────────────────────────────────────
COLOR_MAP = {
    "finished":    [0, 200, 100, 160],
    "in_progress": [255, 165, 0, 180],
    "pending":     [200, 50, 50, 180],
    "other":       [150, 150, 150, 140],
}
DEFAULT_COLOR = [150, 150, 150, 140]


def get_color(state):
    return COLOR_MAP.get(state, DEFAULT_COLOR)


df["color"] = df["state_en"].apply(get_color)

# ── pydeck map ────────────────────────────────────────────────────────────────
df["comment_short"] = df["comment"].fillna("").astype(str).str[:150]

layer = pdk.Layer(
    "ScatterplotLayer",
    data=df,
    get_position=["longitude", "latitude"],
    get_color="color",
    get_radius=80,
    pickable=True,
)

view = pdk.ViewState(latitude=13.75, longitude=100.52, zoom=10, pitch=0)

tooltip = {
    "html": "<b>{problem_type}</b><br/>{district}<br/>Status: {state_en}<br/>{comment_short}",
    "style": {"backgroundColor": "steelblue", "color": "white", "maxWidth": "300px"},
}

st.pydeck_chart(pdk.Deck(layers=[layer], initial_view_state=view, tooltip=tooltip))

st.markdown("🟢 **Finished** &nbsp;&nbsp; 🟠 **In Progress** &nbsp;&nbsp; 🔴 **Pending**")

# ── Distribution charts ───────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("By Status")
    if "state_en" in df.columns:
        status_counts = df["state_en"].value_counts().reset_index()
        status_counts.columns = ["status", "count"]
        fig = px.pie(
            status_counts, values="count", names="status",
            color="status",
            color_discrete_map={
                "finished":    "#00C864",
                "in_progress": "#FFA500",
                "pending":     "#C83232",
                "other":       "#AAAAAA",
            },
            height=300,
        )
        st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("By Problem Type (top 10)")
    if "problem_type" in df.columns:
        type_counts = df["problem_type"].value_counts().head(10).reset_index()
        type_counts.columns = ["type", "count"]
        fig2 = px.bar(
            type_counts, x="count", y="type", orientation="h",
            color="count", color_continuous_scale="Blues",
            height=300, labels={"count": "Complaints", "type": ""},
        )
        fig2.update_layout(coloraxis_showscale=False)
        st.plotly_chart(fig2, use_container_width=True)
