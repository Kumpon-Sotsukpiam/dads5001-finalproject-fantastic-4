"""
utils/queries.py
----------------
Cached data-fetching functions with a TWO-TIER strategy:

  Tier 1 (fast path) : local Parquet snapshot  data_cache/clean_df.parquet
                       created by `python pipeline_mongo.py` — loads in
                       sub-seconds with ZERO network. Aggregations run
                       locally with DuckDB.
  Tier 2 (fallback)  : MongoDB server-side aggregation pipelines — used
                       when the Parquet file is absent. Only small summary
                       tables travel over the network.

Uses st.cache_data (TTL=1 hour) so repeated reruns skip re-querying.
"""

import os

import duckdb
import pandas as pd
import streamlit as st

from utils.db import get_mongo_collection

_PARQUET_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data_cache", "clean_df.parquet",
)


# ── Shared helpers ────────────────────────────────────────────────────────────

def _delist(df):
    """Convert unhashable list values (rogue array fields) to joined strings."""
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].map(
                lambda v: ", ".join(map(str, v)) if isinstance(v, list) else v
            )
    return df


def _shrink(df, cat_cols=(), f32_cols=(), i16_cols=()):
    """Reduce memory: repeated strings -> category, float64 -> float32."""
    for c in cat_cols:
        if c in df.columns:
            try:
                df[c] = df[c].astype("category")
            except TypeError:
                pass
    for c in f32_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    for c in i16_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int16")
    return df


def _agg(pipeline):
    """Run a MongoDB aggregation pipeline and return a DataFrame."""
    col = get_mongo_collection()
    return _delist(pd.DataFrame(list(col.aggregate(pipeline, allowDiskUse=True))))


def _duck(df, sql):
    """Run DuckDB SQL over a DataFrame registered as `df`."""
    con = duckdb.connect()
    con.register("df", df)
    out = con.execute(sql).df()
    con.close()
    return out


# ── Tier 1: local Parquet snapshot ────────────────────────────────────────────

def _local_available():
    return os.path.exists(_PARQUET_PATH)


@st.cache_data(ttl=3600, show_spinner="Loading local data cache ...", max_entries=1)
def _load_local():
    """Load the Parquet snapshot (sub-second, no network)."""
    df = pd.read_parquet(_PARQUET_PATH)
    if "month" in df.columns:
        df["month"] = pd.to_numeric(df["month"], errors="coerce").fillna(0).astype(int)
    return _shrink(
        df,
        cat_cols=("district", "subdistrict", "problem_type", "state_en"),
        f32_cols=("star", "duration_minutes_total", "longitude", "latitude"),
    )


# ── Aggregations (local DuckDB first, MongoDB pipeline fallback) ──────────────

@st.cache_data(ttl=3600, show_spinner="Aggregating district summary ...", max_entries=2)
def get_district_summary():
    if _local_available():
        return _duck(_load_local(), """
            SELECT district,
                   COUNT(*)                                                   AS total_tickets,
                   SUM(CASE WHEN state_en = 'finished'    THEN 1 ELSE 0 END)  AS finished,
                   SUM(CASE WHEN state_en = 'in_progress' THEN 1 ELSE 0 END)  AS in_progress_count,
                   AVG(duration_minutes_total)                                AS avg_resolution_minutes,
                   AVG(star)                                                  AS avg_satisfaction
            FROM df WHERE district IS NOT NULL
            GROUP BY district ORDER BY total_tickets DESC
        """)
    df = _agg([
        {"$match": {"district": {"$ne": None}}},
        {"$group": {
            "_id": "$district",
            "total_tickets":          {"$sum": 1},
            "finished":               {"$sum": {"$cond": [{"$eq": ["$state_en", "finished"]}, 1, 0]}},
            "in_progress_count":      {"$sum": {"$cond": [{"$eq": ["$state_en", "in_progress"]}, 1, 0]}},
            "avg_resolution_minutes": {"$avg": "$duration_minutes_total"},
            "avg_satisfaction":       {"$avg": "$star"},
        }},
        {"$sort": {"total_tickets": -1}},
    ])
    return df if df.empty else df.rename(columns={"_id": "district"})


