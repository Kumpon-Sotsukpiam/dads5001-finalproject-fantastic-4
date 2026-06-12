"""
benchmark_db.py — pinpoint where the slowness is.
Run:  python benchmark_db.py
"""

import os
import time
from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv()

URI = os.getenv("MONGO_URI")
DB  = os.getenv("MONGO_DB", "dads5001")
COL = os.getenv("MONGO_COLLECTION", "bangkok_complaints")

SLIM_PROJ = {
    "_id": 0,
    "district": 1, "problem_type": 1, "state_en": 1,
    "star": 1, "duration_minutes_total": 1,
    "month": 1, "year": 1, "week_start": 1, "count_reopen": 1,
}


def bench(label, fn):
    t0 = time.time()
    result = fn()
    dt = time.time() - t0
    print("{:<42s} {:>8.2f}s   {}".format(label, dt, result or ""))
    return dt


def run(compressors):
    print("\n=== compressors = {} ===".format(compressors or "none"))
    kw = {"serverSelectionTimeoutMS": 15000}
    if compressors:
        kw["compressors"] = compressors
    client = MongoClient(URI, **kw)

    bench("1. connect + ping", lambda: client.admin.command("ping") and "ok")
    col = client[DB][COL]
    bench("2. count documents",
          lambda: "{:,} docs".format(col.estimated_document_count()))
    bench("3. pull SLIM projection (dashboard)",
          lambda: "{:,} rows".format(len(list(col.find({}, SLIM_PROJ)))))
    bench("4. pull 5,000 rows WITH comment",
          lambda: "{:,} rows".format(len(list(col.find({}, {"_id": 0}).limit(5000)))))
    client.close()


if __name__ == "__main__":
    run("zlib")
    run(None)
    print("\nInterpretation:")
    print("- ข้อ 1-2 ช้า (>3s)        -> ปัญหาเน็ตเวิร์ก/Atlas ไม่ใช่โค้ด")
    print("- ข้อ 3 ช้า (>15s)         -> Atlas โดน throttle หรือเน็ตช้า")
    print("- zlib ช้ากว่า none ชัดเจน -> เอา compressors ออก")
