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



def _pick_first_generatable_model() -> str | None:
    """
    Return model name that supports generateContent on the *current* client.
    Falls back to 'text-bison-001' if nothing obvious is found.
    """
    try:
        models = genai.list_models()                    # v1beta or v1
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
                "max_output_tokens":1024,
            }
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