@st.cache_data(ttl=3600, show_spinner="Aggregating monthly trend ...", max_entries=2)
def get_monthly_trend():
    if _local_available():
        return _duck(_load_local(), """
            SELECT CAST(year AS INTEGER)  AS year,
                   CAST(month AS INTEGER) AS month,
                   district,
                   problem_type,
                   COUNT(*)                                                  AS ticket_count,
                   SUM(CASE WHEN state_en = 'finished' THEN 1 ELSE 0 END)    AS finished_count,
                   AVG(duration_minutes_total)                               AS avg_resolution_minutes,
                   AVG(star)                                                 AS avg_star,
                   SUM(star)                                                 AS star_sum,
                   COUNT(star)                                               AS star_count
            FROM df
            WHERE problem_type IS NOT NULL AND month IS NOT NULL
            GROUP BY 1, 2, 3, 4
            ORDER BY 1, 2
        """)
    df = _agg([
        {"$match": {"problem_type": {"$ne": None}, "month": {"$ne": None}}},
        {"$group": {
            "_id": {"year": "$year", "month": "$month",
                    "district": "$district", "problem_type": "$problem_type"},
            "ticket_count":           {"$sum": 1},
            "finished_count":         {"$sum": {"$cond": [{"$eq": ["$state_en", "finished"]}, 1, 0]}},
            "avg_resolution_minutes": {"$avg": "$duration_minutes_total"},
            "avg_star":               {"$avg": "$star"},
            "star_sum":               {"$sum": "$star"},
            "star_count":             {"$sum": {"$cond": [
                {"$in": [{"$type": "$star"}, ["double", "int", "long", "decimal"]]}, 1, 0]}},
        }},
        {"$sort": {"_id.year": 1, "_id.month": 1}},
    ])
    if df.empty:
        return df
    df["year"]         = df["_id"].apply(lambda d: d.get("year"))
    df["month"]        = df["_id"].apply(lambda d: d.get("month"))
    df["district"]     = df["_id"].apply(lambda d: d.get("district"))
    df["problem_type"] = df["_id"].apply(lambda d: d.get("problem_type"))
    df = df.drop(columns=["_id"])
    df["year"]  = pd.to_numeric(df["year"],  errors="coerce").astype("Int64")
    df["month"] = pd.to_numeric(df["month"], errors="coerce").astype("Int64")
    return _shrink(df, cat_cols=("district", "problem_type"))


