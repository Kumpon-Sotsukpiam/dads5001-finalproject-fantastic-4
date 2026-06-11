"""
utils/db.py
-----------
Cached connection helpers for MongoDB and Snowflake.

Reads credentials from (in order of priority):
  1. Streamlit secrets (st.secrets) — used when deployed on Streamlit Cloud
  2. Environment variables / .env file   — used when running locally
"""

import os
import streamlit as st
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()


def _get_secret(key, default=None):
    """Read from st.secrets first, fall back to os.environ."""
    try:
        return st.secrets[key]
    except Exception:
        return os.getenv(key, default)


@st.cache_resource
def get_mongo_collection():
    """Return MongoDB collection (cached singleton)."""
    uri = _get_secret("MONGO_URI")
    db_name  = _get_secret("MONGO_DB",         "dads5001")
    col_name = _get_secret("MONGO_COLLECTION", "bangkok_complaints")

    client = MongoClient(uri, serverSelectionTimeoutMS=15000)
    return client[db_name][col_name]


def get_snowflake_conn():
    """
    Return a Snowflake connection.
    Used only by pipeline_snowflake.py — NOT used by the Streamlit app.
    """
    import snowflake.connector
    return snowflake.connector.connect(
        account         = _get_secret("SNOWFLAKE_ACCOUNT"),
        user            = _get_secret("SNOWFLAKE_USER"),
        password        = _get_secret("SNOWFLAKE_PASSWORD"),
        warehouse       = _get_secret("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database        = _get_secret("SNOWFLAKE_DATABASE",  "DADS5001"),
        schema          = _get_secret("SNOWFLAKE_SCHEMA",    "PUBLIC"),
        login_timeout   = 30,
        network_timeout = 30,
    )
