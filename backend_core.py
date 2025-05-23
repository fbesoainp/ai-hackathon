# backend_core.py
from dotenv import load_dotenv
from typing import Annotated, List
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import numpy as np
import numbers

load_dotenv()
import user_repo
import embed_modal
import db_lancedb
import location_modal
import geo_utils
import postprocess_modal
import modal
import os


EMBED_DIM = 384
restaurants_tbl = db_lancedb.get_table()
DEV_MODE = os.getenv("DEV_MODE")

# -------------- Pydantic models --------------
from pydantic import BaseModel

class QueryRequest(BaseModel):
    text: str
    location: dict[str, float] | None = None

class RestaurantOut(BaseModel):
    name:str; photo_url:list|None=None; rating:float|None=None; total_reviews:int|None=None; price:str|None=None; opening_hours:list|None=None
    tag:str|None=None; summary:str|None=None; description:str|None=None; review_summary:str|None=None

class QueryResponse(BaseModel):
    results: List[RestaurantOut]

class UserDoc(BaseModel):
    uid: str
    email: str | None = None
    photo_url: str | None = None
    preferences: dict = {}

# -------------- FastAPI setup --------------
app = FastAPI(debug=DEV_MODE)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# -------------- Helper: prefs → text --------------
def _prefs_to_text(prefs: dict) -> str:
    parts = []
    for role, p in prefs.items():
        if not isinstance(p, dict):
            continue
        if c := p.get("cuisines"):      parts.append(f"{role} likes {'/'.join(c)}")
        if r := p.get("restrictions"):  parts.append(f"{role} restrictions {', '.join(r)}")
    return "; ".join(parts)



@app.post("/user/prefs", status_code=204)
async def save_prefs(prefs: dict, request: Request):
    uid = request.headers.get("uid")
    if not uid:
        raise HTTPException(400, "uid header missing")
    await user_repo.upsert_prefs(uid, prefs)
    return Response(status_code=204)

# ---------- Endpoint ----------
@app.get("/user", response_model=UserDoc)
async def get_user(request: Request):
    uid = request.headers.get("uid")
    if not uid:
        raise HTTPException(400, "uid header missing")

    doc = await user_repo.get_user(uid)
    if not doc:
        doc = await user_repo.create_user(uid=uid, email="", photo_url="", prefs={})

    return UserDoc(
        uid=doc.get("_id"),
        email=doc.get("email"),
        photo_url=doc.get("photo_url"),
        preferences=doc.get("preferences", {}),
    )

def _sanitize(x):
    """Recursively turn NumPy containers into vanilla Python types."""
    if isinstance(x, dict):
        return {k: _sanitize(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_sanitize(v) for v in x]
    if isinstance(x, np.ndarray):
        return [_sanitize(v) for v in x.tolist()]
    if isinstance(x, np.generic):
        return x.item()
    return x

# -------------- Query route --------------
@app.post("/query", response_model=QueryResponse)
async def query(q: QueryRequest, request: Request):
    uid = request.headers.get("uid")
    if not uid:
        raise HTTPException(400, "uid header missing")

    
    user_doc = await user_repo.get_user(uid) or {}
    prefs_txt = _prefs_to_text(user_doc.get("preferences", {}))

    # --- 2) try to pull explicit place from query -------------------------
    lat_lng_txt = ""              # will hold "37.42 -122.08" etc.
    place = ""
    if not q.location:
        place = location_modal.get_location(q.text)
        if place:
            coords = await geo_utils.geocode(place)      # (lat, lng) | None
            if coords:
                q.location = {"lat": coords[0], "lng": coords[1]}

    if q.location:                # build the numeric string for embedding
        lat_lng_txt = f"{q.location['lat']:.4f} {q.location['lng']:.4f}"
            

    # --- 3) build embedding input exactly like make_embedding -------------
    embed_parts = [
        place,                        # area unknown at query time
        q.text,                    # treat query text as description proxy
        lat_lng_txt,
    ]
    embed_text = " ".join(p for p in embed_parts if p)
    print("text is: ", embed_text)
    vec = embed_modal.embed(embed_text)


    # --- 4) vector search --------------------------------------------------
    raw: list[dict] = (
        restaurants_tbl.search(vec)
        .metric("cosine")
        .limit(15)
        .select([
            "area","name","address","location",
            "rating","review_amount",
            "description",
            "photos",
            #"reviews"
        ])
        .to_pandas()
        .to_dict("records")
    )

    photo_map = { r["name"]: r.get("photos", []) for r in raw }
    light_raw = [
        {k: v for k, v in r.items() if k != "photos"}   # drop photos from payload
        for r in raw
    ]


    # --- 5) LLM post‑processing (Gemini or Modal) -------------------------
    results = postprocess_modal.rank_and_format(prefs_txt, light_raw)

    for item in results:
        item["photo_url"] = photo_map.get(item["name"], [])[:4]   # keep ≤4 URLs

    return QueryResponse(results=results)

# -------------- Graceful shutdown --------------
@app.on_event("shutdown")
async def _shutdown():
    if _mongo: _mongo.close()
