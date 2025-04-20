# backend_core.py
from dotenv import load_dotenv
from typing import Annotated, List
from fastapi import FastAPI, Depends, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import numpy as np

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
    name:str; photo_url:str|None=None; rating:float|None=None; total_reviews:int|None=None; price:str|None=None; opening_hours:list|None=None
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

# -------------- Query route --------------
@app.post("/query", response_model=QueryResponse)
async def query(q: QueryRequest, request: Request):
    uid = request.headers.get("uid")
    if not uid:
        raise HTTPException(400, "uid header missing")

    
    user_doc = await user_repo.get_user(uid) or {}
    prefs_txt = _prefs_to_text(user_doc.get("preferences", {}))
    loc_txt = ""
    place = location_modal.get_location(q.text)
    if place:
        print("Found place: ", place)
        coords = await geo_utils.geocode(place)
        if coords:
            loc_txt = (
    f"User at lat {q.location['lat']:.4f} lng {q.location['lng']:.4f}"
    if q.location else ""
)

    embed_text = ". ".join(p for p in [q.text, prefs_txt, loc_txt] if p)
    vec = embed_modal.embed(embed_text)


    # TODO Fix this shi with the new lancedb seeding.
    raw: list[dict] = (
    restaurants_tbl.search(vec)
    .metric("cosine")
    .limit(8)
    .select([
        "title",
        "rating",
        "description",
        "summary",
    ])
    .to_pandas()
    .to_dict("records")
    )
    
# --- 5) let LLM rank & format ------------------------------------------
    results = postprocess_modal.rank_and_format(prefs_txt, raw)

    return QueryResponse(results=results)

# -------------- Graceful shutdown --------------
@app.on_event("shutdown")
async def _shutdown():
    if _mongo: _mongo.close()
