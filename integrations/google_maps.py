# pylint: disable=line-too-long
from functools import cache

import googlemaps
import requests
from fastapi import Response

from models.maps import GoogleRestaurantInformation, GoogleRestaurantQuery, GoogleRestaurantReview
from utils.constants import GOOGLE_MAPS_API_KEY
from utils.logging import logger

GMAP_CLIENT = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def query_restaurants(query: GoogleRestaurantQuery) -> list[GoogleRestaurantInformation]:
    """Search for restaurants using the Google Maps API."""
    logger.info(f"Querying restaurants with query: {query}")
    response = GMAP_CLIENT.places_nearby(
        location=_get_coodinates_by_address(query.location.lower()),
        radius=20000,
        type="restaurant",
        keyword=query.title,
        min_price=query.min_price,
        max_price=query.max_price,
    )

    if "results" not in response:
        return []

    return [_get_restaurant_information(place["place_id"]) for place in response["results"][:40]]


@cache
def fetch_place_information_by_id(place_id: str) -> dict:
    """Fetch place information by place_id"""
    return GMAP_CLIENT.place(place_id=place_id)["result"]


def _get_restaurant_information(place_id: str) -> GoogleRestaurantInformation:
    """Retrieve detailed information about a restaurant, including reviews, website, and Google Maps link"""
    details = fetch_place_information_by_id(place_id)
    return GoogleRestaurantInformation(
        name=details.get("name", "Unknown"),
        description=details.get("editorial_summary", {}).get("overview", "Not found"),
        address=details.get("formatted_address", "Unknown"),
        rating=details.get("rating", 0),
        user_ratings_total=details.get("user_ratings_total", 0),
        reviews=_get_top_reviews(details),
        website=details.get("website", "Unknown"),
        photo_url=f"http://localhost:8000/restaurants/{place_id}/photo",
    )


@cache
def get_restaurant_photo(place_id: str) -> Response:
    """Retrieve the photo of a restaurant"""
    logger.info(f"Retrieving photo for restaurant with place_id: {place_id}")
    details = fetch_place_information_by_id(place_id)

    if "photos" not in details or len(details["photos"]) == 0:
        return Response(content="No photo available.", media_type="text/plain")

    photo_reference = details["photos"][0]["photo_reference"]
    url = f"https://maps.googleapis.com/maps/api/place/photo?maxwidth=800&photoreference={photo_reference}&key={GOOGLE_MAPS_API_KEY}"  # noqa

    logger.info(f"Retrieving photo from URL: {url}")
    response = requests.get(url, timeout=1000)
    if response.status_code != 200:
        return Response(content="Failed to retrieve photo.", media_type="text/plain")
    return Response(content=response.content, media_type="image/jpeg")


def _get_top_reviews(place_details: dict) -> list[GoogleRestaurantReview]:
    """Extract top reviews from a place"""
    reviews = place_details.get("reviews", [])
    return [GoogleRestaurantReview(rating=r["rating"], text=r["text"]) for r in reviews[:3]]


@cache
def _get_coodinates_by_address(address: str) -> tuple[float, float]:
    """Get the latitude and longitude of an address"""
    logger.info(f"Retrieving coordinates for address: {address}")
    geocode_result = GMAP_CLIENT.geocode(address)
    location = geocode_result[0]["geometry"]["location"]
    return location["lat"], location["lng"]
