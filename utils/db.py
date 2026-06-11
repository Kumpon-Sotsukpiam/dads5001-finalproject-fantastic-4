"""
utils/db.py
-----------
Cached connection helpers for MongoDB and Snowflake.
Uses st.cache_resource so connections are reused across reruns.

NOTE: Snowflake connection is used only by pipeline_snowflake.py.
      The Streamlit app uses MongoDB + DuckDB for all live queries.
"""

import os
import streamlit as st
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


@st.cache_resource
def get_mongo_collection():
    """Return MongoDB collection (cached singleton)."""
    client = MongoClient(
        os.getenv("MONGO_URI"),
        serverSelectionTimeoutMS=15000,
    )
    db  = client[os.getenv("MONGO_DB", "dads5001")]
    col = db[os.getenv("MONGO_COLLECTION", "bangkok_complaints")]
    return col


def get_snowflake_conn():
    """
    Return a Snowflake connection.
    Used only by pipeline_snowflake.py — NOT used by the Streamlit app.
    """
    import snowflake.connector
    return snowflake.connector.connect(
        account       = os.getenv("SNOWFLAKE_ACCOUNT"),
        user          = os.getenv("SNOWFLAKE_USER"),
        password      = os.getenv("SNOWFLAKE_PASSWORD"),
        warehouse     = os.getenv("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database      = os.getenv("SNOWFLAKE_DATABASE", "DADS5001"),
        schema        = os.getenv("SNOWFLAKE_SCHEMA", "PUBLIC"),
        login_timeout = 30,
        network_timeout = 30,
    )
