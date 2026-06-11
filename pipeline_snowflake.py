"""
pipeline_snowflake.py
---------------------
Step 2 of the data pipeline:
  MongoDB (raw data) -> Snowflake (analytics warehouse)

Reads records from MongoDB and loads aggregated + fact tables
into Snowflake for analytics queries used by the Streamlit dashboard.

Run after pipeline_mongo.py.

Usage:
    python pipeline_snowflake.py
"""

import os
import pandas as pd
import duckdb
import snowflake.connector
from snowflake.connector.pandas_tools import write_pandas
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
MONGO_URI        = os.getenv("MONGO_URI")
MONGO_DB         = os.getenv("MONGO_DB", "dads5001")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "bangkok_complaints")

SF_ACCOUNT          = os.getenv("SNOWFLAKE_ACCOUNT")
SF_USER             = os.getenv("SNOWFLAKE_USER")
SF_PRIVATE_KEY_PATH = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH")
SF_WAREHOUSE        = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
SF_DATABASE         = os.getenv("SNOWFLAKE_DATABASE", "DADS5001")
SF_SCHEMA           = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC")


# ── 1. Pull from MongoDB ──────────────────────────────────────────────────────
PROJECTION = {"_id": 0, "embedding": 0}


def pull_from_mongo():
    print("[MONGO] Fetching records ...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    col    = client[MONGO_DB][MONGO_COLLECTION]
    cursor = col.find({}, PROJECTION)
    df     = pd.DataFrame(list(cursor))
    client.close()
    print("[MONGO] Fetched {:,} records".format(len(df)))
    return df


# ── 2. Build aggregates with DuckDB ──────────────────────────────────────────
def build_aggregates(df):
    # Ensure numeric types
    for c in ["duration_minutes_total", "star", "count_reopen", "month", "year"]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    con = duckdb.connect()
    con.register("facts", df)

    agg_district_type = con.execute("""
        SELECT
            CAST(year AS INTEGER)                               AS year,
            CAST(month AS INTEGER)                              AS month,
            district,
            problem_type,
            state_en,
            COUNT(*)                                            AS ticket_count,
            AVG(duration_minutes_total)                         AS avg_resolution_minutes,
            AVG(star)                                           AS avg_star,
            SUM(COALESCE(count_reopen, 0))                      AS total_reopens
        FROM facts
        WHERE district IS NOT NULL
          AND problem_type IS NOT NULL
        GROUP BY year, month, district, problem_type, state_en
        ORDER BY year, month, district
    """).df()

    agg_weekly = con.execute("""
        SELECT
            CAST(year AS INTEGER)                               AS year,
            CAST(EXTRACT(WEEK FROM TRY_CAST(week_start AS DATE)) AS INTEGER) AS week_num,
            TRY_CAST(week_start AS DATE)                        AS week_start,
            problem_type,
            COUNT(*)                                            AS ticket_count,
            SUM(CASE WHEN state_en = 'finished' THEN 1 ELSE 0 END) AS finished_count
        FROM facts
        WHERE week_start IS NOT NULL
          AND week_start != 'NaT'
          AND week_start != 'None'
        GROUP BY year, week_num, week_start, problem_type
        ORDER BY year, week_start
    """).df()

    agg_district_summary = con.execute("""
        SELECT
            district,
            COUNT(*)                                                  AS total_tickets,
            SUM(CASE WHEN state_en = 'finished'    THEN 1 ELSE 0 END) AS finished,
            SUM(CASE WHEN state_en = 'in_progress' THEN 1 ELSE 0 END) AS in_progress_count,
            AVG(duration_minutes_total)                               AS avg_resolution_minutes,
            AVG(star)                                                 AS avg_satisfaction
        FROM facts
        GROUP BY district
        ORDER BY total_tickets DESC
    """).df()

    con.close()
    return {
        "AGG_DISTRICT_TYPE":    agg_district_type,
        "AGG_WEEKLY":           agg_weekly,
        "AGG_DISTRICT_SUMMARY": agg_district_summary,
    }


# ── 3. Snowflake connection (key-pair auth) ───────────────────────────────────
def get_snowflake_conn():
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.backends import default_backend

    key_path = SF_PRIVATE_KEY_PATH
    if not key_path or not os.path.exists(key_path):
        raise FileNotFoundError(
            "Private key not found at: {}\n"
            "Set SNOWFLAKE_PRIVATE_KEY_PATH in .env".format(key_path)
        )
    with open(key_path, "rb") as f:
        private_key = load_pem_private_key(f.read(), password=None, backend=default_backend())

    return snowflake.connector.connect(
        account     = SF_ACCOUNT,
        user        = SF_USER,
        private_key = private_key,
        warehouse   = SF_WAREHOUSE,
        database    = SF_DATABASE,
        schema      = SF_SCHEMA,
    )


# ── 4. DDL ────────────────────────────────────────────────────────────────────
DDL_STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS BANGKOK_COMPLAINTS (
        TICKET_ID              VARCHAR(50),
        PROBLEM_TYPE           VARCHAR(200),
        TYPE_FULL              VARCHAR(500),
        DISTRICT               VARCHAR(200),
        SUBDISTRICT            VARCHAR(200),
        STATE_EN               VARCHAR(50),
        COMMENT                VARCHAR(2000),
        STAR                   FLOAT,
        COUNT_REOPEN           INTEGER,
        DURATION_MINUTES_TOTAL FLOAT,
        LONGITUDE              FLOAT,
        LATITUDE               FLOAT,
        MONTH                  INTEGER,
        YEAR                   INTEGER,
        TIMESTAMP              VARCHAR(50),
        SOURCE_FILE            VARCHAR(100)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS AGG_DISTRICT_TYPE (
        YEAR                    INTEGER,
        MONTH                   INTEGER,
        DISTRICT                VARCHAR(200),
        PROBLEM_TYPE            VARCHAR(200),
        STATE_EN                VARCHAR(50),
        TICKET_COUNT            INTEGER,
        AVG_RESOLUTION_MINUTES  FLOAT,
        AVG_STAR                FLOAT,
        TOTAL_REOPENS           INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS AGG_WEEKLY (
        YEAR            INTEGER,
        WEEK_NUM        INTEGER,
        WEEK_START      VARCHAR(10),
        PROBLEM_TYPE    VARCHAR(200),
        TICKET_COUNT    INTEGER,
        FINISHED_COUNT  INTEGER
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS AGG_DISTRICT_SUMMARY (
        DISTRICT                VARCHAR(200),
        TOTAL_TICKETS           INTEGER,
        FINISHED                INTEGER,
        IN_PROGRESS_COUNT       INTEGER,
        AVG_RESOLUTION_MINUTES  FLOAT,
        AVG_SATISFACTION        FLOAT
    )
    """,
]


def prep_df_for_snowflake(df):
    """Uppercase columns, convert types for write_pandas compatibility."""
    df = df.copy()
    df.columns = [c.upper() for c in df.columns]
    # Convert all datetime columns to ISO date strings
    # (write_pandas serialises them as microsecond integers which Snowflake rejects)
    for col in df.columns:
        if hasattr(df[col], "dt") and hasattr(df[col].dt, "strftime"):
            try:
                df[col] = df[col].dt.strftime("%Y-%m-%d").where(df[col].notna(), None)
                continue
            except Exception:
                pass
        if df[col].dtype == object:
            df[col] = df[col].where(df[col].notna(), None)
    return df


def load_to_snowflake(conn, df, table_name):
    """Truncate table and bulk-load DataFrame via write_pandas."""
    cur = conn.cursor()
    cur.execute("TRUNCATE TABLE IF EXISTS {}".format(table_name))
    cur.close()

    df_up = prep_df_for_snowflake(df)
    success, n_chunks, n_rows, _ = write_pandas(
        conn, df_up, table_name,
        database=SF_DATABASE,
        schema=SF_SCHEMA,
        auto_create_table=False,
        overwrite=False,
        quote_identifiers=False,
    )
    print("  [{}] loaded {:,} rows (success={})".format(table_name, n_rows, success))


# ── 5. Fact table ─────────────────────────────────────────────────────────────
FACT_COLS = [
    "ticket_id", "problem_type", "type_full", "district", "subdistrict",
    "state_en", "comment", "star", "count_reopen", "duration_minutes_total",
    "longitude", "latitude", "month", "year", "timestamp", "source_file",
]


def load_facts(conn, df):
    available = [c for c in FACT_COLS if c in df.columns]
    sub = df[available].copy()
    sub["comment"]  = sub["comment"].fillna("").astype(str).str[:2000]
    sub["timestamp"] = sub["timestamp"].astype(str).where(sub["timestamp"].notna(), None)
    # Coerce numerics
    for col in ["star", "duration_minutes_total", "longitude", "latitude"]:
        if col in sub.columns:
            sub[col] = pd.to_numeric(sub[col], errors="coerce")
    for col in ["count_reopen", "month", "year"]:
        if col in sub.columns:
            sub[col] = pd.to_numeric(sub[col], errors="coerce").astype("Int64")
    load_to_snowflake(conn, sub, "BANGKOK_COMPLAINTS")


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Bangkok Complaints Pipeline -> Snowflake")
    print("=" * 60)

    df   = pull_from_mongo()
    aggs = build_aggregates(df)

    print("[SNOWFLAKE] Connecting ...")
    conn = get_snowflake_conn()
    cur  = conn.cursor()

    # Ensure DB/schema active
    cur.execute("USE DATABASE {}".format(SF_DATABASE))
    cur.execute("USE SCHEMA {}".format(SF_SCHEMA))
    cur.execute("USE WAREHOUSE {}".format(SF_WAREHOUSE))

    for ddl in DDL_STATEMENTS:
        cur.execute(ddl)
    conn.commit()
    print("[SNOWFLAKE] Tables ready")
    cur.close()

    print("[SNOWFLAKE] Loading BANGKOK_COMPLAINTS ...")
    load_facts(conn, df)

    for table_name, agg_df in aggs.items():
        print("[SNOWFLAKE] Loading {} ({:,} rows) ...".format(table_name, len(agg_df)))
        load_to_snowflake(conn, agg_df, table_name)

    conn.commit()
    conn.close()
    print("[DONE] Snowflake pipeline complete.")
