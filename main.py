# backend_fastapi_main.py – Pairfecto MVP (FastAPI + LanceDB)
"""Run with:
    uvicorn backend_fastapi_main:app --reload

Set `DEV_MODE=true` (env or constant) to **bypass Firebase auth** so you can
hit the endpoints without tokens during local development.
"""
from __future__ import annotations

import os, time, random
from functools import lru_cache
from typing import Annotated, List, Optional

import httpx, numpy as np, lancedb
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, Field
from lancedb.table import LanceTable

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
load_dotenv()

DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/pairfecto")
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID", "dummy-project" if DEV_MODE else None)
LANCEDB_DIR = os.getenv("LANCEDB_DIR", "./data/lancedb")
LANCEDB_URI = os.getenv("LANCEDB_URI")
LANCEDB_API_KEY = os.getenv("LANCEDB_API_KEY")
LANCEDB_REGION = os.getenv("LANCEDB_REGION", "us-east-1")
EMBED_DIM = 384

if not DEV_MODE and not FIREBASE_PROJECT_ID:
    raise RuntimeError("FIREBASE_PROJECT_ID env missing; set DEV_MODE=true to bypass")

# ---------------------------------------------------------------------------
# Firebase helpers (skipped in dev)
# ---------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _firebase_certs():
    if DEV_MODE:
        return {}
    r = httpx.get("https://www.googleapis.com/robot/v1/metadata/x509/securetoken@system.gserviceaccount.com")
    r.raise_for_status()
    return r.json()

def verify_firebase_token(tok: str) -> dict:
    if DEV_MODE:
        return {"uid": "dev-uid", "email": "dev@example.com", "picture": None}
    try:
        return id_token.verify_oauth2_token(tok, google_requests.Request(), audience=FIREBASE_PROJECT_ID, certs=_firebase_certs())
    except Exception:
        raise HTTPException(401, "Invalid auth token")

# ---------------------------------------------------------------------------
# DB connections
# ---------------------------------------------------------------------------
_mongo: AsyncIOMotorClient | None = None

def get_mongo():
    global _mongo
    if _mongo is None:
        _mongo = AsyncIOMotorClient(MONGO_URI)
    return _mongo["pairfecto"]

# LanceDB connection
if LANCEDB_URI:
    db = lancedb.connect(uri=LANCEDB_URI, api_key=LANCEDB_API_KEY, region=LANCEDB_REGION)
else:
    db = lancedb.connect(LANCEDB_DIR)

try:
    restaurants_tbl: LanceTable = db.open_table("restaurants")
except Exception:
    restaurants_tbl = db.create_table("restaurants", data=[{"vector": np.zeros(EMBED_DIM), "title": "placeholder"}], mode="overwrite")
    print("[WARN] Placeholder 'restaurants' table created – seed real data soon.")

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class Prefs(BaseModel):
    cuisines: List[str] = []
    restrictions: List[str] = []
    allergies: List[str] = []
    budget: Optional[str] = None
    max_distance_km: Optional[float] = None
    atmosphere: List[str] = []

class UserDoc(BaseModel):
    user_id: str
    email: str | None = None
    photo_url: str | None = None
    preferences: dict[str, Prefs] = {}

class QueryRequest(BaseModel):
    text: str
    location: Optional[dict[str, float]] = None

class RestaurantOut(BaseModel):
    title: str
    photo_url: str | None = None
    rating: float | None = None
    hours: str | None = None
    tag: str | None = None
    summary: str | None = None
    description: str | None = None
    review_summary: str | None = None

class QueryResponse(BaseModel):
    results: List[RestaurantOut]

# ---------------------------------------------------------------------------
# FastAPI setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Pairfecto API", version="0.1", debug=DEV_MODE)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

async def _current_user(req: Request):
    if DEV_MODE:
        return {"uid": "dev-uid", "email": "dev@example.com", "picture": None}
    auth = req.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(401, "Missing bearer token")
    return verify_firebase_token(auth[7:])

CurrentUser = Annotated[dict, Depends(_current_user)]
DB = Annotated[AsyncIOMotorClient, Depends(get_mongo)]

# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------
@app.post("/query", response_model=QueryResponse)
async def query(q: QueryRequest):
    vec = np.random.random(EMBED_DIM)
    df = restaurants_tbl.search(vec).limit(8).select(["title", "photo_url", "rating", "hours", "tag", "summary", "description", "review_summary"]).to_pandas()
    return QueryResponse(results=df.to_dict("records"))

# ---------------------------------------------------------------------------
# Shutdown
# ---------------------------------------------------------------------------
@app.on_event("shutdown")
async def _shutdown():
    if _mongo:
        _mongo.close()
