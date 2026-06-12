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

    # zlib wire compression: shrinks payloads over the network (helps a lot
    # for large text fields like `comment` when pulling many documents)
    client = MongoClient(uri, serverSelectionTimeoutMS=15000,
                         compressors="zlib")
    return client[db_name][col_name]


def get_snowflake_conn():
    """
    Return a Snowflake connection using key-pair authentication (no MFA).
    Supports both local (private key file path) and Streamlit Cloud
    (private key content stored in secrets).
    """
    import snowflake.connector
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    from cryptography.hazmat.backends import default_backend

    # Try to load private key — from file path first, then from secret content
    private_key_path    = _get_secret("SNOWFLAKE_PRIVATE_KEY_PATH")
    private_key_content = _get_secret("SNOWFLAKE_PRIVATE_KEY")

    if private_key_path and os.path.exists(private_key_path):
        with open(private_key_path, "rb") as f:
            pem_data = f.read()
    elif private_key_content:
        pem_data = private_key_content.encode() if isinstance(private_key_content, str) else private_key_content
    else:
        raise ValueError("No Snowflake private key found. Set SNOWFLAKE_PRIVATE_KEY_PATH or SNOWFLAKE_PRIVATE_KEY.")

    private_key = load_pem_private_key(pem_data, password=None, backend=default_backend())

    return snowflake.connector.connect(
        account         = _get_secret("SNOWFLAKE_ACCOUNT"),
        user            = _get_secret("SNOWFLAKE_USER"),
        private_key     = private_key,
        warehouse       = _get_secret("SNOWFLAKE_WAREHOUSE", "COMPUTE_WH"),
        database        = _get_secret("SNOWFLAKE_DATABASE",  "DADS5001"),
        schema          = _get_secret("SNOWFLAKE_SCHEMA",    "PUBLIC"),
        login_timeout   = 30,
        network_timeout = 30,
    )
