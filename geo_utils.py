# geo_utils.py
import os, httpx

MAPBOX_TOKEN = os.getenv("MAPBOX_TOKEN")
MB_URL = "https://api.mapbox.com/geocoding/v5/mapbox.places/{place}.json"

async def geocode(place: str) -> tuple[float, float] | None:
    """Returns (lat, lng) or None."""
    if not MAPBOX_TOKEN:
        print("[WARN] MAPBOX_TOKEN missing – geocoding skipped")
        return None
    url = MB_URL.format(place=place)
    params = {"access_token": MAPBOX_TOKEN, "limit": 1}
    async with httpx.AsyncClient(timeout=6) as client:
        r = await client.get(url, params=params)
        r.raise_for_status()
        feats = r.json().get("features") or []
        if not feats:
            return None
        lon, lat = feats[0]["center"]   # mapbox gives [lon, lat]
        return float(lat), float(lon)
