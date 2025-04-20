# user_repo.py  – simple MongoDB wrapper for user docs
"""
Front‑end now authenticates with Firebase; the backend only receives a
`UID` header.

This helper module:
    • connects to Mongo once (lazy singleton)
    • offers `get_user(uid)`  → dict | None
    • offers `upsert_prefs(uid, prefs_dict)`  → None
"""

from __future__ import annotations
import os, time
from typing import Any, Dict

from motor.motor_asyncio import AsyncIOMotorClient

# ---------- DB connection ----------
MONGO_URI = os.getenv("MONGO_URI", "mongodb://mongo:27017/pairfecto")
_DB: AsyncIOMotorClient | None = None


def _db():
    global _DB
    if _DB is None:
        _DB = AsyncIOMotorClient(MONGO_URI)
    return _DB["pairfecto"]


# ---------- public helpers ----------
async def get_user(uid: str) -> Dict[str, Any] | None:
    """
    Returns full user document or None if not found.
    """
    return await _db().users.find_one({"_id": uid})


async def upsert_prefs(uid: str, prefs: Dict[str, Any]) -> None:
    """
    Creates user doc if it doesn't exist, or updates preferences field.
    """
    await _db().users.update_one(
        {"_id": uid},
        {
            "$set": {
                "preferences": prefs,
                "updated": time.time(),
            },
            "$setOnInsert": {
                "created": time.time(),
            },
        },
        upsert=True,
    )

async def create_user(
    uid: str,
    *,
    email: str | None = None,
    photo_url: str | None = None,
    prefs: Dict[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Insert a brand‑new user document if it doesn’t exist.
    Returns the resulting document (existing or newly created).
    """
    coll = _db().users

    doc = await coll.find_one({"_id": uid})
    if doc:
        return doc  # already present

    doc = {
        "_id": uid,
        "email": email,
        "photo_url": photo_url,
        "preferences": prefs or {},
        "created": time.time(),
        "updated": time.time(),
    }
    await coll.insert_one(doc)
    return doc