@st.cache_data(ttl=3600, show_spinner="Aggregating weekly trend ...", max_entries=2)
def get_weekly_trend():
    if _local_available():
        return _duck(_load_local(), """
            SELECT week_start,
                   COUNT(*)                                               AS ticket_count,
                   SUM(CASE WHEN state_en = 'finished' THEN 1 ELSE 0 END) AS finished_count
            FROM df
            WHERE week_start IS NOT NULL
              AND week_start NOT IN ('None', 'NaT', 'nan')
            GROUP BY week_start ORDER BY week_start
        """)
    df = _agg([
        {"$match": {"week_start": {"$nin": [None, "None", "NaT", "nan"]}}},
        {"$group": {
            "_id": "$week_start",
            "ticket_count":   {"$sum": 1},
            "finished_count": {"$sum": {"$cond": [{"$eq": ["$state_en", "finished"]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ])
    return df if df.empty else df.rename(columns={"_id": "week_start"})


@st.cache_data(ttl=3600, show_spinner="Loading top problem types ...", max_entries=2)
def get_top_problem_types(top_n=15):
    if _local_available():
        return _duck(_load_local(), """
            SELECT problem_type, COUNT(*) AS total
            FROM df WHERE problem_type IS NOT NULL
            GROUP BY problem_type ORDER BY total DESC LIMIT {}
        """.format(int(top_n)))
    df = _agg([
        {"$match": {"problem_type": {"$ne": None}}},
        {"$group": {"_id": "$problem_type", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": int(top_n)},
    ])
    return df if df.empty else df.rename(columns={"_id": "problem_type"})


@st.cache_data(ttl=3600, show_spinner="Loading resolution stats ...", max_entries=2)
def get_resolution_stats():
    if _local_available():
        return _duck(_load_local(), """
            SELECT problem_type,
                   AVG(duration_minutes_total) / 60.0 AS avg_hours,
                   COUNT(*)                           AS ticket_count
            FROM df
            WHERE state_en = 'finished'
              AND duration_minutes_total IS NOT NULL
              AND problem_type IS NOT NULL
            GROUP BY problem_type ORDER BY avg_hours DESC LIMIT 20
        """)
    df = _agg([
        {"$match": {
            "state_en": "finished",
            "duration_minutes_total": {"$ne": None},
            "problem_type": {"$ne": None},
        }},
        {"$group": {
            "_id": "$problem_type",
            "avg_minutes":  {"$avg": "$duration_minutes_total"},
            "ticket_count": {"$sum": 1},
        }},
        {"$sort": {"avg_minutes": -1}},
        {"$limit": 20},
    ])
    if df.empty:
        return df
    df = df.rename(columns={"_id": "problem_type"})
    df["avg_hours"] = pd.to_numeric(df["avg_minutes"], errors="coerce") / 60.0
    return df.drop(columns=["avg_minutes"])


@st.cache_data(ttl=3600, show_spinner="Loading district x problem heatmap ...", max_entries=2)
def get_district_problem_heatmap():
    if _local_available():
        return _duck(_load_local(), """
            SELECT district, problem_type, COUNT(*) AS ticket_count
            FROM df
            WHERE district IS NOT NULL AND problem_type IS NOT NULL
            GROUP BY district, problem_type
        """)
    df = _agg([
        {"$match": {"district": {"$ne": None}, "problem_type": {"$ne": None}}},
        {"$group": {
            "_id": {"district": "$district", "problem_type": "$problem_type"},
            "ticket_count": {"$sum": 1},
        }},
    ])
    if df.empty:
        return df
    df["district"]     = df["_id"].apply(lambda d: d.get("district"))
    df["problem_type"] = df["_id"].apply(lambda d: d.get("problem_type"))
    return df.drop(columns=["_id"])


# ── Record-level queries (Explorer / Map) ─────────────────────────────────────

_SAMPLE_COLS = ["ticket_id", "problem_type", "district", "subdistrict",
                "state_en", "timestamp", "duration_minutes_total", "star",
                "longitude", "latitude", "month", "year", "comment"]


@st.cache_data(ttl=3600, show_spinner="Fetching records ...", max_entries=2)
def get_mongo_sample(month_min=None, month_max=None, limit=0):
    """Records for the Explorer page (month-filtered, comment truncated)."""
    if _local_available():
        df = _load_local()
        if month_min is not None and month_max is not None:
            df = df[df["month"].between(int(month_min), int(month_max))]
        df = df[[c for c in _SAMPLE_COLS if c in df.columns]].copy()
        if limit and limit > 0:
            df = df.head(int(limit))
        return df.reset_index(drop=True)

    col = get_mongo_collection()
    match = {}
    if month_min is not None and month_max is not None:
        match["month"] = {"$gte": int(month_min), "$lte": int(month_max)}
    pipeline = [
        {"$match": match},
        {"$project": {
            "_id": 0,
            "ticket_id": 1, "problem_type": 1, "district": 1,
            "subdistrict": 1, "state_en": 1, "timestamp": 1,
            "duration_minutes_total": 1, "star": 1,
            "longitude": 1, "latitude": 1,
            "month": 1, "year": 1,
            "comment": {"$substrCP": [{"$ifNull": ["$comment", ""]}, 0, 300]},
        }},
    ]
    if limit and limit > 0:
        pipeline.append({"$limit": int(limit)})
    df = _delist(pd.DataFrame(list(col.aggregate(pipeline, allowDiskUse=True))))
    if df.empty:
        return df
    if "month" in df.columns:
        df["month"] = pd.to_numeric(df["month"], errors="coerce").fillna(0).astype(int)
    return _shrink(
        df,
        cat_cols=("district", "subdistrict", "problem_type", "state_en"),
        f32_cols=("star", "duration_minutes_total", "longitude", "latitude"),
    )


@st.cache_data(ttl=3600, show_spinner="Loading map data ...", max_entries=2)
def get_map_data(month=None, problem_type=None, limit=0):
    """Geo records for the Map page (comment truncated for tooltips)."""
    if _local_available():
        df = _load_local()
        df = df[df["latitude"].notna() & df["longitude"].notna()]
        if month:
            df = df[df["month"] == int(month)]
        if problem_type and problem_type != "All":
            df = df[df["problem_type"] == problem_type]
        keep = ["ticket_id", "latitude", "longitude", "problem_type",
                "district", "state_en", "month", "comment"]
        df = df[[c for c in keep if c in df.columns]].copy()
        if "comment" in df.columns:
            df["comment"] = df["comment"].fillna("").astype(str).str[:150]
        if limit and limit > 0:
            df = df.head(int(limit))
        return df.reset_index(drop=True)

    col = get_mongo_collection()
    match = {"latitude": {"$ne": None}, "longitude": {"$ne": None}}
    if month:
        match["month"] = int(month)
    if problem_type and problem_type != "All":
        match["problem_type"] = problem_type
    pipeline = [
        {"$match": match},
        {"$project": {
            "_id": 0, "ticket_id": 1, "latitude": 1, "longitude": 1,
            "problem_type": 1, "district": 1, "state_en": 1, "month": 1,
            "comment": {"$substrCP": [{"$ifNull": ["$comment", ""]}, 0, 150]},
        }},
    ]
    if limit and limit > 0:
        pipeline.append({"$limit": int(limit)})
    df = _delist(pd.DataFrame(list(col.aggregate(pipeline, allowDiskUse=True))))
    if df.empty:
        return df
    return _shrink(
        df,
        cat_cols=("district", "problem_type", "state_en"),
        f32_cols=("latitude", "longitude"),
        i16_cols=("month",),
    )


# ── Ad-hoc DuckDB filter ──────────────────────────────────────────────────────

def duckdb_filter(df, sql):
    """Run an ad-hoc DuckDB query on a pandas DataFrame registered as 'df'."""
    return _duck(df, sql)
