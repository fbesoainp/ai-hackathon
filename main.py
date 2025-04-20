# backend_fastapi_main.py – Pairfecto MVP (FastAPI + LanceDB + Gemini)
"""Run (dev, no auth):
    DEV_MODE=true uvicorn backend_fastapi_main:app --reload

* Gemini Embedding 001 → 768‑dim, but our LanceDB table stores **384‑dim**
  vectors. We slice to the first 384 dims so dimensions match.
* If Gemini lib or key is absent ➜ deterministic random embedding (stable dev).
"""
from __future__ import annotations

import os, time
from functools import lru_cache
from typing import Annotated, List

import httpx, numpy as np, lancedb
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()
DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/pairfecto")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "dummy" if DEV_MODE else None)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
LANCEDB_DIR = os.getenv("LANCEDB_DIR", "./data/lancedb")

EMBED_DIM = 384  # VECTOR DIM STORED IN LANCEDB

# ---------------------------------------------------------------------------
# Gemini setup (optional)
# ---------------------------------------------------------------------------
_USING_RANDOM = False
try:
    import google.generativeai as genai  # pip install google-generativeai
    _GENAI_AVAILABLE = True
except ImportError:
    _GENAI_AVAILABLE = False
    _USING_RANDOM = True
    if not DEV_MODE:
        print("[WARN] google-generativeai not installed; using random embeddings.")

if _GENAI_AVAILABLE and GEMINI_API_KEY:
    try:
        genai.configure(api_key=GEMINI_API_KEY)
        _EMBED_MODEL = "models/embedding-001"
        genai.embed_content(model=_EMBED_MODEL, content="ping", task_type="retrieval_query")
    except Exception as e:
        print("[WARN] Gemini init failed –", e)
        _USING_RANDOM = True
else:
    _USING_RANDOM = True

# ---------------------------------------------------------------------------
# Firebase helpers (noop in dev)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _firebase_certs():
    if DEV_MODE:
        return {}
    r = httpx.get("https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com"); r.raise_for_status(); return r.json()

def verify(tok:str)->dict:
    if DEV_MODE: return {"uid":"dev"}
    try:
        return id_token.verify_oauth2_token(tok, google_requests.Request(), audience=FIREBASE_PROJECT_ID, certs=_firebase_certs())
    except Exception: raise HTTPException(401, "Invalid token")

# ---------------------------------------------------------------------------
# DB connections
# ---------------------------------------------------------------------------
_mongo: AsyncIOMotorClient|None=None

def get_mongo():
    global _mongo
    if _mongo is None: _mongo = AsyncIOMotorClient(MONGO_URI)
    return _mongo["pairfecto"]

import pyarrow as pa

# LanceDB connection
lance = lancedb.connect(LANCEDB_DIR)
arrow_schema = pa.schema([
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

try:
    restaurants_tbl = lance.open_table("restaurants")
    if restaurants_tbl.schema != arrow_schema:
        print("[WARN] 'restaurants' table schema mismatch — recreating.")
        lance.drop_table("restaurants")
        raise FileNotFoundError
except (FileNotFoundError, ValueError):
    print("[INFO] Creating empty 'restaurants' table with full schema …")
    restaurants_tbl = lance.create_table("restaurants", schema=arrow_schema)
    print("[INFO] Table ready — run seed_fake_restaurants.py to populate with data.")
    print("[WARN] placeholder table created; run seeder.")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    text: str
    location: dict[str, float] | None = None  # {"lat": ..., "lng": ...}
class RestaurantOut(BaseModel): title:str; photo_url:str|None=None; rating:float|None=None; hours:str|None=None; tag:str|None=None; summary:str|None=None; description:str|None=None; review_summary:str|None=None
class QueryResponse(BaseModel): results:List[RestaurantOut]

# ---------------------------------------------------------------------------
# FastAPI app
# ---------------------------------------------------------------------------
app = FastAPI(debug=DEV_MODE)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

async def _current(req:Request):
    if DEV_MODE: return {"uid":"dev"}
    auth=req.headers.get("Authorization","")
    if not auth.startswith("Bearer "): raise HTTPException(401,"Missing token")
    return verify(auth[7:])
CurrentUser=Annotated[dict,Depends(_current)]

# ---------------------------------------------------------------------------
# Embedding helper
# ---------------------------------------------------------------------------

def _embed(text:str)->np.ndarray:
    if _USING_RANDOM:
        rng=np.random.default_rng(abs(hash(text))%2**32); return rng.random(EMBED_DIM).astype("float32")
    vec=np.array(genai.embed_content(model=_EMBED_MODEL, content=text, task_type="retrieval_query")["embedding"],dtype="float32")
    return vec[:EMBED_DIM]  # slice 768→384

# ---------------------------------------------------------------------------
# Helper – turn prefs dict into a promptable text blob
# ---------------------------------------------------------------------------

def _prefs_to_text(prefs: dict) -> str:
    """Flatten both user & partner prefs into a single string for embedding."""
    parts = []
    for role, p in prefs.items():
        if not isinstance(p, dict):
            continue
        if cuisines := p.get("cuisines"):
            parts.append(f"{role} likes {'/'.join(cuisines)} cuisine")
        if restrictions := p.get("restrictions"):
            parts.append(f"{role} dietary restrictions: {', '.join(restrictions)}")
        if allergies := p.get("allergies"):
            parts.append(f"{role} allergies: {', '.join(allergies)}")
        if budget := p.get("budget"):
            parts.append(f"{role} budget {budget}")
        if atmosphere := p.get("atmosphere"):
            parts.append(f"{role} prefers {'/'.join(atmosphere)} vibe")
    return "; ".join(parts)

# ---------------------------------------------------------------------------
@app.post("/query", response_model=QueryResponse)
async def query(
    q: QueryRequest,
    user: CurrentUser,
    db: Annotated[AsyncIOMotorClient, Depends(get_mongo)],
):
    """Main search endpoint.
    - Combines user query + stored prefs + (lat,lng) into the embedding input.
    - Future: We can post‑filter by distance once restaurant docs include lat/lng.
    """

    # 1) Fetch prefs
    prefs_txt = ""
    if not DEV_MODE:
        try:
            doc = await db.users.find_one({"_id": user["uid"]})
            if doc:
                prefs_txt = _prefs_to_text(doc.get("preferences", {}))
        except Exception as e:
            print("[WARN] prefs fetch failed:", e)

    # 2) Location text (if provided)
    loc_txt = ""
    if q.location and "lat" in q.location and "lng" in q.location:
        loc_txt = f"User location lat {q.location['lat']:.4f} lng {q.location['lng']:.4f}"

    # 3) Build embedding input
    embed_parts = [q.text, prefs_txt, loc_txt]
    embed_text = ". ".join([p for p in embed_parts if p])

    vec = _embed(embed_text)

    # 4) Vector search (no geo filter yet)
    df = (
        restaurants_tbl.search(vec)
        .metric("cosine")
        .limit(8)
        .select([
            "title",
            "photo_url",
            "rating",
            "hours",
            "tag",
            "summary",
            "description",
            "review_summary",
        ])
        .to_pandas()
    )

    return QueryResponse(results=df.to_dict("records"))

# ---------------------------------------------------------------------------
@app.on_event("shutdown")
async def _shutdown():
    if _mongo: _mongo.close()
