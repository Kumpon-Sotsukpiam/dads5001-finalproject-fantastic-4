"""
pipeline_mongo.py
-----------------
Step 1 of the data pipeline:
  Dataset (month 7-12) -> Pandas + DuckDB -> MongoDB (raw data)

Run once to populate MongoDB Atlas before launching the Streamlit app.

Usage:
    pip install -r requirements.txt
    python pipeline_mongo.py
"""

import os
import pandas as pd
import duckdb
from pymongo import MongoClient, UpdateOne
from pymongo.errors import BulkWriteError
from dotenv import load_dotenv

load_dotenv()

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR      = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dataset")
TARGET_MONTHS = ["07", "08", "09", "10", "11", "12"]
TARGET_FILES  = [
    os.path.join(DATA_DIR, "bangkok_2025-{}.csv".format(m)) for m in TARGET_MONTHS
]

MONGO_URI        = os.getenv("MONGO_URI")
MONGO_DB         = os.getenv("MONGO_DB", "dads5001")
MONGO_COLLECTION = os.getenv("MONGO_COLLECTION", "bangkok_complaints")

BATCH_SIZE = 512


# ── 1. Load with Pandas ───────────────────────────────────────────────────────
def load_raw(files):
    dfs = []
    for fp in files:
        if not os.path.exists(fp):
            print("[SKIP] Not found: {}".format(fp))
            continue
        df = pd.read_csv(fp, low_memory=False)
        df.columns = [c.strip().lstrip("﻿").lstrip("​") for c in df.columns]
        df["source_file"] = os.path.basename(fp)
        dfs.append(df)
        print("[READ] {} -> {:,} rows".format(os.path.basename(fp), len(df)))
    if not dfs:
        raise RuntimeError("No CSV files loaded. Check dataset/ directory.")
    return pd.concat(dfs, ignore_index=True)


# ── 2. Clean & enrich with DuckDB ─────────────────────────────────────────────
def clean_with_duckdb(df):
    con = duckdb.connect()
    con.register("raw", df)

    cleaned = con.execute("""
        SELECT
            ticket_id,
            SPLIT_PART(CAST(type AS VARCHAR), ' -> ', 1)        AS problem_type,
            CAST(type AS VARCHAR)                               AS type_full,
            district,
            subdistrict,
            province,
            address,
            state,
            comment,
            coords,
            TRY_CAST(star AS DOUBLE)                            AS star,
            TRY_CAST(count_reopen AS INTEGER)                   AS count_reopen,
            TRY_CAST(duration_minutes_total AS DOUBLE)          AS duration_minutes_total,
            TRY_CAST(duration_minutes_inprogress AS DOUBLE)     AS duration_minutes_inprogress,
            TRY_CAST(duration_minutes_finished AS DOUBLE)       AS duration_minutes_finished,
            TRY_CAST(timestamp AS TIMESTAMP)                    AS timestamp,
            TRY_CAST(timestamp_inprogress AS TIMESTAMP)         AS timestamp_inprogress,
            TRY_CAST(timestamp_finished AS TIMESTAMP)           AS timestamp_finished,
            TRY_CAST(last_activity AS TIMESTAMP)                AS last_activity,
            photo,
            photo_after,
            problemtype_tag,
            source_file,
            MONTH(TRY_CAST(timestamp AS TIMESTAMP))             AS month,
            YEAR(TRY_CAST(timestamp AS TIMESTAMP))              AS year,
            DATE_TRUNC('week', TRY_CAST(timestamp AS TIMESTAMP)) AS week_start,
            CASE
                WHEN state = 'เสร็จสิ้น'        THEN 'finished'
                WHEN state = 'กำลังดำเนินการ'   THEN 'in_progress'
                WHEN state = 'รอรับเรื่อง'       THEN 'pending'
                ELSE 'other'
            END                                                 AS state_en,
            TRY_CAST(SPLIT_PART(CAST(coords AS VARCHAR), ',', 1) AS DOUBLE) AS longitude,
            TRY_CAST(SPLIT_PART(CAST(coords AS VARCHAR), ',', 2) AS DOUBLE) AS latitude
        FROM raw
        WHERE ticket_id IS NOT NULL
          AND type IS NOT NULL
    """).df()

    con.close()
    print("[DUCKDB] Cleaned -> {:,} rows".format(len(cleaned)))
    return cleaned


# ── 3. Upsert to MongoDB ──────────────────────────────────────────────────────
def upsert_to_mongo(df, collection):
    # Convert timestamps to strings to avoid BSON issues
    for col in ["timestamp", "timestamp_inprogress", "timestamp_finished",
                "last_activity", "week_start"]:
        if col in df.columns:
            df[col] = df[col].astype(str).replace("NaT", None).replace("None", None)

    records = df.where(pd.notnull(df), None).to_dict(orient="records")

    total = 0
    for i in range(0, len(records), BATCH_SIZE):
        batch = records[i: i + BATCH_SIZE]
        ops = [
            UpdateOne({"ticket_id": r["ticket_id"]}, {"$set": r}, upsert=True)
            for r in batch
        ]
        try:
            result = collection.bulk_write(ops, ordered=False)
            total += result.upserted_count + result.modified_count
        except BulkWriteError as bwe:
            print("[WARN] Partial error: {} inserted".format(
                bwe.details.get("nInserted", 0)))
        print("  batch {}: {:,}/{:,}".format(
            i // BATCH_SIZE + 1, min(i + BATCH_SIZE, len(records)), len(records)))

    print("[MONGO] Done. Upserted/modified: {:,}".format(total))


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 60)
    print("Bangkok Complaints Pipeline -> MongoDB")
    print("=" * 60)

    raw_df   = load_raw(TARGET_FILES)
    clean_df = clean_with_duckdb(raw_df)

    print("[MONGO] Connecting ...")
    client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=15000)
    col    = client[MONGO_DB][MONGO_COLLECTION]

    # Indexes
    col.create_index("ticket_id", unique=True)
    col.create_index("district")
    col.create_index("problem_type")
    col.create_index("state_en")
    col.create_index("month")
    # Text index for RAG fallback search
    col.create_index([("comment", "text"), ("problem_type", "text"),
                      ("district", "text")])

    upsert_to_mongo(clean_df, col)
    client.close()
    print("[DONE] Pipeline complete. {:,} records in MongoDB.".format(len(clean_df)))
