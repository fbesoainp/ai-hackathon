import os
import json
from pathlib import Path

import lancedb
import pyarrow as pa
from sentence_transformers import SentenceTransformer

# embedding dimension must match model
EMBED_DIM = 384
_model = SentenceTransformer("all-MiniLM-L6-v2")
# lanceDB storage directory
LANCEDB_DIR = os.getenv("LANCEDB_DIR", "./data/lancedb")
# optional NDJSON path to seed new table
NDJSON_PATH_ENV = "restaurants.ndjson"

# Arrow schema definitions
location_type = pa.struct([
    ("lat", pa.float64()),
    ("lng", pa.float64()),
])

review_type = pa.struct([
    ("author_name", pa.utf8()),
    ("author_url", pa.utf8()),
    ("language", pa.utf8()),
    ("rating", pa.int32()),
    ("relative_time_description", pa.utf8()),
    ("text", pa.utf8()),
    ("time", pa.int64()),
])

arrow_schema = pa.schema([
    ("area", pa.utf8()),
    ("name", pa.utf8()),
    ("address", pa.utf8()),
    ("location", location_type),
    ("rating", pa.float32()),
    ("review_amount", pa.int32()),
    ("description", pa.utf8()),
    ("reviews", pa.list_(review_type)),
    ("photos", pa.list_(pa.utf8())),
    ("vector", pa.list_(pa.float32(), EMBED_DIM)),
])


def make_embedding(record: dict) -> list[float]:
    """Compute a 384-d embedding over key text fields and location."""
    parts = [
        record.get("name") or "",
        record.get("address") or "",
        record.get("description") or "",
        record.get("area") or "",
        f"{record.get('location', {}).get('lat', 0.0)} "
        f"{record.get('location', {}).get('lng', 0.0)}",
    ] + [
        r.get("text", "") or ""  # also guard review texts
        for r in record.get("reviews", [])
    ]
    text = " ".join(parts)
    vec = _model.encode(text)
    c = vec.astype("float32").tolist()
    return c


def make_row(data: dict) -> dict:
    return {
        "area": data.get("area", ""),
        "name": data.get("name", ""),
        "address": data.get("address", ""),
        "location": {
            "lat": float(data.get("location", {}).get("lat", 0.0)),
            "lng": float(data.get("location", {}).get("lng", 0.0)),
        },
        "rating": float(data.get("rating", 0.0)),
        "review_amount": int(data.get("user_ratings_total", 0)),
        "description": data.get("description", ""),
        "reviews": [
            {
                "author_name": r.get("author_name", ""),
                "author_url": r.get("author_url", ""),
                "language": r.get("language", ""),
                "rating": int(r.get("rating", 0)),
                "relative_time_description": r.get("relative_time_description", ""),
                "text": r.get("text", ""),
                "time": int(r.get("time", 0)),
            }
            for r in data.get("reviews", [])
        ],
        "photos": data.get("photo_urls", []),
        "vector": make_embedding(data),
    }


def seed_table(table, ndjson_path: Path) -> None:
    print(f"[INFO] Seeding 'restaurants' table from {ndjson_path}")
    batch = []
    with ndjson_path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            rec = json.loads(line)
            try:
                batch.append(make_row(rec))
            except Exception as e:
                print(f"[ERROR] Error processing line {i}: {e}")
                continue
            if i % 100 == 0:
                table.add(batch)
                print(f"  - inserted batch up to line {i}")
                batch.clear()
    if batch:
        table.add(batch)
        print(f"  - inserted final batch of {len(batch)} rows")
    # build vector index
    table.create_index(metric="cosine")
    total = table.count_rows()
    print(f"[INFO] Seeding complete. Total rows: {total}")


def get_table():
    """
    Returns a LanceTable named 'restaurants'.
    If missing or schema mismatched, recreates it, and optionally seeds from NDJSON.
    """
    db = lancedb.connect(LANCEDB_DIR)
    try:
        tbl = db.open_table("restaurants")
        raise FileNotFoundError
        if tbl.schema != arrow_schema:
            print("[WARN] Schema mismatch – recreating table")
            raise FileNotFoundError
    except (FileNotFoundError, ValueError):
        db.drop_table("restaurants")
        tbl = db.create_table("restaurants", schema=arrow_schema)
        print("[INFO] Created 'restaurants' table")
        ndjson_path = "restaurants.ndjson"
        if ndjson_path:
            path = Path(ndjson_path)
            if path.is_file():
                seed_table(tbl, path)
            else:
                print(f"[WARN] {NDJSON_PATH_ENV}='{ndjson_path}' not found or not a file")
    return tbl
