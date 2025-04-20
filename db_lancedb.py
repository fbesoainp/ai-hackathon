# db_lancedb.py
import os, numpy as np, lancedb, pyarrow as pa

LANCEDB_DIR = os.getenv("LANCEDB_DIR", "./data/lancedb")
EMBED_DIM    = 384

_SCHEMA = pa.schema([
    ("vector", pa.list_(pa.float32(), EMBED_DIM)),
    ("title", pa.utf8()),
    ("photo_url", pa.utf8()),
    ("rating", pa.float32()),
    ("hours", pa.utf8()),
    ("tag", pa.utf8()),
    ("summary", pa.utf8()),
    ("description", pa.utf8()),
    ("review_summary", pa.utf8()),
])

def get_table():
    """
    Returns a LanceTable named 'restaurants' with the expected schema.
    Creates or recreates it if necessary.
    """
    db = lancedb.connect(LANCEDB_DIR)

    try:
        tbl = db.open_table("restaurants")
        if tbl.schema != _SCHEMA:
            print("[WARN] Schema mismatch – recreating 'restaurants' table")
            db.drop_table("restaurants")
            raise FileNotFoundError
    except (FileNotFoundError, ValueError):
        tbl = db.create_table("restaurants", schema=_SCHEMA)
        print("[INFO] Created empty 'restaurants' table – seed data soon")

    return tbl
