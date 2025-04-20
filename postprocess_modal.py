# postprocess_gemini.py
"""
Uses **Gemini‑Pro** to rank raw restaurant docs and return the formatted
top‑10 list.

Env vars required:
    GEMINI_API_KEY   – Google AI Studio key
    DEV_MODE=true    – lets code fall back to heuristic list when key missing
"""
from __future__ import annotations
import json, os, re
from typing import List, Dict
import numpy as np
from dotenv import load_dotenv


def _pick_first_generatable_model() -> str | None:
    """
    Return model name that supports generateContent on the *current* client.
    Falls back to 'text-bison-001' if nothing obvious is found.
    """
    try:
        models = list(genai.list_models())                    # v1beta or v1
        print("models: ",models)
        for m in models:
            if "generateContent" in m.supported_generation_methods:
                return m.name
    except Exception as e:
        print("[WARN] list_models failed:", e)
    return "text-bison-001"   # v1beta safe option


DEV_MODE = os.getenv("DEV_MODE", "false").lower() == "true"
GEM_API  = os.getenv("GEMINI_API_KEY")

# ------------------------------------------------------------------ Gemini init
_USING_FAKE = False
try:
    import google.generativeai as genai
    genai.configure(api_key=GEM_API)
    model_name = _pick_first_generatable_model()
    model = genai.GenerativeModel("gemini-1.5-flash")
except Exception as e:
    _USING_FAKE = True
    if not DEV_MODE:
        print("[WARN] Gemini unavailable – post‑process falls back to heuristic:", e)

# ------------------------------------------------------------------ helper
def _fallback(raw: List[Dict]) -> List[Dict]:
    """Return first 10 with minimal formatting."""
    out = []
    for r in raw[:10]:
        out.append({
            "name": r.get("name") or r.get("title"),
            "photos": r.get("photo_urls", [])[:4],
            "rating": r.get("rating"),
            "total_reviews": r.get("user_ratings_total"),
            "price": "$$",
            "tag": r.get("tag","Unknown"),
            "tags": [r.get("tag","Unknown")],
            "location": r.get("address"),
            "summary": r.get("description","")[:80],
            "description": r.get("description",""),
            "review_summary": "",
            "opening_hours": ["9:30","20:00"],
        })
    return out

MATCHED_RESTAURANT_SCHEMA = {
    "type": "object",
    "properties": {
        "name": {
            "type": "string"
        },
        "photos": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "rating": {
            "type": "number"
        },
        "total_reviews": {
            "type": "integer"
        },
        "price": {
            "type": "string"
        },
        "tag": {
            "type": "string"
        },
        "tags": {
            "type": "array",
            "items": {
                "type": "string"
            }
        },
        "location": {
            "type": "string"
        },
        "summary": {
            "type": "string"
        },
        "description": {
            "type": "string"
        },
        "review_summary": {
            "type": "string"
        },
        "opening_hours": {
            "type": "array",
            "items": {
                "type": "string",
            }
        }
    },
    "required": [
        "name",
        "photos",
        "rating",
        "total_reviews",
        "price",
        "tag",
        "tags",
        "location",
        "summary",
        "description",
        "review_summary",
        "opening_hours"
    ]
}

MATCHED_RESTAURANTS_SCHEMA = {
    "type": "array",
    "items": MATCHED_RESTAURANT_SCHEMA,
}

# ------------------------------------------------------------------ main api
def rank_and_format(prefs_text: str, raw: List[Dict]) -> List[Dict]:
    """
    Returns up to 10 dicts in frontend schema using Gemini‑Pro.
    Falls back to heuristic if key missing or JSON parse fails.
    """
    if _USING_FAKE:
        return _fallback(raw)

    # Trim raw to reduce prompt size (drop full reviews text >200 chars)
    trimmed = []
    for r in raw:
        t = r.copy()
        if "reviews" in t and isinstance(t["reviews"], list):
            t["reviews"] = [
                {**rev, "text": rev["text"][:160]} for rev in t["reviews"][:2]
            ]
        trimmed.append(t)
    user_prompt = f"""

        "You are an expert restaurant recommender. "
        "Format your entire response strictly as JSON array only."
User preferences: {prefs_text or 'N/A'}

Here is a JSON list of candidate restaurants (≤15):
{json.dumps(trimmed)}
Rank them best to worst for the user. Keep exactly 10 items. For each produce this JSON object:

{{ "name": string, "photos": string[] max 4 (use photo_urls), "rating": number, "total_reviews": number, "price": "$$", "tag": string (first in tags or 'Unknown'), "tags": string[] max 3, "location": string (address), "summary": string (1 sentence, personal), "description": string (copy original description), "review_summary": string (1‑sentence vibe), "opening_hours": ["9:30","20:00"] }}

Respond with ONLY the JSON list – no markdown, no explanations. """
    try:
        resp = model.generate_content(
            [
            {"role":"user",   "parts":[user_prompt]} ],
            generation_config = {
                "temperature":0.5,
                "max_output_tokens":40000,
                "response_mime_type": "application/json",
                "response_schema": MATCHED_RESTAURANTS_SCHEMA
            },
        )
        text = resp.text.strip()
        # strip fences if model adds them
        text = re.sub(r"^```json|```$", "", text, flags=re.S).strip()
        data = json.loads(text)
        return data[:10] if isinstance(data, list) else _fallback(raw)
    except Exception as e:
        if not DEV_MODE:
            print("[WARN] Gemini post‑process failed, using fallback:", e)
        return _fallback(raw)


