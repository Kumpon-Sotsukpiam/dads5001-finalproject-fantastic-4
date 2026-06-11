"""
utils/queries.py
----------------
Cached data-fetching functions.

All dashboard queries use MongoDB + in-memory DuckDB aggregation.
Snowflake integration is handled separately via pipeline_snowflake.py.

Uses st.cache_data (TTL=1 hour) so repeated reruns skip re-querying.
"""

import pandas as pd
import duckdb
import streamlit as st
from utils.db import get_mongo_collection


# ── Raw data fetch from MongoDB ───────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Loading data from MongoDB ...")
def _load_all_data():
    """
    Pull all records from MongoDB (excluding embeddings).
    Cached for 1 hour — this is the base dataset for all dashboard queries.
    """
    col = get_mongo_collection()
    cursor = col.find(
        {},
        {
            "_id": 0, "embedding": 0,
            "photo": 0, "photo_after": 0,
            "problemtype_tag": 0, "type_full": 0,
            "coords": 0, "province": 0, "address": 0,
        }
    )
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return df

    # Coerce numerics
    for c in ["month", "year", "count_reopen"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("Int64")
    for c in ["star", "duration_minutes_total", "duration_minutes_inprogress",
              "duration_minutes_finished", "longitude", "latitude"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


# ── DuckDB aggregations (mimicking Snowflake tables) ─────────────────────────

@st.cache_data(ttl=3600, show_spinner="Aggregating district summary ...")
def get_district_summary():
    df = _load_all_data()
    if df.empty:
        return pd.DataFrame()
    con = duckdb.connect()
    con.register("facts", df)
    result = con.execute("""
        SELECT
            district,
            COUNT(*)                                                   AS total_tickets,
            SUM(CASE WHEN state_en = 'finished'    THEN 1 ELSE 0 END) AS finished,
            SUM(CASE WHEN state_en = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_count,
            AVG(duration_minutes_total)                                AS avg_resolution_minutes,
            AVG(star)                                                  AS avg_satisfaction
        FROM facts
        WHERE district IS NOT NULL
        GROUP BY district
        ORDER BY total_tickets DESC
    """).df()
    con.close()
    return result


@st.cache_data(ttl=3600, show_spinner="Aggregating monthly trend ...")
def get_monthly_trend():
    df = _load_all_data()
    if df.empty:
        return pd.DataFrame()
    con = duckdb.connect()
    con.register("facts", df)
    result = con.execute("""
        SELECT
            CAST(year AS INTEGER)        AS year,
            CAST(month AS INTEGER)       AS month,
            problem_type,
            COUNT(*)                     AS ticket_count,
            AVG(duration_minutes_total)  AS avg_resolution_minutes,
            AVG(star)                    AS avg_star
        FROM facts
        WHERE problem_type IS NOT NULL
          AND month IS NOT NULL
        GROUP BY year, month, problem_type
        ORDER BY year, month
    """).df()
    con.close()
    return result


@st.cache_data(ttl=3600, show_spinner="Aggregating weekly trend ...")
def get_weekly_trend():
    df = _load_all_data()
    if df.empty:
        return pd.DataFrame()
    con = duckdb.connect()
    con.register("facts", df)
    result = con.execute("""
        SELECT
            TRY_CAST(week_start AS DATE)                               AS week_start,
            COUNT(*)                                                   AS ticket_count,
            SUM(CASE WHEN state_en = 'finished' THEN 1 ELSE 0 END)    AS finished_count
        FROM facts
        WHERE week_start IS NOT NULL
          AND week_start NOT IN ('None', 'NaT', 'nan')
        GROUP BY week_start
        ORDER BY week_start
    """).df()
    con.close()
    return result


@st.cache_data(ttl=3600, show_spinner="Loading top problem types ...")
def get_top_problem_types(top_n=15):
    df = _load_all_data()
    if df.empty:
        return pd.DataFrame()
    con = duckdb.connect()
    con.register("facts", df)
    result = con.execute("""
        SELECT problem_type, COUNT(*) AS total
        FROM facts
        WHERE problem_type IS NOT NULL
        GROUP BY problem_type
        ORDER BY total DESC
        LIMIT {}
    """.format(top_n)).df()
    con.close()
    return result


@st.cache_data(ttl=3600, show_spinner="Loading resolution stats ...")
def get_resolution_stats():
    df = _load_all_data()
    if df.empty:
        return pd.DataFrame()
    con = duckdb.connect()
    con.register("facts", df)
    result = con.execute("""
        SELECT
            problem_type,
            AVG(duration_minutes_total) / 60.0 AS avg_hours,
            COUNT(*)                            AS ticket_count
        FROM facts
        WHERE state_en = 'finished'
          AND duration_minutes_total IS NOT NULL
          AND problem_type IS NOT NULL
        GROUP BY problem_type
        ORDER BY avg_hours DESC
        LIMIT 20
    """).df()
    con.close()
    return result


@st.cache_data(ttl=3600, show_spinner="Loading district x problem heatmap ...")
def get_district_problem_heatmap():
    df = _load_all_data()
    if df.empty:
        return pd.DataFrame()
    con = duckdb.connect()
    con.register("facts", df)
    result = con.execute("""
        SELECT district, problem_type, COUNT(*) AS ticket_count
        FROM facts
        WHERE district IS NOT NULL AND problem_type IS NOT NULL
        GROUP BY district, problem_type
    """).df()
    con.close()
    return result


# ── MongoDB direct queries ────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Fetching sample from MongoDB ...")
def get_mongo_sample(limit=2000):
    col = get_mongo_collection()
    # Inclusion-only projection (mixed inclusion/exclusion not allowed in MongoDB)
    cursor = col.find(
        {},
        {
            "_id": 0,
            "comment": 1, "problem_type": 1, "district": 1,
            "subdistrict": 1, "state_en": 1, "timestamp": 1,
            "duration_minutes_total": 1, "star": 1, "ticket_id": 1,
            "longitude": 1, "latitude": 1, "address": 1,
            "month": 1, "year": 1,
        },
        limit=limit,
    )
    df = pd.DataFrame(list(cursor))
    if df.empty:
        return df
    if "month" in df.columns:
        df["month"] = pd.to_numeric(df["month"], errors="coerce").fillna(0).astype(int)
    return df


@st.cache_data(ttl=3600, show_spinner="Loading map data ...")
def get_map_data(month=None, problem_type=None, limit=5000):
    col  = get_mongo_collection()
    filt = {}
    if month:
        filt["month"] = int(month)
    if problem_type and problem_type != "All":
        filt["problem_type"] = problem_type

    cursor = col.find(
        filt,
        {
            "_id": 0, "ticket_id": 1, "latitude": 1, "longitude": 1,
            "problem_type": 1, "district": 1, "state_en": 1, "comment": 1,
        },
        limit=limit,
    )
    return pd.DataFrame(list(cursor))


# ── Ad-hoc DuckDB filter ──────────────────────────────────────────────────────

def duckdb_filter(df, sql):
    """Run an ad-hoc DuckDB query on a pandas DataFrame registered as 'df'."""
    con = duckdb.connect()
    con.register("df", df)
    result = con.execute(sql).df()
    con.close()
    return result
