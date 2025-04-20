# seed_fake_restaurants.py — create table & seed 100 fake rows in LanceDB
"""Populate the `restaurants` table with a full, typed schema so later inserts
won’t hit Arrow casting errors.

Run:
    python seed_fake_restaurants.py

Dependencies:
    pip install lancedb faker numpy pyarrow
"""
from __future__ import annotations

import os, random
from pathlib import Path

import numpy as np
from faker import Faker
import lancedb
import pyarrow as pa

EMBED_DIM = 384
NUM_ROWS = 100

# ---------------- connection ----------------
LANCEDB_DIR = os.getenv("LANCEDB_DIR", "./data/lancedb")
LANCEDB_URI = os.getenv("LANCEDB_URI")
LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")
LANCEDB_REGION = os.getenv("LANCEDB_REGION", "us-east-1")

db = (
    lancedb.connect(uri=LANCEDB_URI, api_key=LANCEDB_API_KEY, region=LANCEDB_REGION)
    if LANCEDB_URI
    else lancedb.connect(Path(LANCEDB_DIR))
)

# ---------------- explicit Arrow schema ----------------
arrow_schema = pa.schema(
    [
        ("vector", pa.list_(pa.float32(), EMBED_DIM)),
        ("title", pa.utf8()),
        ("photo_url", pa.utf8()),
        ("rating", pa.float32()),
        ("hours", pa.utf8()),
        ("tag", pa.utf8()),
        ("summary", pa.utf8()),
        ("description", pa.utf8()),
        ("review_summary", pa.utf8()),
    ]
)

# ---------------- create / validate table ----------------
try:
    tbl = db.open_table("restaurants")
    if tbl.schema != arrow_schema:
        print("Schema mismatch — overwriting table …")
        db.drop_table("restaurants")
        raise FileNotFoundError
except (FileNotFoundError, ValueError):
    print("Creating new 'restaurants' table …")
    tbl = db.create_table("restaurants", schema=arrow_schema)

# ---------------- generate fake rows ----------------
fake = Faker()
cuisines = [
    "italian", "japanese", "mexican", "thai", "indian", "mediterranean",
    "french", "vegan", "steakhouse", "sushi", "bbq", "ramen",
]

def make_row():
    tag = random.choice(cuisines)
    return {
        "vector": np.random.random(EMBED_DIM).astype("float32").tolist(),
        "title": f"{fake.company()} {tag.title()}",
        "photo_url": fake.image_url(width=400, height=300),
        "rating": round(random.uniform(3.3, 5.0), 1),
        "hours": "11:00‑22:00",
        "tag": tag,
        "summary": fake.sentence(nb_words=8),
        "description": fake.paragraph(nb_sentences=3),
        "review_summary": fake.sentence(nb_words=12),
    }

rows = [make_row() for _ in range(NUM_ROWS)]
print(f"Inserting {NUM_ROWS} fake restaurants …")
tbl.add(rows)
print("Done. Total rows:", tbl.count_rows())
