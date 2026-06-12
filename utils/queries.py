"""
utils/queries.py
----------------
Cached data-fetching functions.

Dashboard aggregations run SERVER-SIDE as MongoDB aggregation pipelines —
only small summary tables (hundreds of rows) travel over the network,
instead of all 168K raw documents. This keeps the app fast even on a
slow connection or a throttled Atlas free tier.

DuckDB + pandas are still used for in-app filtering (Explorer page) and
in the ETL pipelines (pipeline_mongo.py / pipeline_snowflake.py).

Uses st.cache_data (TTL=1 hour) so repeated reruns skip re-querying.
"""

import pandas as pd
import duckdb
import streamlit as st
from utils.db import get_mongo_collection


def _delist(df):
    """
    Some MongoDB documents may store fields as arrays (e.g. problem_type).
    Lists are unhashable — they crash groupby/isin/astype('category') with
    "TypeError: unhashable type: 'list'". Convert them to joined strings.
    """
    for c in df.columns:
        if df[c].dtype == object:
            df[c] = df[c].map(
                lambda v: ", ".join(map(str, v)) if isinstance(v, list) else v
            )
    return df


def _agg(pipeline):
    """Run an aggregation pipeline and return a DataFrame."""
    col = get_mongo_collection()
    return _delist(pd.DataFrame(list(col.aggregate(pipeline, allowDiskUse=True))))


def _shrink(df, cat_cols=(), f32_cols=(), i16_cols=()):
    """
    Reduce DataFrame memory footprint WITHOUT losing data:
    - repeated strings (district names, problem types) -> category dtype
    - float64 -> float32, month/year -> int16
    Typical saving: 50-70% — same rows, same values, smaller cache.
    """
    for c in cat_cols:
        if c in df.columns:
            try:
                df[c] = df[c].astype("category")
            except TypeError:
                pass  # column contains unhashable values — leave as-is
    for c in f32_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").astype("float32")
    for c in i16_cols:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype("int16")
    return df


# ── Server-side aggregations (MongoDB pipelines) ──────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Aggregating district summary ...", persist="disk")
def get_district_summary():
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
    if df.empty:
        return df
    return df.rename(columns={"_id": "district"})


@st.cache_data(ttl=3600, show_spinner="Aggregating monthly trend ...", persist="disk")
def get_monthly_trend():
    df = _agg([
        {"$match": {"problem_type": {"$ne": None}, "month": {"$ne": None}}},
        {"$group": {
            "_id": {"year": "$year", "month": "$month",
                    "district": "$district", "problem_type": "$problem_type"},
            "ticket_count":           {"$sum": 1},
            "finished_count":         {"$sum": {"$cond": [{"$eq": ["$state_en", "finished"]}, 1, 0]}},
            "avg_resolution_minutes": {"$avg": "$duration_minutes_total"},
            "avg_star":               {"$avg": "$star"},
            # star_sum / star_count enable a correctly WEIGHTED overall
            # satisfaction average for any filter combination
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


@st.cache_data(ttl=3600, show_spinner="Aggregating weekly trend ...", persist="disk")
def get_weekly_trend():
    df = _agg([
        {"$match": {"week_start": {"$nin": [None, "None", "NaT", "nan"]}}},
        {"$group": {
            "_id": "$week_start",
            "ticket_count":   {"$sum": 1},
            "finished_count": {"$sum": {"$cond": [{"$eq": ["$state_en", "finished"]}, 1, 0]}},
        }},
        {"$sort": {"_id": 1}},
    ])
    if df.empty:
        return df
    return df.rename(columns={"_id": "week_start"})


@st.cache_data(ttl=3600, show_spinner="Loading top problem types ...", persist="disk")
def get_top_problem_types(top_n=15):
    df = _agg([
        {"$match": {"problem_type": {"$ne": None}}},
        {"$group": {"_id": "$problem_type", "total": {"$sum": 1}}},
        {"$sort": {"total": -1}},
        {"$limit": int(top_n)},
    ])
    if df.empty:
        return df
    return df.rename(columns={"_id": "problem_type"})


@st.cache_data(ttl=3600, show_spinner="Loading resolution stats ...", persist="disk")
def get_resolution_stats():
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


@st.cache_data(ttl=3600, show_spinner="Loading district x problem heatmap ...", persist="disk")
def get_district_problem_heatmap():
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


# ── MongoDB record-level queries (Explorer / Map) ─────────────────────────────

@st.cache_data(ttl=3600, show_spinner="Fetching data from MongoDB ...",
               persist="disk", max_entries=2)
def get_mongo_sample(month_min=None, month_max=None, limit=0):
    """
    Load records for the Explorer page.
    Filters by month SERVER-SIDE and truncates `comment` to 300 chars in the
    projection — both drastically cut network transfer.
    """
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


@st.cache_data(ttl=3600, show_spinner="Loading map data ...",
               persist="disk", max_entries=2)
def get_map_data(month=None, problem_type=None, limit=0):
    """
    Load map data. `comment` is truncated to 150 chars server-side (it is
    only used in the hover tooltip) — cuts transfer size by ~80%.
    """
    col  = get_mongo_collection()
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
    con = duckdb.connect()
    con.register("df", df)
    result = con.execute(sql).df()
    con.close()
    return result
