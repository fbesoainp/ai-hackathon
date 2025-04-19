from integrations.gemini import get_restaurant_query, match_restaurants
from integrations.google_maps import query_restaurants
from models.partner import PartnerPreferences
from models.restaurant import UserRestaurantQueryResponse


def get_restaurants_by_user_query(
    partner_preferences: PartnerPreferences, user_query: str
) -> UserRestaurantQueryResponse:
    """Get restaurants by user query"""
    query = get_restaurant_query(partner_preferences, user_query)
    restaurants = query_restaurants(query)
    return match_restaurants(restaurants, partner_preferences, user_query)
