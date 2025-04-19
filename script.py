import os
import time

import googlemaps

from utils.constants import GOOGLE_MAPS_API_KEY

# Initialize Google Maps Client
gmaps = googlemaps.Client(key=GOOGLE_MAPS_API_KEY)


def search_restaurants(title: str, location: tuple, radius: int = 32186, price_level: int = None):
    """
    Search for restaurants based on title, location, and optional price level.

    Args:
        title (str): General category of the restaurant (e.g., "Italian restaurant").
        location (tuple): Latitude and Longitude (e.g., (37.7749, -122.4194) for SF).
        radius (int): Search radius in meters (20 miles = ~32,186 meters).
        price_level (int, optional): Price level (0=Free, 1=Inexpensive, 2=Moderate, 3=Expensive, 4=Very Expensive).

    Returns:
        list: List of restaurant details including name, address, ratings, reviews, website, and Google Maps link.
    """
    results = []

    response = gmaps.places_nearby(
        location=location,
        radius=radius,
        type="restaurant",
        keyword=title,
        min_price=price_level,
        max_price=price_level,
    )

    if "results" in response:
        results.extend(response["results"])

    return [get_restaurant_details(place) for place in results[:40]]  # Get details for top 40 results


def get_restaurant_details(place):
    """
    Retrieve detailed information about a restaurant, including reviews, website, and Google Maps link.

    Args:
        place (dict): Google Places API response for a place.

    Returns:
        dict: Restaurant details.
    """
    place_id = place["place_id"]
    details = gmaps.place(place_id=place_id)["result"]

    return {
        "name": details.get("name"),
        "address": details.get("formatted_address"),
        "rating": details.get("rating"),
        "user_ratings_total": details.get("user_ratings_total"),
        "reviews": get_top_reviews(details),
        "website": details.get("website"),
        "google_maps_link": f"https://www.google.com/maps/place/?q=place_id:{place_id}",
    }


def get_top_reviews(details):
    """
    Extract top reviews from a place.

    Args:
        details (dict): Detailed place information from Google Places API.

    Returns:
        list: List of up to 3 top reviews with rating and text.
    """
    reviews = details.get("reviews", [])
    return [
        {"author": r["author_name"], "rating": r["rating"], "text": r["text"]}
        for r in reviews[:3]  # Limit to top 3 reviews
    ]


# Example Query
location = (37.7749, -122.4194)  # San Francisco, CA
title = "Italian restaurant"  # Example category
price_level = 2  # Moderate

restaurants = search_restaurants(title, location, price_level=price_level)
for r in restaurants:
    print(r)