if __name__ == "__main__":

    prefs_text = "i like asian food"
    raw = [{'area': 'Palo Alto', 'name': 'Ramen Nagi', 'address': '541 Bryant St, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4454866, 'lng': -122.16072}, 'rating': 4.599999904632568, 'review_amount': 3049, 'description': 'Japanese noodle chain outpost offering customizable ramen bowls and vibrant-colored broths.', '_distance': 0.6889216899871826}, {'area': 'Marina District, San Francisco', 'name': 'HINODEYA Ramen Chestnut', 'address': '3340 Steiner St, San Francisco, CA 94123, United States', 'location': {'lat': 37.80024119999999, 'lng': -122.4375457}, 'rating': 4.900000095367432, 'review_amount': 381, 'description': None, '_distance': 0.8100766539573669}, {'area': 'Palo Alto', 'name': 'YAYOI Palo Alto', 'address': '403 University Ave, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4473091, 'lng': -122.1604632}, 'rating': 4.199999809265137, 'review_amount': 1139, 'description': 'Tranquil Japanese restaurant where diners use self-ordering tablets for homestyle dishes & tea.', '_distance': 0.8307063579559326}, {'area': 'Palo Alto', 'name': 'San Agus Cocina Urbana & Cocktails', 'address': '115 Hamilton Ave, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4430386, 'lng': -122.1625459}, 'rating': 4.400000095367432, 'review_amount': 456, 'description': 'Laid-back bar serving Mexican street food, cocktails & beers, plus mezcales & tequilas.', '_distance': 0.8530364632606506}, {'area': 'Palo Alto', 'name': 'Rara', 'address': '201 California Ave, Palo Alto, CA 94306, United States', 'location': {'lat': 37.4282246, 'lng': -122.1430906}, 'rating': 4.800000190734863, 'review_amount': 966, 'description': None, '_distance': 0.865138828754425}, {'area': 'Palo Alto', 'name': 'Wildseed', 'address': 'South, 855 El Camino Real Building 4, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4382288, 'lng': -122.1587727}, 'rating': 4.5, 'review_amount': 563, 'description': None, '_distance': 0.8668149709701538}, {'area': 'Palo Alto', 'name': 'Sweet Maple', 'address': '150 University Ave, Palo Alto, CA 94301, United States', 'location': {'lat': 37.443997, 'lng': -122.162979}, 'rating': 4.400000095367432, 'review_amount': 742, 'description': None, '_distance': 0.8694137930870056}, {'area': 'Palo Alto', 'name': 'Reposado', 'address': '236 Hamilton Ave, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4441583, 'lng': -122.1609667}, 'rating': 4.300000190734863, 'review_amount': 2011, 'description': 'Trendy spot for high-end Mexican fare with a popular bar scene thanks to their margarita selection.', '_distance': 0.87373948097229}, {'area': 'Palo Alto', 'name': "Joanie's Cafe", 'address': '405 California Ave, Palo Alto, CA 94306, United States', 'location': {'lat': 37.4263955, 'lng': -122.1445711}, 'rating': 4.400000095367432, 'review_amount': 1565, 'description': "Casual corner cafe serving lunch & dinner, plus a popular breakfast that's available all day.", '_distance': 0.8749344944953918}, {'area': 'Palo Alto', 'name': 'Nola', 'address': '535 Ramona St, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4449386, 'lng': -122.1614268}, 'rating': 4.400000095367432, 'review_amount': 3322, 'description': 'New Orleans-themed spot offering Creole fare in a 3-floor space reminiscent of the French Quarter.', '_distance': 0.8771637082099915}, {'area': 'Palo Alto', 'name': 'Meyhouse', 'address': '640 Emerson St, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4433997, 'lng': -122.160937}, 'rating': 4.599999904632568, 'review_amount': 311, 'description': None, '_distance': 0.8939375281333923}, {'area': 'Palo Alto', 'name': 'La Boheme', 'address': '415 California Ave, Palo Alto, CA 94306, United States', 'location': {'lat': 37.4262478, 'lng': -122.1446999}, 'rating': 4.400000095367432, 'review_amount': 574, 'description': 'Convivial establishment preparing a range of traditional & modern French specialties.', '_distance': 0.9001345634460449}, {'area': 'Palo Alto', 'name': "Hobee's", 'address': '4224 El Camino Real, Palo Alto, CA 94306, United States', 'location': {'lat': 37.408966, 'lng': -122.1224389}, 'rating': 4.300000190734863, 'review_amount': 1086, 'description': 'Longtime local chain serving health-minded fare, including breakfast, sandwiches, salads & pasta.', '_distance': 0.900178849697113}, {'area': 'Palo Alto', 'name': 'Palo Alto Sol', 'address': '408 California Ave, Palo Alto, CA 94306, United States', 'location': {'lat': 37.4265744, 'lng': -122.1448389}, 'rating': 4.400000095367432, 'review_amount': 589, 'description': 'Colorful cantina with outdoor seating specializing in traditional Puebla cuisine.', '_distance': 0.9003962278366089}, {'area': 'Palo Alto', 'name': 'Tamarine Restaurant & Gallery', 'address': '546 University Ave, Palo Alto, CA 94301, United States', 'location': {'lat': 37.4489127, 'lng': -122.1584482}, 'rating': 4.400000095367432, 'review_amount': 1565, 'description': 'Modern Vietnamese winner stays busy furnishing creative small & large plates in an artful space.', '_distance': 0.9024680256843567}]
 

    rank_and_format(prefs_text=prefs_text, raw=raw)
    pass