"""
pages/2_Map.py
--------------
Geographic distribution of complaints (MongoDB -> pydeck scatter map).
"""

import streamlit as st
import pandas as pd
import pydeck as pdk
import plotly.express as px
from utils.queries import get_map_data

st.set_page_config(page_title="Map", page_icon="🗺️", layout="wide")
st.title("🗺️ Geographic Distribution")
st.caption("Source: MongoDB · GPS coordinates from Traffy Fondue reports")

# ── Sidebar filters ───────────────────────────────────────────────────────────
with st.sidebar:
    st.header("Map Filters")
    sel_month = st.selectbox(
        "Month (2025)",
        options=[None, 7, 8, 9, 10, 11, 12],
        format_func=lambda m: "All months" if m is None
            else ["","","","","","","","Jul","Aug","Sep","Oct","Nov","Dec"][m],
    )

    PROBLEM_TYPES = [
        "All", "ผิดกฎจราจร", "ถนน", "ไฟฟ้า", "ทางเท้า", "ความสะอาด",
        "อุปกรณ์ชำรุด", "เสียง", "หาบเร่แผงลอย", "ต้นไม้",
        "น้ำท่วม", "ฝุ่นควัน&กลิ่น&PM2.5",
    ]
    sel_type = st.selectbox("Problem Type", PROBLEM_TYPES)
    max_pts  = st.slider("Max points on map", 500, 5000, 3000, step=500)

# ── Load data ─────────────────────────────────────────────────────────────────
with st.spinner("Loading map data from MongoDB ..."):
    try:
        df = get_map_data(month=sel_month, problem_type=sel_type, limit=max_pts)
    except Exception as e:
        st.error("Failed to load map data: {}".format(e))
        st.stop()

if df.empty:
    st.warning("No data found for selected filters.")
    st.stop()

# ── Clean coordinates ─────────────────────────────────────────────────────────
df = df.copy()
df["latitude"]  = pd.to_numeric(df.get("latitude"),  errors="coerce")
df["longitude"] = pd.to_numeric(df.get("longitude"), errors="coerce")
df = df.dropna(subset=["latitude", "longitude"])
df = df[df["latitude"].between(13.4, 14.1) & df["longitude"].between(100.3, 101.0)]

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
# Truncate comment for tooltip to avoid render issues
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
                "finished": "#00C864",
                "in_progress": "#FFA500",
                "pending": "#C83232",
                "other": "#AAAAAA",
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
